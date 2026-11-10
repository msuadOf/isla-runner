# 标量 min/max SYMBOLIC 数值路径修复

日期：2026-09-26。本包属于已授权浮点 77 项调通。生产改动只涉及 H/S/D 的 FMIN/FMAX/FMINM/FMAXM 十二个 execute clause、FD 纯 helper、V 纯 helper 迁移和模型加载顺序。正式 IR、严格 workaround、官方 77 项与完整指令状态验证由集成人另行完成。

## 版本和冻结件

- Sail-RISC-V HEAD f8ce8490981eac6396a31013180a2e718615757d 加当前未提交工作树；Isla HEAD f4f8e4584a70588c66c9e7a6286cc20211618f18 加当前未提交工作树；Sail 0.20.1 446fb477c508853595ccc937ed60765aa685ae31。
- 大产物：isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z/。pre-edit/ 保存六个生产文件在本轮修改前的真实字节；pre-edit-sha256.json 列出原始哈希，不能以 HEAD 代替。production.patch 是相对冻结件的源码差分，SHA-256 e6a66fbeaac8b7f0b76ecc2cc62b1602708474e9052a36e78865bb8f990cf91b。
- 本轮生产 SHA-256：FD 新 helper b7f7017fa2b0801f0f3618ddd1c7457075d06a572a2bd8e873d653528580997b；V utils 28e3c93d07427dfa9eda93433532a99c2854e6a45aef161baa978a96ea1d3a0c；riscv.sail_project 6cbffa8bb6e9c7103476c86636b1b2d3329c8b6dfe673198826b9c7b6807bb8e。标量文件依次为 F d8a91126223008976795da636b1d904b6a4b7f779c765d495b07ded4dedf9b87、D 3fb3566c16fea04f6e81c01630827b23982f66ffe1c6638404e63464b7740122、H 4d199c591407a5e4286e20e9513af268ce28109d8d33304d157c2da372ce8c2d、Zfa 54210197e82ef682b0174c724751ba6b01116012b4e9891ad9d8aeab4b6435a4。

## 实施

原 V 的 fp_min_pure、fp_max_pure 定义逐字移到 FD/fp_minmax.sail，名称和实现保持。新增 fp_minm_pure、fp_maxm_pure：先调用对应原 helper，再以 strict_or_bool(ieee_is_nan(op1), ieee_is_nan(op2)) 选择 canonical NaN，五位 flags 原样返回。FD_core 在 softfloat_symbolic_f64.sail 后加载新文件，不依赖 V；未新增 IEEE 类型或 primop。

Sail 条件编译置于函数内部会报语法错误，因此十二处使用顶层 SYMBOLIC/普通双 clause。SYMBOLIC 数值体调用纯 helper；普通 clause 整块逐字保留。两侧输入读取、accrue_fflags、原 setter、RETIRE_SUCCESS 相同；mapping guard、索引域和 RM 没有本轮改动。verify_source.py 对照冻结件核普通 clause 字节以及 V helper 原文迁移。

原 fle_H/S/D 的位域比较是小于等于，局部 rs*_lt_rs* 名称并不表示严格小于。旧 MAX 用 fle(b,a) 且相等时选 a；旧 MIN 用 fle(a,b) 且相等时选 a，新 min helper 的严格小于比较在相等时选 b。差异证明比较完整 bits 与 flags，覆盖相等值和 NaN 等位型。

## 验证

- 完整模型 SYMBOLIC 和普通 strict typecheck 均退出 0；原始日志为 typecheck-symbolic.log、typecheck-normal.log。使用 Sail --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --all-modules --just-check model/riscv.sail_project，SYMBOLIC 额外加 -D SYMBOLIC。verify_source.py 五项检查通过；既有 V helper fixture 49/49 通过，日志在 vector-helper/run.log。
- 命令：bash sail-riscv/test/symbolic_fp/solve_scalar_minmax/run.sh isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z/probe-v5 ISLA_PLUGIN_PATH isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z。测试脚本建立新目录，按相同 strict 选项 typecheck、用上述哈希绑定的 Isla plugin 生成 IR、执行 check_ir.py 和 Cargo offline release runner。复跑 V 的命令为 bash sail-riscv/test/symbolic_fp/solve_vector_lanes/run_helper_probe.sh isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z/vector-helper ISLA_PLUGIN_PATH isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z/probe-v2/runner-target/release/scalar_minmax_runner。
- 小 fixture 从冻结源码抽取真实 fsplit、SNaN/NaN、正负零分类、完整 fle 与十二个原数值块；仅 nvFlag 的同值定义与 FD 原 canonical NaN 函数拷入隔离模型，没有用 stub 替换旧分类。任意未知双输入：十二个旧入口共 1566 条完成路径（MIN/MAX/MAXM 各格式 132，MINM 各格式 126），每条先 SAT，再证完整结果 bits 和五位 flags 差异 UNSAT。十二个新入口各一条完成路径，SAT。runner 每条检查没有采样，也没有 ReadReg、WriteReg、ReadMem、WriteMem、Abstract 事件；无 Unknown 或执行错误。
- 每格式与操作另有 24 对定向输入，共 288 对，覆盖正负 qNaN/sNaN 各位置、双 NaN 不同 payload、±0 两顺序、同号零、相等非零、±inf 与正负 subnormal。独立预期核原/新两侧完整值与 flags；仅任一 sNaN 出现时 NV=0b10000，其余四位始终零。十二个定向入口各一条完成路径，SAT。最终 probe-v5/run.log 为 36/36，通过日志 SHA-256 98cbf7da2aeb5490c05d96729a49c56bb364e1d56fb925e2d5d598ac2cb64a93。
- 小 IR SHA-256 504f2c2d469afe99a92afd66d6a4a6b5b114d343144f5d1032d2a1a9c4e4b740。check_ir.py 按实际小写 jump 指令解析：fp_min_pure/fp_max_pure 各两个仅由 bitvector_length 与 16/32 常数比较驱动的位宽分派；fp_minm_pure/fp_maxm_pure 为零个 jump；四函数均无 eq_bits/neq_bits 和数据条件 jump。Isla plugin SHA-256 c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6；最终 runner SHA-256 075d2c4ae162cc8fa01ba56edf498d77704c769466f8e699bd7c2fa13cd28811。probe-v5/report.json 保存 IR、fixture、runner、生成器、生产 helper 与 plugin 哈希。

后续由集成人冻结统一模型，重生成正式 IR、迁移严格配置，并重跑十二目标完整状态及官方组。本隔离结果只证明数值与 flags，不单独代表指令状态验收。
