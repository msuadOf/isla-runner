# 协作规范对照与依据

## Codex 的规则读取方式

- OpenAI Docs 的 [AGENTS.md 说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)指出：Codex 在运行开始时沿项目根到当前目录读取 `AGENTS.md`，越靠近当前目录的规则越具体；同一目录有 `AGENTS.override.md` 时它优先。普通文档不是自动注入的规则，因此根 `AGENTS.md` 必须说明何时主动阅读 `overview.md`、议题 `status.md` 和专题文件。
- OpenAI Docs 的 [Subagents 说明](https://learn.chatgpt.com/docs/agent-configuration/subagents)指出：子 agent 适合边界清楚的并行阅读、测试和汇总；并行写入同一工作树容易产生冲突。仓库规范应写清任务边界与交付约定，但不应规定所有任务都必须派发。

## 参考仓库 `nacc_boom@aa03a94`

- 根 `AGENTS.md` 提供项目入口、先读文档、权威来源、工作约定和修改后一致性检查；`vcs/AGENTS.md` 只给局部目录补充规则。根 `CLAUDE.md` 是指向 `AGENTS.md` 的符号链接，避免维护两份规则。
- 文档各有明确职责：`specs/GOAL.md` 管目标与验收口径；`specs/project-structure.md` 管长期结构与组件归属，开篇明确不记录实施步骤、任务进度和测试结论；`specs/TODOs.md` 管动态状态；`docs/RESULTS.md` 管逐次测试证据；`README.md` 管用户命令。根规则也写明需求变化、结构变化、进度变化分别更新哪里。
- `specs/TODOs.md` 自称唯一动态协作 scoreboard。每个职责条目分开记录“实现情况”和“验证”，验证有 `PASS`、`FAIL`、`未测`、`不适用`、`阻塞` 等明确值；`PASS` 需要证据，代码改变使旧 PASS 失效时回退为待复验。旧证据保留，重复尝试进入进展日志或详细结果。这比笼统的“已完成”更能防止状态误报。
- `specs/TODOs.md` 的单项描述有时也很长，因此“摘要”在此指**任务级当前判断与证据入口**，并不意味着必须限制为几行；逐次配置、版本、耗时、日志等细节仍交给 `docs/RESULTS.md` 或运行目录。这是“状态指向详细证据”的直接参考。
- `AGENTS.md` 要求每轮修改后检查代码、脚本、注释与文档的逻辑一致性；历史材料保留原记录并注明适用版本，不能把旧约束混入当前待办。
- 参考仓库的 SoC 设计、Git push、具体构建和文档审批规则均依赖它自身项目，不应复制到 Isla Runner。

## 对 Isla Runner 的可用映射

| `nacc_boom` 的职责 | Isla Runner 的对应位置 | 建议更新时机 |
| --- | --- | --- |
| 根 `AGENTS.md`、局部 `vcs/AGENTS.md` | 根 `AGENTS.md`、局部 `isla/AGENTS.md` | 协作规则或目录专属约束变化时 |
| 长期结构和文档入口 | `agents/overview.md` | 稳定入口、议题索引或目录职责变化时 |
| 动态 `specs/TODOs.md` | `agents/<topic>/status.md` | 当前进度、验证结论、风险或下一步变化时 |
| `docs/RESULTS.md` 和运行目录 | `agents/<topic>/<subject>.md` 与相应产物 | 实验、审查、设计推导和证据变化时 |
| 稳定设计依据 | `agents/findings.md` 中经核实的跨议题代码发现 | 可复用事实确立或被修订时 |

`plan.md` 是本仓库现行要求的事前实施方案，在参考仓库中没有完全等价的统一文件。不能因借鉴其 scoreboard 就取消“先写计划、等用户确认”的本地规则。

## 当前仓库与迁移边界

- 根 `AGENTS.md` 已有计划确认门槛、`overview.md` 与 `findings.md` 的阅读要求，但未把 `status.md` 定义成摘要导航，也未说明专题细节如何回链。
- `agents/zSTORE_path_explosion/status.md` 已有数百行历史过程，而 `agents/v_symbolic_dedup_perf/status.md` 和 `agents/float_support_review/status.md` 较短。新规范适用于后续维护；批量搬迁历史内容会扩大范围并增加断链风险。
- `agents/findings.md` 目前超过 200 KB。完整通读成本高；在保持“分析前先核对既有发现”的前提下，建议用概览和相关章节定位，必要时扩大阅读。此项应由用户确认。
