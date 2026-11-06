# AGENTS.md

本文件面向在 isla-runner 中工作的 agent 和协作者。项目目标见 [specs/GOAL.md](specs/GOAL.md)，目录和版本边界见 [specs/project-structure.md](specs/project-structure.md)，当前任务与验证状态见 [specs/TODOs.md](specs/TODOs.md)。先读这些入口，再按任务阅读专题文件；不要仅凭历史记录推断当前实现。

涉及 IR 生成或严格 workaround 时，还需阅读 [specs/ir-workflow.md](specs/ir-workflow.md)。
涉及源码版本、子模块或提交边界时，阅读 [GIT.md](GIT.md)。

中英文术语对照统一以 [TRANSLATOR.md](TRANSLATOR.md) 为准；提交说明、代码注释、文档和技术解释均遵循该文件。

CODEX / GPT 的回答、解释、问题说明、方案讨论和进展汇报统一遵循 [GPT_SAY.md](GPT_SAY.md)：先简短说清问题，再按需给具体例子和影响，降低用户的阅读负担。

## 项目与局部规则

本仓库组织特定版本的 Sail、Sail-RISC-V 和 Isla，用于 RISC-V 模型 IR 生成、符号分析和相关差异测试。根目录 `isla/` 与 `sail-riscv/` 是由父仓库 gitlink 固定的子模块。`sail/`、Ara 与 XiangShan 等工具或上游 checkout 按各自边界管理；不得因文档迁移重置它们的工作树。

进入子目录前先检查其 `AGENTS.md`。例如 `isla/AGENTS.md` 有中文、TDD、格式化和编码要求；子目录规则在其范围内补充根规则。若与用户指令或根规则出现无法同时满足的实质冲突，说明具体条款后请求澄清。遵循既有代码风格和变量命名习惯。

## 文档权威关系

| 内容 | 权威位置 | 更新条件 |
| --- | --- | --- |
| 长期目标、范围和验收口径 | `specs/GOAL.md` | 目标或验收定义变化 |
| 目录职责、依赖与版本边界 | `specs/project-structure.md` | 结构或版本管理方式变化 |
| 当前任务的实施、验证、证据和下一步 | `specs/TODOs.md` | 进度、结果或阻塞变化 |
| 逐次测试结果和适用版本 | `docs/RESULTS.md` | 完成一次有结论的验证 |
| 议题计划、状态摘要、调查与协作记录 | `agents/<topic>/` | 对应议题变化 |
| 已核实、可复用的代码发现 | `agents/findings.md` | 发现确立或被修订 |
| 使用者可执行的命令 | `README.md` | 公共入口或已验证用法变化 |
| 中英文术语对照及翻译约定 | `TRANSLATOR.md` | 术语新增、翻译确认或修订 |
| CODEX / GPT 的表达方式与解释示例 | `GPT_SAY.md` | 用户确认或修订表达要求 |

`agents/` 保持原有协作记录目录。`agents/overview.md` 是议题入口，`agents/<topic>/status.md` 是该议题的摘要和详细文件导航，`plan.md` 保存实施方案。`specs/TODOs.md` 汇总全仓当前状态，`docs/RESULTS.md` 汇总逐次验证；更新议题细节后同步议题摘要及全仓状态，不要在多处复制长篇过程。

## 工作方式

1. 开始代码分析前，先从 `agents/overview.md` 和 `specs/TODOs.md` 定位议题，再阅读 `agents/findings.md` 中相关的既有发现及议题文件；必要时扩大阅读范围。结合当前源码核对旧结论，并把新确认的可复用代码事实写回 `agents/findings.md`。
2. 新议题在 `agents/<topic>/plan.md` 写清目标、范围、热点文件、步骤、验证与未决问题，同时建立摘要型 `status.md` 并在 `specs/TODOs.md` 登记。只读调查和写计划属于准备工作。
3. 实施和验证分别记录。只有具体命令、配置、受测版本与结果足以支持时才写 PASS；代码、IR 或关键配置变化后，旧 PASS 退为待复验。失败、未测或阻塞须如实标注。逐次结果、日志解释和历史失败进入 `docs/RESULTS.md` 或议题详细文件，摘要同步到 `agents/<topic>/status.md` 与 `specs/TODOs.md`。
4. 每轮修改后核对代码、脚本、注释、README、设计文档与状态表的逻辑一致性。历史结论不静默删改；发现与当前行为矛盾时，注明原结论适用版本、修订依据和现行入口。
5. 多 agent 任务应明确每个 agent 的目标、可写文件、共享工作树边界和交付格式。主 agent 汇总结论并检查冲突；避免两个 agent 同时编辑同一文件。

既有未提交内容属于当前工作区状态，处理文档或代码前先检查并保留。仓库内路径在说明文字中以根目录为基准，Markdown 链接按文件相对位置书写；不要把本机绝对路径写入可提交文档。

## subagent选用（如果使用subagent）
### 客户端为codex
- gpt-6-luna low做不可靠search
- gpt-6-sol medium/high/xhigh做一些可靠的事情，包括读代码写代码总结代码
- gpt-6-astra medium/high/xhigh做一些关键的判断或者high level的东西架构层面的。所有的astra不准产生二级子代理。
- Main agent就负责调度和用户沟通

### 客户端为claude
无特别要求

### Claude 与 Codex 的分工（2026-11-05 用户确认）

**Codex（gpt-6.1-sol）的特点**
- 优点：严格执行用户指明的技术路径，不偏离、不擅自改方案，做事诚实、不容易出错。
- 缺点一：回复不讲人话，名词晦涩、缺背景铺垫，用户读起来累；关键结论不主动点明。
- 缺点二：容易过度测试、钻牛角尖；架构层面的发散和取舍偏死板。

**分工**
- Claude 负责架构设计、方案取舍和与用户沟通，并把 Codex 的回复翻译成人话（先说结论，再给例子和影响，见 [GPT_SAY.md](GPT_SAY.md)）。
- 调用 Codex 的具体做法（调用链路、指令模板、监控与取消、已踩过的坑）见 [USE_CODEX.md](USE_CODEX.md)。
- 绝大部分代码实现、测试、审查交给 Codex；这样也能降低 Claude 的消耗。普通任务用 gpt-6.1-sol high；所有评审（每块独立评审、方案评审、代码 review 等）统一用 gpt-6.1-sol high（2026-11-05 用户确认，取代此前"high 或 xhigh"的写法）。

**派任务**
- 给 Codex 的指令要写清楚怎么做：目标、技术路径、可改文件、不许改的范围、验收命令。路径一旦指明，Codex 会照做。
- 方案不确定时，先由 Claude 和用户讨论定下来，再派给 Codex，不让 Codex 自行选方案。
- 实验和实现放在 `.worktree/` 独立工作树里做，不动主工作区。

**监控**
- Claude 要盯 Codex 的工作过程：测试跑得过长、偏离主题时及时停止并纠正方向。
- 审查只针对本次改动，不审历史提交；一次性收集尽可能多的问题再统一修改，避免一次只修一点的反复轮次。
- 评审（2026-11-05 用户确认）：范围只限本次关注的修改，不钻牛角尖；评审发现问题后让 Codex 在同一轮里直接修复，修完不必再评审一遍，除非问题涉及面大、需要用户或 Claude 定夺。
