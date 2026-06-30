 排序

  1. range_subset 最值得继续内置化。
  2. pmpCheckRWX 次之，但对当前 zSTORE 收益有限。
  3. misaligned_order 不值得；如果要追这一片，真正该看的是 split_misaligned。

  证据：

  - range_subset 源码本身只是一个纯布尔公式，见 ../sail-riscv/model/core/range_util.sail:12。但编译到 IR 后变成了两层短路 jump，见 ../isla/rv64d.ir:9934、../isla/
    rv64d.ir:9948、../isla/rv64d.ir:9954。这类函数最适合直接改写成 SMT 公式。
  - 我已经加了一个 gated prototype，入口在 ../isla/isla-lib/src/executor.rs:842、../isla/isla-lib/src/executor.rs:855、实现体在 ../isla/isla-lib/src/executor.rs:944，调用拦截
    Store(Data)，源头就在 ../sail-riscv/model/extensions/I/base_insts.sail:323。所以对当前 zSTORE 来说，pmpCheckRWX 内部大部分模式匹配其实是确定的，真正还在 fork 的是调用者
    pmpCheck 对返回布尔值的分支，见 ../isla/rv64d.ir:25595、../isla/rv64d.ir:25597、../isla/rv64d.ir:25611。因此它不是当前最优先。
  - misaligned_order 源码在 ../sail-riscv/model/sys/vmem_utils.sail:101，IR 在 ../isla/rv64d.ir:50638。但它控制的配置位在 IR 里已经固化成 false，见 ../isla/rv64d.ir:50433。这类函
    数本身只有一个配置分支，不该是主要 fork 源。
  - 你现在 profile 里那个看起来像 misaligned_order 的热点，源位置其实是 ../sail-riscv/model/sys/vmem_utils.sail:84，对应 IR 是 ../isla/rv64d.ir:50576。也就是 split_misaligned 的短
    路条件，不是 misaligned_order 本体。

  怎么做 builtin

  - range_subset：
      - 直接在 builtin 里构造 a_end = (a_begin + a_size) - b_begin
      - b_end = (b_begin + b_size) - b_begin
      - shifted_a_begin = a_begin - b_begin
      - 结果是 bvule(shifted_a_begin, b_end) && bvule(a_end, b_end) && bvule(shifted_a_begin, a_end)
      - 现在的 prototype 就是这么做的，见 ../isla/isla-lib/src/executor.rs:859 和 ../isla/isla-lib/src/executor.rs:964
  - pmpCheckRWX：
      - 对当前 STORE 特化时，可以直接改写成 ent[W] == 1
      - 更通用地做，要按 access 构造子生成不同布尔公式：Load -> R，Store -> W，Atomic -> R && W，InstructionFetch -> X，CacheAccess -> 对应字段
      - 如果 access 是符号 union，就要基于 union tag 构造 ITE；这比 range_subset 明显更复杂
  - misaligned_order：
      - 如果只是语义等价改写，最多是把 (n-1,0,-1) 和 (0,n-1,1) 做成 tuple ITE
      - 但在当前 IR 里不值得做

  该记什么事件

  - 不要记成 ../isla/isla-lib/src/smt.rs:287。builtin 不是抽象语义，而是精确改写。
  - 应保留函数级 trace：solver.trace_call/trace_return，见 ../isla/isla-lib/src/smt.rs:2263。我已经在 builtin 路径里补了，见 ../isla/isla-lib/src/executor.rs:997 和 ../isla/isla-
    lib/src/executor.rs:1005。
  - 真正给 Z3 的内容应该落成 ../isla/isla-lib/src/smt.rs:277：
      - 返回值公式用 DefineConst，入口在 ../isla/isla-lib/src/smt.rs:2223
      - 需要额外约束时再加 Assert
  - 如果只是为了后处理更清楚，可以额外加一个新的 Event::Builtin { name, args, return_value }。这只是调试事件，不是求解必须项。

  当前结论就是：先做 range_subset，不要做 misaligned_order；如果继续追第三个热点，优先看的也不是 misaligned_order，而是 split_misaligned。