# 联合动态独审进度

尚未整体签收。最终组件为 Isla `4d085b14`、模型 `bf861b3e`，正式程序 SHA 前缀 `3e44cdd6`。最终数值、混合见证、nat、测试和定向 Make 已实际复算通过；原域 STORE/C_LD partial 的基线归因仍待关闭，不能由定向通过覆盖。

## 已独立核实

- 模型 `bf861b3e` 普通 strict 与四配置生成退出 0。166 个模型文件同时匹配提交 blob 与工作树，149 个工具文件及配置、五安装 IR 来源相符。见 [生成来源](generation-binding-independent.json)。
- `7cce7834` 与模型 `bf861b3e` 的来源、程序 `50465535`、真实 trace/interrupt feature 依赖指纹、官方 Z3 SHA、版本及 ELF 链接相符。独立短探针在 10ms 预算下真实调用一次 `Z3_interrupt`，80ms 返回。见 [v3 构建来源](build-binding-v3-independent.json)。
- v2→v3 仅在两个 `cfg(test)` 模块加入 14 行既有 SMT 初始化；删除这 14 行可精确反构 v2 的文件 SHA，其余 1040 文件相同。见 [精确差异](v2-v3-test-delta-independent.json)。不据此假设两个程序字节相同。
- `final315-7cce`：实际机器字/前态调用独立 SoftFloat，315/315 数值及 flags 相符；独立重建全部约束 IR，核 seed、全部 partial、6566 个初值与 30870 个保持字段。见 [数值](final-315-numerical-independent.json)、[来源与状态](final-315-binding-independent.json)、[并集字段](final-315-schema-independent.json)。
- `final300-7cce`：五 IR 各 60 组，按实际 old/incoming/pre-state 复算 fcsr、FS、SD 和其余位，300/300。callback 只核静态 IR 合同。见 [状态复算](final-300-state-independent.json)。
- `final-union-7cce`：9 个新 JSON 的浮点/整数/原子/压缩访存均按机器字、实际前态、事件顺序、前后字节图和精确三表示复算相符，无 partial。见 [并集与访存复算](final-union-independent.json)。范围限显式 Machine/mstatus 及 4KiB 定向配置。

v1/v2 结果和旧构建来源保留为当时实际受测证据，不改署当前版本。正式后续改动后以新批次和精确版本重新签收。

## 最终 4d085b14 新批次

`7cce7834` 后续仅改四文件末尾 `cfg(test)` 模块的初始化与 panic 原因断言；生产前缀逐字相同。见 [测试差异](workspace-test-delta-independent.json)。最终仍重编并重跑，未用此等价说明改署旧程序结果。

| 项目 | 最终实际结果与独审 |
| --- | --- |
| 程序与来源 | 1042 源文件清单 `6717e0f6` 与 clean 最终提交匹配；正式程序 `3e44cdd6`、真实 trace/interrupt、官方 Z3 与独立 watchdog 通过。[来源](build-binding-4d085b14-independent.json) |
| 新 315 | 实际机器字/前态 SoftFloat 315/315；全部约束 IR 重建、来源、seed 与完整状态通过。[数值](final-4d08-315-numerical-independent.json)、[来源](final-4d08-315-binding-independent.json) |
| 新 300 | 五 IR 各 60 组，fcsr/FS/SD 与其他位全符。[状态](final-4d08-300-state-independent.json) |
| 混合 schema | 9 新 JSON 的完整并集、机器字、访存顺序和前后内存全符。[混合](final-4d08-union-independent.json) |
| nat | VFMERGE/VLSEG 四边界各一组，8/8；direct init_masked_source mask 1/0/0/0，4/4。[指令](final-4d08-nat-independent.json)、[helper](final-4d08-masked-helper-independent.json) |
| 汇编三表示 | 自写 ELF 解析独立读取 54 个 GCC/Clang `.text`，逐字节相符。[工具链](final-4d08-assembly-independent.json) |
| 测试 | 默认单库 394、workspace lib 610、workspace tests 665 全部通过且零忽略/过滤；永久 IR 26 步；104 负控全部拒绝并独立重跑。[测试](final-4d08-regressions-independent.json) |
| 定向真实 Make | 四入口共 27 JSON finished，生产 tactic/配置/双预算/seed/实际 argv 与字段语义相符。wrapper 仅追加固定机器字和前态，不能代替原域。[Make](final-4d08-directed-make-independent.json) |

F1 已独立同输入复证：bdd 与最终候选在同配置、同机器字、同址 `0x80000000`，固定地址读 0，自由符号地址均可读全 1 或 0。该具体/符号内存后端不一致仍在；[继承复证](final-4d08-f1-inheritance-independent.json)不是修复 PASS。

最终限制还包括未钉控制状态的辅助译码边界、原 float 77 全预算未通过范围、未测全控制流覆盖及未做硬件重放。源码/IR/定向无新增阻断不能扩写为全域正确或全预算通过。
