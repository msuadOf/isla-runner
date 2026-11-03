# float→memory 合流计划

目标：以根仓 memory `31ef3b9` 为主线纳入 float `0665526d`，形成有两个父提交的根仓合流，并分别合流 Isla 与 Sail-RISC-V。根仓保持 `topic=memory`。

范围：保留 memory 的内存模型、PMA/CSR、JSON 与构建入口，接入 float 的纯数据选择回退、NaN/trap 与既有 OPEN 实现。本轮不新增通用策略配置，不研究 OPEN 策略；`feat/witness-randomization` 继续排除。旧 memory 排除表中的 float/general 分支随合流进入祖先，不再作为排除项。

热点：父仓 `GIT.md`、`README.md`、`docs/RESULTS.md`、`docs/json-semantic-validation-20261030.md`、`specs/TODOs.md`、`specs/topic-version.json`、`specs/topic-versions.md` 与两个 gitlink；子仓具体代码和 IR 由各自负责人处理。父仓不复制原 master 的未提交内容，不纳入大 IR、二进制或 target 产物。

步骤：保留两个父提交及冲突三方版本；模型和 Isla 双亲合流提交已形成。模型普通严格检查与四配置 IR 生成、五入口安装及来源独审已完成；Isla 冻结源码独审已完成。父仓两个 gitlink 和组合 IR 来源已绑定；已测联合动态范围获[限定签收](review/acceptance/limited-signoff.md)，两组件已从正式远端逐 SHA 回读。父仓提交/发布仍待完成。合流前的 float/memory PASS 只作各自历史证据。

验证：检查父仓冲突全消、`git diff --check`、JSON 可解析、gitlink 与元数据一致；子仓分别执行适用测试、严格 IR 工作流、组合语义与运行门槛，记录命令、配置、结果和限度。未完成项保持待验，不写 PASS。

现行 workaround 边界：合流模型 `bf861b3e` 的 79 份配置、130 个 region、22 处注释锚点经源码映射核对；旧 float 的 132 个 region 是历史版本，不作为合流数量。两处旧 vstart 陷阱区域已退役。严格生成与 IR 来源结论见[模型独审](review/model/ir-review.md)；动态语义仅在[限定签收](review/acceptance/limited-signoff.md)列出的范围内通过。

未决：STORE/C_LD 旧基线完整预算长尾、原域 partial 的全域无退化证明、原目标保护更新及父仓提交/发布。最终 `4d085b14` 二进制绑定的 315/300、Schema Union、nat、真实 Make 与双工具链结果已在已测范围完成独审；两组件正式远端可获取性已核。Isla `4d085b14`、模型 `bf861b3e`、主 IR 哈希已按实际提交和文件回填；验证状态为 `limited-pass`。旧 v2/`7cce7834` 二进制结果不改署为最终版本。精选小证据及未归档产物见[证据清单](implementation/evidence-selection.json)。
