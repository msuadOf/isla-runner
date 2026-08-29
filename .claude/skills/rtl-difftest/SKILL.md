---
name: rtl-difftest
description: 对 XiangShan RTL 疑点做"构造用例→DiffTest→分析→再构造"的定向验证循环。输入为一个或多个疑点（文件:行号 + 预期错误行为），自动构造汇编自检用例、跑真实 emu vs NEMU、迭代收敛根因，并把结论写入 agents/findings.md。当用户给出 RTL 疑点/隐患清单并要求验证、复现或定向测试时使用。
---

# RTL 疑点定向 DiffTest 工作流

对每个疑点执行以下循环。多个疑点时，每个疑点派一个独立 subagent 并行执行（用户说"用 N 个 subagent"时必须并行派发），主会话只汇总。

独立仓库 https://github.com/msuadOf/directed-difftest 是本方法的多疑点工程化实现（5 阶段 workflow 脚本 + run.sh 入口），可选使用；本 skill 自身完整可用。

## 环境（已就绪，勿重建）

- DUT：`difftest-xiangshan/xiangshan/build/emu`（MinimalConfig, VLEN=128, Verilator, commit 7bf51a8）
- REF：`difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so`
- 编译：`riscv64-linux-gnu-gcc`；ELF 入口 `0x80000000`，结束放 GOODTRAP（`.word 0x0000006b`）
- 跑法参考：`difftest-xiangshan/run-local-xiangshan.sh`、`run-v128-smoke.sh`、`pipeline.py`
- emu 无波形支持（`--dump-wave` 会 SIGABRT）；证据用提交跟踪：emu 加 `-b <开始> -e <结束>`，日志含每条退休指令的 pc/编码/dst/data
- 中间文件写 `$CLAUDE_JOB_DIR/tmp/<疑点slug>/`（或 `/tmp/<slug>/`）

## 每个疑点的循环（至少 2-3 轮）

### 第 0 步：把疑点变成可判定的假设
读相关 RTL（疑点行 ± 全调用链），写清楚三件事：
1. 触发条件（什么指令序列/参数组合能让坏路径被执行到）
2. 预期错误表现（哪个寄存器/CSR/内存会得到什么错值，正确值应是什么）
3. 掩盖可能性（是否有前置检查拦截，使坏路径不可达）

### 第 1 步：构造最小自检用例
汇编模板（自检，不依赖人工看波形）：

```asm
# 伪代码骨架
setup:  设置 vl/sew/lmul（vsetvli）、初始化 vd/vs 为可辨识值（如 0x5A、0x70）
trigger: 触发疑点指令序列
check:  读回受影响状态到 GPR（vmv.x.s / csrr）
        beq/bne 分支：值不对则跳到 FAIL 地址（非 GOODTRAP）
        正确则落到 GOODTRAP（0x0000006b）
```

要点：
- 初值要"可辨识"（旧值与算错的新值能区分），掩盖保留旧值类 bug
- 变参数扫描（vstart/vl/间距/顺序各出几个变体），一个 ELF 一组
- **覆盖陷阱**：检查用例是否真的有灵敏度——先跑一个"已知应有差异"的对照（如不执行清零指令确认 vxsat 真被置位），防止用例本身恒真

### 第 2 步：跑 DiffTest 并取证
- GOODTRAP = 双方一致且自检通过；DiffTest ABORT = DUT 与 REF 分歧（这本身就是 bug 证据，看日志里 `data` 字段的双值）
- **测试通过 ≠ 无 bug**（最重要的教训）：若疑点被证伪，追问"异常/flush 路径之后架构状态是否一致"——在 trap 返回、flushPipe、vsetvli 重配置之后再读回向量/CSR 状态。真 bug 常藏在掩盖原疑点的路径里（实例：illegal trap 后 vmv.x.s 读到 agnostic 污染值）
- 证据优先级：DiffTest ABORT 日志 > 提交跟踪的写回 data > 最终寄存器 dump

### 第 3 步：变量控制收敛根因
每轮只改一个变量，目标是找到"决定性实验"：
- 换指令/换参数仍复现 → 排除偶然
- 换目标寄存器（读从未被写过的寄存器）仍复现 → 污染经旁路/检查点扩散，而非写错目标
- 时通时不过 → 竞态特征，记录触发率

### 第 4 步：沉淀
- 结论三分类：真实可触发（bug）/ 被机制天然规避（写明是哪条机制）/ 当前配置不可达（写明何时会暴露）
- 复现用例路径 + 最小复现 ELF 名单
- 所有代码发现追加到 `agents/findings.md`（带日期标题），格式见该文件既有条目

## 并行派发模板

给每个疑点的 subagent 的 prompt 必须包含：疑点描述（文件:行号+预期错误）、上面的环境段、"至少 2-3 轮循环"要求、报告字数上限（<400 词）、中间文件目录。用 Agent 工具单条消息多 tool_use 并行发出。
