# JSON语义复审修复验证（2026-10-30）

本记录只覆盖本次固定版本的定向验收，不宣称Sail源码控制流全覆盖。

本分支：memory；Isla `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`；Sail-RISC-V `c70482a73be2a67c5a89d88b1e6c2bbea224940c`。IR及工具哈希见`isla/ir/provenance/manifest.json`。

- float：`cargo test --release -p isla --lib isarch::` 95项通过；五份IR的`test/float_ir/run.py`全部22步通过，helper合计1615例、状态180例、guard20例。helper数量不是源码分支覆盖率。
- memory：同组isarch测试149项通过，含30项数组内存测试；执行限制测试42项通过。部分符号化和错误策略保持原抽象。
- 从当前模型生成的FLI.H/S/D各32项、两种标量BF16共36条JSON，共132条，经GCC/Clang各汇编一次，264/264编码比较通过。
- 模型`test/assembly_text/check.py`另覆盖FLI96条、向量BF16八条、标量BF16十二条，共116条，两套驱动均成功且编码一致。Clang22.1.8；GCC14.2.0配GNU assembler2.45.50。GCC14通过`-Wa,-march=...`选择BF16扩展。
- FCVT.S.BF16的rm=0使用标准无rm助记符；其他模型允许的rm以`.insn r`字段形式表示，保持编码和模型路径。没有用`.4byte`绕过文本检查。
- 内存固定反例：`0x22008f87`寄存器组越界现在返回Illegal且无访存；`0x02008087`在vstart=全1时退休且无活动访存，vstart=0时一次读。
- `configs/riscv64_memory_coverage.toml`将reservation符号化，SC固定编码`0x1820b1af`生成失败无写/成功有写两条路径；原平台配置保持。
- ld/sd/c.ld/amoadd/向量段访问/SC八条见证，两套驱动16次编码比较通过。
- 显式采样的MRET在两个分支均写`summary.status=partial`且sampled-paths非零。无采样MRET生成四条见证，但另有一条未完成终态，因此同样如实标partial。
- 终值查询超时从gen移到diagnostics；单测确认这种空壳不能进入可重放gen。1ms时间盒AMO探针本次未触发超时，不能声称动态强制超时验收通过。
- 根分支独立检出上执行`make solve-MRET THREADS=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=30s SMT_TIMEOUT=20s TASTIC=qfaufbv`均退出0；float追加solve-FLI_S退出0、32条。退出0不替代summary检查。
- 两套workaround各79份；float132个region、memory130个region和各22处锚点有效。memory旧vstart陷阱的两处预算已删除；基准IR哈希按advisory规则保留，告警不表示源码坐标失效。

未验证：完整源码分支分母、全部浮点clause/向量访存域、硬件重放。外部杀进程仍须检查退出状态；JSON不能保证保存正在运行批次。没有推送远端，精确子模块提交的GitHub可获取性未核验。

复现入口：`isla/docs/json-results.md`、`isla/scripts/regenerate_ir.py`、`isla/test/assembly_roundtrip.py`，模型汇编测试为`sail-riscv/test/assembly_text/check.py`（float模型分支）。
