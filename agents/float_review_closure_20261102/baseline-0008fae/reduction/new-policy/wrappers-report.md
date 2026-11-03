# 12 个 FP→整数 wrapper 的纯结果选择候选

## 目标与边界

按本轮 Sol 新准则，12 个 f16/f32/f64→I32/Ui32/I64/Ui64 wrapper 中 `invalid → NaN → sign` 的三层 `if` 只选择返回的饱和整数，回退为已发布基线 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a` 的 ITE 表达式。候选从 `e9d69d2f28586c089244c8e37ee4c904c5114458` 的三个完整 Git 对象构造；没有读取根 dirty `sail-riscv/` 当前文件作为候选来源，没有修改任一生产树、IR、inputs、提交或推送。

ROD 模式两处 `riscv_f32ToF16`、`riscv_f64ToF32` **保持 e9d69d2 原字节**；它们的新增 mode guard 仍列为 OPEN，本候选不对其裁决或改动。NaN canonical 出口、每源分类流程、其他函数和两个测试探针依赖的 RM helper 同样保留 e9 源字节。

| 文件 | e9 源 SHA-256 | 候选 SHA-256 | 说明 |
| --- | --- | --- | --- |
| `model/extensions/FD/softfloat_symbolic_f16.sail` | `63c22bc512222b9697a5d7bf544f4260074eb5cbd2b62cbd716e7cd8917a5877` | `715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646` | 候选整文件与6202基线相同；其间仅这四个整数wrapper发生过差异。 |
| `model/extensions/FD/softfloat_symbolic_f32.sail` | `eb9d4883a239700a78f1969c879ac3857f7b8cb2d9290098c4d06ca769d94ac1` | `ffe71d8f99652a20f9c7c6d969648af75bdc575ee9f2ca34e459fdfa879c5e17` | 四整数wrapper回基线；ROD包装与RM helper保持e9。 |
| `model/extensions/FD/softfloat_symbolic_f64.sail` | `0cd758949af3ed2b13bc519087aff3fa87cf9c080d79b53efe1bebc7108b14ed` | `b5b8ea9e4723e647fa74ea8ebfa47129106993a3a99d9df80105f9b3eab545ce` | 四整数wrapper回基线；ROD包装保持e9。 |

候选文件为同目录 `wrappers-softfloat_symbolic_f16.sail`、`wrappers-softfloat_symbolic_f32.sail`、`wrappers-softfloat_symbolic_f64.sail`；针对 e9 的差异为 `wrappers-source.diff`（SHA-256 `f7f3ad063eede91f55fe8fcdd37ee2b0a6cb40bb333ff7860de83ab49e1612ac`）。`wrappers-build-candidate.py`（SHA-256 `994fdc37bc0e072ca1f81847289c31c35d23dd91a87ba37546c000319fbffce3`）可从两个固定Git提交重新生成，并写 `wrappers-audit.json`（SHA-256 `20eab713cb23c9ee17e294798e8d92f78dd1456427c67c930c62d68680b4d21a`）。

## 逐函数语义与证据

12 个函数的签名、RM 解码、`round_to_integral`、异常facts和原候选整数表达式逐字相同；flags打包调用也逐字保留。只替换最后的饱和选择：invalid为假返回原candidate；invalid且NaN（包括负NaN）返回正端点；invalid且非NaN再依符号选择负/正端点。有符号正/负端点分别为 I32 `0x7fffffff/0x80000000`、I64 `0x7fffffffffffffff/0x8000000000000000`；无符号为 Ui32 `0xffffffff/0x00000000`、Ui64 `0xffffffffffffffff/0x0000000000000000`。flags仍只由原exceptions或flags facts打包，不受选择形式改变。具体12项函数名、正负/负NaN结果及源码函数哈希见 `wrappers-audit.json`。

`python3 agents/float_review_closure_20261102/baseline-0008fae/reduction/new-policy/wrappers-build-candidate.py` 退出0：12函数×invalid/NaN/sign/候选/五位flags共 **12288** 个布尔选择组合，原三层if与基线ITE的返回值和flags配对相同。脚本还逐项要求候选函数等于6202 Git对象，反向恢复12函数后整文件逐字等于e9；两ROD函数另外逐字核对。这个证明覆盖选择公式，**不声称新模型 IR CFG、动态结果、预算或所有FP输入域已验**。

后续由主agent确定是否移入独立模型树并重生/验收IR。当前本目录只是经独审的候选，不是生产实施。

独立Sol已完成[候选源码签收](../../architecture-candidates-review-20261103.json)：从e9 Git对象独立重建12函数的6202精确替换后，三文件与本候选逐字相同；非目标和ROD模式字节未变；独立12288组合的结果/flags等价。此签收只覆盖准备源码，仍未应用生产、运行strict检查、重生IR或取得动态结果。
