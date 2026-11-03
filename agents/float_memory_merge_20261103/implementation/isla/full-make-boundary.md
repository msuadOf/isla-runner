# STORE/C_LD 原域 Make `partial` 边界（2026-11-04）

本记录核对最终 Isla `4d085b14aa0f987436b86d72f41fab1df9e9a132` 的候选运行产物、相关源码、三条错误代表的旧/新同具体状态复放及在途原 memory 全跑。未修改生产源码。两项 Make 都产生了可用见证，但完整 Clause 状态均为 `partial`。三条已复放代表均在原 memory 代码与旧 IR 下触发相同模型异常；此限定结论不能外推为 922/112/7 条已逐项分类，原 memory 全跑也尚未结束。

## 固定输入与实际命令

候选产物位于 `../../validation/dynamic/runs/merge-make-full-v2/make/{STORE,C_LD}/`，实际命令和哈希见各自 `result.json`、`output/rv64_zSTORE.json`、`output/rv64_zC_LD.json` 的 provenance。两项均为原 Clause 自由域、seed 17、单线程、`qfaufbv`、Clause/SMT/外层各 7200 秒；候选二进制 SHA-256 为 `3b0ed9cd570699c6e68134a7309f200d2625295000fea9376354242f3cb5f8dd`，IR 为 `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9`。

Make 命令行**显式传入** `SOLVE_CONFIG=.../configs/riscv64_difftest_mem.toml`，实际 isarch 命令的 `-C` 与 JSON provenance 也指向该文件；SHA-256 为 `f05ab1ce95e776222e0f8f24b65757bdee4341ad084b150b00e7b71b45c73105`。因此不能把 `run.mk` 的缺省配置当成本批输入。原 memory 对照的 `launch.json` 也指向同一物理配置和同一哈希；它使用 bdd047bc 源码二进制 `70d3fa13152b6041faa5c8b1deebc3d5b2076a7f8b733c7835bb83ee340b7b09`、旧 IR `c65b26c8518042c67bfcb48c9feaf2a13a6eb7d741bc01ae8688d78c4370e5d9`，同为 seed 17、`qfaufbv`、单线程和三个 7200 秒时间盒。配置及求解参数可比较，源码和 IR 不同，不能以路径计数逐条配对。

| Clause | Make 退出 | 生成见证 | 错误诊断 | 未完成路径 | JSON 状态 | 运行秒数 |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| STORE | 2 | 130 | 922 | 112 | `partial` | 325.228 |
| C_LD | 0 | 89 | 0 | 7 | `partial` | 22.916 |

`exit 0` 不抵消 C_LD JSON 的 `partial`。`src/isarch/solve_summary.rs` 只要 `errors` 或 `unfinished-paths` 非零就标记 `partial`，并把 `model-coverage` 固定为 `not-measured`；因此生成见证数和退出码均不能证明完整覆盖。

## 失败分类与源码位置

STORE 的 `output/rv64_zSTORE.json` 有 922 条 `diagnostics`，全部为 `reason=path-error`，错误文本相同：`Unreachable: zext_decode 译码回环返回非具体值: Poison`。`src/isarch/exec.rs::encdec_guard_roundtrip_ok` 在 `zencdec_forwards` 产出的 32 位编码上执行 `zext_decode`，检查各可满足译码终值是否为具体构造子；遇到 `Poison` 返回该错误。调用方将错误记录为不完整诊断，不把对应路径加入 `gen`。这是**辅助编码译码回环**的错误；目前没有证据将 922 条解释为 922 条架构执行结果错误或 922 种独立编码。

STORE 运行日志另有 112 条 `zSTORE这个Ctor返回值是Poison`，C_LD 有 7 条同型 `zC_LD` 警告。`src/isarch/exec.rs` 对顶层 `Run::Finished(Val::Poison)` 增加 `unfinished_paths`，不生成成功见证；该计数与上述辅助译码诊断分开。日志提示可能与不支持扩展导致的 Sail `_inner_error_` 有关，但仅凭这条通用提示不能确认具体根因。C_LD 的 `diagnostics` 为空，`partial` 全由这 7 条顶层未完成路径造成。两项均未计执行/SMT/终值模型查询超时，STORE 另有 1 条断言过滤路径。

候选成功见证可作入口健康检查：STORE JSON 含 `32'h3a05_b7a3`（`sd x0, 0x3af(x11)`，Machine），C_LD JSON 含 `16'h73e0`（`c.ld x8, 0xe0(x15)`），且 `16'h6000` 也见于其完成路径日志。错误诊断只保存 `path-signature` 与错误文本，未保存完整前态或待译编码；这些成功编码**不能**充当错误路径的复现输入，也不能据此声称译码 Poison 已定点复现。

## 原 memory 对照与未决判断

原 memory 对照位于 `../../validation/dynamic/runs/merge-baseline-full-v1/baseline-full/{STORE,C_LD}/`。截至本记录，两个进程仍在运行，仅有 `launch.json` 和在途 `run.log`，没有最终 `result.json`。C_LD 在途日志已出现顶层 Poison 与 `read_symbolic` 宽度错误；在最终计数、退出状态和完整日志落盘前，只能作为中途观察。不得将本批候选的 922/112/7 个数或 `partial` 状态署给旧版。

旧 bdd047bc 的 `encdec_guard_roundtrip_ok` 只保留一个译码回调结果，并在末尾检查是否为构造子；候选版收集所有结果，逐条作 Sat 与具体值检查。两版译码回环的诊断机会和文本不相同。旧 collector 在该门的错误分支仅记日志后返回，也不将该错误计入 `summary.errors`；候选版按完整性合同记不完整诊断。这解释了旧新版错误**记账机制**不同，不能由旧版较少的错误数推出该具体状态合法，也不能推断旧版把全部错误路径输出成 `gen`。

## 独立探针与三条同状态复放

为取得错误路径实际输入，另在 `.worktree/fm-store-probe-20261104/` 建两份独立临时源码及独立 Cargo target，候选与原 memory 正式源码、正式二进制、IR 均未改。探针只在环境变量启用时记录首个对应错误并以预设 86/87 停止；直接译码复放以预设 88 停止。这些退出码是诊断完成标记，不是 Make 验收结果。原始产物及补丁路径由主负责人统一归档；独立复核与哈希见[分类审查](../../review/core/partial-boundary/report.md)。

| 代表 | 候选实际捕获 | 新/旧同状态直接复放 |
| --- | --- | --- |
| STORE 辅助译码错误 | path-signature `3705594432398073476`；最终模型的机器字 `32'h01ff_b023`（`sd x31,0(x31)`）；`cur_privilege=VirtualSupervisor`、`mstatus=0`、`misa=0x800000000034112f`、`x31=1`；主执行是地址 1 的 `E_SAMO_Addr_Align` | 两侧各自程序与 IR 的 `zext_decode` 均有一条 Sat 的 Poison 终态，frame 异常均为 `extensions/cfi/zicfilp_regs.sail:31: Hypervisor extension not supported`。旧 helper 报“译码结果不是指令构造子: Poison”，新 helper 报“译码回环返回非具体值: Poison”。 |
| STORE 顶层 Poison | path-signature `662382735639519740`；最终模型 `VirtualSupervisor`、`mstatus=0x21000`；原 STORE 构造子 imm=0、rs1=rs2=31、width=1 | 不经过机器字译码，直接以同一构造子及 102 项完整前态执行；两侧均 Sat、顶层 Poison，frame 异常均为 `core/types.sail:78: Invalid privilege level or virtual mode`。 |
| C_LD 顶层 Poison | path-signature `9876273536327509654`；最终模型 `VirtualSupervisor`、`mstatus=0x21000`；原 C_LD 构造子三个载荷字段均为零 | 直接以同一构造子及 102 项完整前态执行；两侧均 Sat、顶层 Poison，frame 异常也均为 `core/types.sail:78: Invalid privilege level or virtual mode`。 |

辅助译码复放将可解析的 141 项具体寄存器钉入，两侧实际译码寄存器环境各有 183 项。独立复核按寄存器、结构字段和枚举名字比较：141 项钉值、4 项从相同配置重建的 Unit/List/Vector、38 项未初始化状态，与首次候选捕获逐项一致；直接 helper 日志覆盖全部回调类型，本代表各只有一条 Sat Poison 终态。主执行复放的 102 项完整前态与捕获逐项一致。直接复放使用旧 `bdd047bc` 和新 `4d085b14` 各自程序及 IR；固定机器字 CLI 的启动译码会先被符号环境拒绝，不能替代此处辅助回环或原构造子复放。

上述三个**具体代表**在旧版已经触发相同模型异常，故不能把它们定性为合流新增的合法执行丢失。`mstatus=0x21000` 的主执行代表涉及 MPRV=1、MPP=保留值 2；P3 代表则是独立的 zicfilp 虚拟权限不支持分支。两者并非同一原因。剩余 921 条 STORE 回环诊断、111 条 STORE 未完成路径及 6 条 C_LD 未完成路径尚未逐例复放；不据此声称所有候选 `partial` 都已证明继承。

后续由动态验证负责人记录旧版完整原域最终结果，再核对总体计数和是否还有其他错误类型。当前三条代表的继承边界已有旧/新同具体状态实证，但两项 Make 仍为 `partial`，不签完整 Clause PASS。
