# P2：任意宽整数转换与宽位串 ABI 合同

日期：2026-09-27。本文由架构审查者独占，作为[统一后端方案](unified-backend-plan.md)及[P1 adapter 合同](unified-backend-adapter-contract.md)的补充。范围是任意 `n > 0` 整数 BV → f16/f32/f64/f128、四种 FP → BV16/32/64/128，以及 f128 IEEE BV 的准确进出。公共输入域保持现有 Sail 声明，不限制到32/64/128位。

方案准备时点状态：算法与固定 SoftFloat 源码接口已核；隔离原型通过61,820条独立整数数学预期，八个FP→BV128出口的真实Sail生成及对象编译通过，当时尚未实现 P2 adapter。后续P2交付的独立源码/证据审定见第9节；原型证据位于 ignored `.tmp/unified-backend-wide-contract/`，保持其原有适用范围。

## 1. 入口、表示与共同约束

| 入口族 | 个数 | 数学合同 |
| --- | ---: | --- |
| `fpN_from_signed`，N=16/32/64/128 | 4 | 输入 n 位补码整数，按请求 RM 正确舍入到目标格式一次 |
| `fpN_from_unsigned` | 4 | 输入 n 位无符号整数，同上 |
| `fpN_to_signedW`，N/W各取16/32/64/128 | 16 | 先按 RM 舍入输入 FP 到整数；结果在 `[-2^(W-1), 2^(W-1)-1]` 内时返回其 W 位补码 |
| `fpN_to_unsignedW` | 16 | 同上，整数有效范围为 `[0,2^W-1]` |
| `fp128_from_ieee` / `fp128_to_ieee` | 2 | BV128 与 native f128 的编码边界；所有非 NaN 逐位一致，NaN 出口使用统一代表 |

这里的 N 是源或目标 FP 格式，W 是整数目标位宽，n 是运行时输入 BV 位宽。五种 RM 复用 P1 的 `float_rounding_mode` ABI；ROD/DYN 不进入这些通用入口。合法 FP→整数的域外输入仍是数值接口的有效调用：NaN、无穷、越界必须终止并返回某个 BV，不能异常退出或触发 C++ UB。

建议 P2 的 FP→整数共同实现对所有域外值返回全零。此值不是 ISA 饱和规则；Sail 包装仍负责选择架构结果和 flags。P1 的32/64位 direct SoftFloat 路径若保留原域外饱和值，也满足已有未指定域合同；迁移到共同实现时不能把该域外变化误报为有效域错误。无论采用哪种确定选择，所有 native NaN 载体必须得到同一返回值。

通用转换只交付数值，SoftFloat 内部 flags 不传出。调用 `roundPack` / `roundToInt` 时使用 P1 的环境 RAII/TLS 约定，恢复调用前 RM、tininess 与 flags；本文件不另造环境实现。

## 2. 已核 Sail 宽位串 ABI

安装 Sail runtime 的 `lib/sail.h` 定义：

```c
typedef struct {
  mp_bitcnt_t len;
  mpz_t *bits;
} lbits;
typedef lbits sail_bits;
```

正常 `lbits` 保持 `0 <= *bits < 2^len`。借用参数不可修改，也不复制其指针后当成独立所有者。`CREATE(lbits)` 分配并 `mpz_init`，`COPY(lbits)` 使用 `mpz_set`，`KILL(lbits)` 清理；输出 `lbits *rop` 由生成调用者初始化，adapter 只设置长度与值，不再次 CREATE、不释放调用者内存。

P1 实际生成的 `.tmp/unified-backend-p1-adapter/abi_probe.cpp` 已核：Sail bits32/bits64 参数先经 `CONVERT_OF(lbits, fbits)(...,32/64,true)`，再调用 `sail_fp32_from_signed(uint_fast8_t,lbits)`。没有额外隐式长度参数，实例位宽取 `lbits.len`。因此 P2 在相同入口读取完整 GMP 数值即可扩展任意宽，不能继续只读低64位。

固定 FP→BV16/32/64 的生成 ABI 为按值 `uint64_t`，返回值超出 W 的高位清零。FP→BV128 的实际 ABI 已用P0隔离patched Sail确认：`void sail_fpN_to_signed128(lbits *rop, uint_fast8_t rm, floatN_t x)`，unsigned同形。四源格式×两符号性的八个extern均生成此输出指针布局，并通过带相应声明的C++对象编译；没有额外宽度参数。证据为 `wide_abi.sail/.cpp`、`wide_abi.json`，尚未链接/运行实际P2实现。

**线程细节：** Sail `sail.c::sail_signed` 使用共享临时量 `sail_lib_tmp1`。SoftFloat TLS 不能保护该 GMP 状态，P2 不直接调用这个 helper 做补码解码。复用 `lbits` 所有权规则和 GMP API，每次转换用局部 `mpz_t` / `mpz_class` 临时量；所有线程各自拥有输入/输出对象。整个 Sail model 是否可并发是另一个合同，不能由 adapter TLS 自动推出。

## 3. BV → sign + 精确整数幅值

共用内部函数接收 `(lbits raw, bool is_signed)`，返回 `sign` 和非负 GMP 幅值 M：

1. n=`raw.len`；合法公开入口要求 `n>0`。用局部 `mpz_set` 复制输入到 U，可通过 `mpz_fdiv_r_2exp(U,U,n)` 防御性规范到 n 位；不得改借用输入。
2. `sign = is_signed && mpz_tstbit(U,n-1)`。
3. 若非负，M=U；若负，先 `mpz_neg(M,U)`，再 `mpz_fdiv_r_2exp(M,M,n)`，得到精确 `2^n-U`。
4. M=0 时直接返回目标正零。整数 BV 没有负零。

全部补码处理在 GMP 内完成；不把最高位为1的 uint64 强制转为有符号数，不对 `INT64_MIN` 作有符号取负。n=1 时 signed `1` 正确解释为-1；任意 n 的最小负数幅值 `2^(n-1)` 也可准确表示。

溢出判断依据 M 的有效位长 L，不依据输入 n。例如 n=65537 的 signed 全1输入仍为-1，必须返回精确-1。`mpz_sizeinbase(M,2)` 只在 M非零之后调用，得到准确 L；GMP 对0返回1不应进入指数公式。

## 4. 任意宽整数 → 目标格式的单次 roundPack

固定 SoftFloat 的以下内部函数已有实现和声明，位于 `source/s_roundPackToF*.c` 与 `source/include/internals.h`。新 adapter 可以在其实现 TU 中引用这些内部入口；公共头不泄漏内部结构。依赖必须固定当前 SoftFloat 源码和编译宏，后续升级重新核参数合同。

| 目标 | 有效精度 p | bias / emax | 丢弃区 g | 保留总位数 K=p+g | roundPack 参数 |
| --- | ---: | ---: | ---: | ---: | --- |
| f16 | 11 | 15 | 4 | 15 | `(sign, exp, sig)`，sig最高有效位在14 |
| f32 | 24 | 127 | 7 | 31 | 同上，sig最高有效位在30 |
| f64 | 53 | 1023 | 10 | 63 | 同上，sig最高有效位在62 |
| f128 | 113 | 16383 | 64 | 177 | `(sign, exp, sig64, sig0, sigExtra)`；保留113位拆为49+64，另有64位extra |

对非零整数 M，`e=L-1` 为真实二进制指数，普通调用的 `exp=e+bias-1`。减1来自 roundPack 的 pack 宏会把显式 hidden bit 加到 exponent 位；不能把 `e+bias` 直接传入。

先处理指数容量，再转换成 host 类型：若 `e>emax`，使用 `exp=2*bias`，sig采用规格化的1（即第K-1位置1，其余0），进入该目标 roundPack 的确定溢出分支。这个哨兵在四格式中分别是30、254、2046、32766，均适合对应参数类型。真实 e 可能来自任意大 n，不能先转成 `int_fast16_t/int` 再比较。此快捷路径只用于已确定 `|x| >= 2^(emax+1)`；`e==emax` 仍进入正常舍入，以正确处理最大有限值和溢出中点附近。

其余情况计算局部 GMP 的 Q：

```text
if L <= K:
    Q = M << (K-L)
else:
    d = L-K
    Q = floor(M / 2^d)
    discarded_nonzero = !mpz_divisible_2exp_p(M,d)
    Q.bit[0] = Q.bit[0] OR discarded_nonzero
```

这里保留 p 位主有效数，以及 g 位舍入区。最后一位汇总所有更低位是否非零；它保留精确/非精确、半ULP以下/恰好/以上的区别，不进行预舍入。禁止先执行“加半ULP再右移”，否则 roundPack 会再次舍入。

f16/f32/f64 的 Q 最多15/31/63位，精确导出到无符号64位后调用相应 roundPack。f128 的 Q 最多177位，以低字优先导出三个64位 word：

```text
sig64   = Q[176:128]  // 49位，含 hidden bit
sig0    = Q[127:64]
sigExtra= Q[63:0]     // bit63是half，低位含sticky
softfloat_roundPackToF128(sign, exp, sig64, sig0, sigExtra)
```

推荐 `mpz_export` 到清零的 `uint64_t words[3]`，`order=-1,size=sizeof(uint64_t),endian=0,nails=0`；实际导出字数必须在容量内。不要依赖 `mpz_get_ui` 总能返回64位，也不要通过 `uint64 << 64` 拼宽字。左移、右移使用 GMP；差值仅在已知非负的分支计算，避免无符号下溢。

这条路径只有一次浮点舍入：最终目标 roundPack。M到Q只截取有效数并保存sticky，目标舍入所需信息未丢失。大整数不能普通舍入到 f128 再窄化：例如 f32/f64 中点附近的大整数会先在f128丢掉低位，再被误当成精确中点。此处 f128仅作为最终目标格式时调用其 roundPack。

可选32/64位 native fast path 必须与这一算法在五RM、符号和端点上等价，并保留任意 n 的通用路径；不能用未实现宽度断言作为最终 P2 行为。首版采用统一 GMP 路径更容易审阅，性能优化由实测决定。

## 5. FP → 任意指定 W 的同格式取整和精确提位

所有32个 typed 出口可复用一个内部算法。W当前为16、32、64、128；算法本身可写为编译期W参数。先按 raw exponent/fraction 分类，不经 host浮点。

1. 若输入为NaN或无穷，返回选定域外BV（建议0）。所有NaN payload/sign/sNaN均走同一返回。
2. 在环境作用域内调用同源格式的 `fN_roundToInt(x,rm,false)`，N=16/32/64/128；返回 R 仍是源FP格式。不得先转到不同精度，也不得先调用FP→i64。
3. 精确拆R：sign、存储指数E、fraction F；p/bias取第4节表。若R为任一零，令整数J=0。非零R必须为normal，令 `M=(1<<(p-1))+F`，`shift=E-bias-(p-1)`。
4. 若shift≥0，GMP幅值 `A=M<<shift`；若shift<0，`A=M>>(-shift)`。后者必须整除，测试/调试可用 `mpz_divisible_2exp_p` 核实此内部不变量；结果已经是整数，不在这里再舍入。
5. 根据sign令 `J=-A` 或 `J=A`。signed有效条件为 `-2^(W-1)<=J<2^(W-1)`；unsigned有效条件为 `0<=J<2^W`。先检查范围，再编码。
6. 有效时用 `mpz_fdiv_r_2exp(B,J,W)` 得到非负W位补码；域外返回0。不得先取模再检查范围，否则越界会静默绕回有效域。

同格式 `roundToInt` 足够：如果原值的小数需要舍入，所得整数能在源格式精确表示；当幅值已大到源格式整数间距≥1时，原值本来就是整数。因此步骤2不会制造“先浮点舍入，再整数舍入”的二次误差。步骤3–6只有整数精确运算。

负小数不能在取整之前按 unsigned 非法处理：例如-0.25在RTZ/RTP/RNE/RMM下取整为0，是合法无符号结果；在RTN下为-1，才属无效。-0.5的RNE→0、RMM→-1也应区分。负零应当作整数0，不因原sign位拒绝。

原FP exponent字段有固定宽度，f128的最大有效移位也仅约16K位，可安全使用足够宽的有符号host临时变量计算shift，再把非负量传GMP。可先按最终W和指数早判明显越界以减少分配，但不能改动取整后的边界语义。不得使用 `1ULL<<W` 构造W=64/128范围，范围常量同样用GMP。

## 6. f128 IEEE 进出与整数结果写回

当前平台头 `LITTLEENDIAN=1`，SoftFloat `float128_t.v[0]` 对应低64位、`v[1]` 对应高64位。外部BV128的bit0是低字bit0；sign是高字bit63，指数为高字bits62:48，fraction为高字低48位与低字64位。

`fp128_from_ieee(lbits)` 检查宽度128，按上述 `mpz_export` 取两字组成 `float128_t`；它是重解释，不作整数数值转换。`fp128_to_ieee` 对非NaN原样写回两字；NaN使用高字 `0x7fff800000000000`、低字0的统一代表。所有原始sNaN/payload/sign信息由调用方原BV保留，数值对象不承诺恢复。

写回`lbits *rop`时对两字使用 `mpz_import`，设置 `rop->len=128`。参数 `order=-1,size=sizeof(uint64_t),endian=0,nails=0` 保证字序，避免把64位低字getter误用为128位读取。FP→BV128整数输出直接 `mpz_set(*rop->bits,B)`，同样设置len128。固定小BV输出使用清零的64位暂存和精确导出，并满足高位清零。

`SOFTFLOAT_FAST_INT64` 的库/adapter一致可见性沿P1；roundPack内部API的参数分别为f16/f32/f64的 `int_fast16_t`、f128的 `int_fast32_t`。头文件与实际对象必须采用同一平台、TLS、编译宏，不能把旧非TLS库当成新生产构建。

## 7. 小原型结果与它的适用范围

本轮在 `.tmp/unified-backend-wide-contract/` 写入独占 `probe.cpp` 与 `run.py`。C++原型采用第3–5节算法，链接已有固定哈希SoftFloat静态库；Python预期只用任意精度整数、商余数和五RM规则计算，不调用被测SoftFloat或生成器。输入和原始输出均保留。

| 项目 | 本轮结果 |
| --- | --- |
| C++原型构建 | `g++ -std=c++17 -fsanitize=undefined -fno-sanitize-recover=all` 退出0；精确命令及库/源哈希见 `build.json` |
| FP→BV128实际ABI | P0 patched Sail生成八个typed出口退出0，`g++ -c`退出0；命令/源/生成哈希见 `wide_abi.json`。P0源码来源为 `git archive 446fb477` 加其生成器补丁，wrapper的 `--version` 可能误读父仓Git，不据此判定源码版本 |
| BV→FP | 9,500条全部一致；四FP格式、五RM、signed/unsigned，n含1/2/7/8/15/16/31/32/63/64/65/66/112/113/114/127/128/129/130/256/1024/16384/16385/65537 |
| FP→BV | 52,320条全部一致；四FP格式到四W、两种符号性、五RM，包含NaN/inf/零/次正规/整数边界/随机位模式 |
| 执行 | 退出0，61,820个输出，0差异，stderr为空，原型UBSan无报告 |

结果与哈希见 `results.json`；输入SHA-256为 `66015916b74c8fa091e13d140ea72b6cec218b0f54996696b877785cbdca516a`。数值PASS只验证隔离算法，库为历史非TLS构建，UBSan仅覆盖原型TU，未重新编译检测库内部。另有独立生成ABI编译证据，但尚无生成对象与P2实现的链接/运行、生产代码、TLS交错或资源泄漏验证。原型可供实现者理解参数布局，不直接复制其CLI或历史库路径到生产。

## 8. 实施必须补齐的边界测试

1. **真实生成ABI：** Sail程序调用全部8个任意宽入口与32个整数出口，含n=1/33/65/113/129/1024及BV128输出；检查输入len完整保留、输出len准确、宽输出先初始化再写回且无泄漏。FP/RM默认返回、record/ITE由P0门槛覆盖。
2. **补码与有效位：** 每个n的0、1、全1、最大正数、最小负数；signed宽全1→-1；只有bit64/112/127/最高位为1；不能只检查低64位。确认输入GMP对象未改动。
3. **舍入信息：** 每格式保留尾位奇/偶，半ULP前一整数、精确半ULP、后一整数；更低余数仅bit0为1；正负号对调，五RM；f32/f64经普通f128中转会出错的中点±1例必须过。
4. **溢出与容量：** e=emax-1/emax/emax+1；最大有限值、溢出中点附近；输入有效位长大于65536，确认先夹指数再转换host类型；超宽但有效幅值小的signed输入不得误溢出。
5. **FP→整数边界：** ±0、±最小次正规、±0.25/0.5/0.75/1.5/2.5；每W的±2^(W-1)、2^W及相邻可表示FP；取整后刚进入/越出范围；特别核unsigned负小数→0和signed最小值。
6. **无效总定义与NaN：** 各格式正负qNaN/sNaN、多payload、±inf、两侧有限越界均正常结束；同一native NaN抽象返回一致；只有有效域要求数值oracle逐位等同。Sail ITE先计算candidate再屏蔽的真实入口也要跑。
7. **线程/环境/UB：** 复用P1作用域和TLS测试，加入宽转换并发、不同RM/flags哨兵；不用`sail_signed`全局scratch。ASan/UBSan或等效检查覆盖移位0/63/64/112/127/128、最小负值、GMP临时对象及重复输出复用。
8. **独立预期：** 32/64有效域对照SoftFloat native API，任意宽域对照独立精确整数算法或Z3。最终共享helper结果/flags仍需独立native参考，不从同一Sail公式反推预期。

P2放行要同时满足完整公共宽度域、真实生成ABI、数值正确、无效输入总定义和环境隔离。当前小原型的PASS只用于支持这份可实施算法合同。

## 9. P2实际交付的独立审定

2026-09-27复核[实际源码](tools/unified_backend_p2_wide/sail_softfloat_wide.cpp)、[声明](tools/unified_backend_p2_wide/sail_softfloat_wide.h)、全部测试与生成脚本，并逐项重算[冻结manifest](tools/unified_backend_p2_wide/manifest.json)的文件哈希。审查结论：**该冻结P2实现满足本文宽转换数值、ABI形状、无效输入总定义和局部环境合同，未发现必须修正的语义问题，可以进入生产集成。** 此结论不代替最终190声明公共绑定、共享Sail helper或整机验收。

冻结标识：manifest SHA-256 `6f09b80c4fc3ef3268117877d3cf7faa68b4ec8a3f96ca27c16910c9986b4ddd`；wide.cpp `3e934be4379d627158b4dd2b2cecb54563a51dbd9cda7a579b798a7d5be318e5`；wide.h `966116135755712e470f2374d0b9a38fd688fbf95eac77e8c076a69fa9ac358f`。所列P1源码、静态库、P0 wrapper、生成文件和测试二进制哈希也与受审文件全部一致。详细运行证据位于 `.tmp/unified-backend-p2-wide/final/`。

逐函数审查确认：

- `prepare_pack` 先按n规范U，再用局部GMP取补码幅值；不写输入、不使用Sail共享scratch。有效位长在任何host指数cast前比较上限，只有确定溢出时进入 `2*bias` 哨兵；n=65537的-1仍走精确小幅值路径。零输入经零significand的roundPack返回正零。
- 四种目标使用本文p/g/K和word次序，`discarded`仅在L>K时计算，sticky由全部丢弃位是否可被 `2^d` 整除决定。`export_words` 的非负和≤192位内部检查保证三个64位字容量；f128按 `[2],[1],[0]` 传入49位高有效数、64位低有效数、64位extra，未经过另一FP格式中转。
- `rounded_integer` 对NaN/inf先返回域外状态；其他输入调用同源 `roundToInt`。`unpack_rounded` 使用精确GMP移位和取整后范围检查，负零归0、unsigned负小数按舍入后的整数判定。域外和内部非整数状态均由出口返回0，正常数值输入没有assert/abort路径。
- `wide_result` 只写调用者已初始化的GMP和len128；`LocalInteger` 的析构逐个清理临时对象，禁止复制。f128 IEEE入口正确读两个word，出口将所有NaN映射为单一代表，非NaN按位保留。
- 使用SoftFloat的路径由P1 `Scope`包住；提前返回NaN/inf的路径没有修改环境。所有GMP临时对象均局部；TLS和线程各自输入/输出避免共享状态竞争。wrong-width IEEE输入或损坏的lbits指针属于ABI错误，不属于合法FP→整数域外输入。

验证证据和独立复核范围：

| 证据 | 已确认内容 | 范围限制 |
| --- | --- | --- |
| 61,820条数值矩阵 | actual wide hooks：9,500 From与52,320 To，全部输出数、退出0、差异0。独审再次使用原合同的独立Python整数参考逐项重算已保存输出，61,820条仍全部一致；未重新执行整矩阵 | 直接调用内部hooks；不是所有公共wrapper的动态调用证据 |
| 82个真实Sail方法 | 48个不同n的From实例、32个To形状、2个f128编码入口全部生成、编译、链接和运行退出0；类型和输出指针ABI无手工绕过 | fixture绑定名为 `p2_*`，经生成的bridge进入内部hooks；不能把82个方法称为82种公开FP原语 |
| 公共wrapper定向 | P1静态库的真实 `sail_fp*` 入口覆盖n129/65537、f16/f32/f64/f128的宽输入、16/128位输出、f128 IEEE和环境恢复；退出0 | 稀疏定向覆盖；最终190声明的生成公共绑定由P1整体验证提供 |
| 8线程×1000轮 | 宽整数→f128中点与f128→int128按五RM循环，不同线程RM/tininess/flags哨兵均保持；源码未串行化运算，三SoftFloat状态符号实为TLS | 支持adapter环境隔离，不能推广为整个Sail模型共享实例的线程安全 |
| ASan/UBSan | 数值、生成bridge、环境测试直接编译的P2 wide.cpp及测试TU使用两类sanitizer，无报告 | P1 adapter、SoftFloat C、Sail runtime、GMP静态/动态库未由此runner instrument。public_dispatch仅测试TU instrument，其调用的P1库内P2对象也未instrument |

独审保存输出重算结果与输入/输出哈希见 `.tmp/unified-backend-wide-contract/implementation-review.json`；输出SHA-256为 `bad0ea8f0d1814523248300c59fdd177a2bfcf96b8e30c564c3b61e887adaa1f`。原合同参考是精确整数商余数算法，未调用SoftFloat roundPack/roundToInt来计算预期；因此支持独立数值比较，但仍不宣称形式证明或所有可能输入穷举。

P1实际接线已读：32/64位From保留native快路，其余n分派 `sail_softfloat::wide::from_*`；16/128位To及f128 IEEE边界走wide，32/64位To保留native API。两组To的域外零/原生饱和值差异符合未指定域合同，ISA结果仍由Sail决定。集成必须启用 `SAIL_SOFTFLOAT_ENABLE_WIDE`，包含同一冻结wide源码和一致TLS/FAST_INT64库；只拷贝声明或关闭该构建分支不能继承本节放行。P1公有文件接线仍由其唯一owner维护，P2交付不重复定义公有wrapper。
