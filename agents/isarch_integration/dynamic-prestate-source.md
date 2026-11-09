# 动态前态与模板绑定（2026-11-08）

Python 重放入口已取消固定 x1/x2、VA `0x20000000` 和根表 `0x80200000` 的要求。代码与测试只修改当前 `feat/p0-replay` 工作树，未提交；原有未跟踪的 `output/` 内容保留。

## 实施

- `replay_symbolic_prestate.py`：场景支持 `va_values`、`va_domain`（`base`/`size`、`mask`/`value`），保留已有 profile 中的显式约束。默认不注入固定 VA 或 ld/sd 操作数；访问方向与 SATP 模式仍来自场景名。CLI 可重复传 `--va`，或传 JSON `--va-domain`。取消历史样本条数断言，仍要求非空与唯一 sample_id。
- `paging_replay.py`：严格解析实际 ld/sd 构造子或汇编字符串，计算编码及操作数；VA 由基址寄存器加有符号偏移并按 RV64 回绕，根表由 SATP 读取。地址域与指令白名单按实际值检查。模板生成实际指令，并在退出逻辑改写临时寄存器前保存 LOAD 结果，覆盖 rd=x0/t0/s0/x31 等情况。历史 E0 与定向入口也使用动态操作数及根地址。
- `paging_fuzz.py`：预测、STORE 数据、LOAD 后态、异常地址、TLB 的 VPN/ASID 均使用实际前态。非规范 VA 和错位在页表读取前终止。页表搬迁位置及边界候选来自场景 RAM/保留区与样本实际页表，覆盖记录按实际根表和页表页分类。
- 成员复验：保留模板的 IR、config、指令和 clause 绑定，按场景验证模板中已有的有效地址及 SATP 模式；生成复验命令时移除旧的 GPR/SATP `--prestate`，具体值交给 samples v1 输入绑定。继续拒绝符号特权域中的固定特权/mstatus 命令。

本轮未修改符号执行或求解配置；Python 负责消费已求解的样本。既有 J2 变异补充字节与重放诱饵仍是具体测试输入，须经既有 J1 门槛，不构成新的符号求解机制或覆盖证明。

## 验证

从仓库根目录执行：

```bash
PT_DECODE_DIR="$(realpath ../isla-enumerate/agents/path_merge_call_support/pt_decode)" \
PYTHONDONTWRITEBYTECODE=1 \
PAGING_TEST_OUTPUT_DIR="$PWD/output/replay-dynamic-prestate-20261108/elf" \
TMPDIR="$PWD/output/replay-dynamic-prestate-20261108/tmp" \
python3 -m pytest -q difftest-xiangshan/tests/
```

结果：**153 passed，210 subtests passed**。新增 11 项测试，涵盖 Sv39/Sv48 × LOAD/STORE × 八个 VA 槽位（`0x20000000..0x20007000`）、动态 GPR/根表/ASID、正负偏移、寄存器重合、x0、RV64 回绕、高半规范 VA、异常地址及地址域拒绝；真实 ELF 编译并核对 payload 指令编码。所有原有测试保留。

受测基线 `ffcc98e1639327953caab04ef6cee00bdbac4be3` 加本轮未提交修改；Python 3.13.9、pytest 9.0.2。外部 decoder SHA-256 `2ddc69915d0cde369759160182dd34d2ea7191fffc258ed93ab167645a4d7e47`，按只读导入。运行环境中的 `pytest` 脚本使用另一 Python 且无法导入 pytest，因此实际使用 `python3 -m pytest`。

证据：[最终测试日志](../../output/replay-dynamic-prestate-20261108/pytest-final.log)、[受测版本与源码哈希](../../output/replay-dynamic-prestate-20261108/versions-final.json)。前次完整运行的日志和哈希亦保留在同目录。首轮回归发现旧测试仍要求固定 profile 与直接读取 x2，已更新为动态契约；未将中间失败计为 PASS。

本轮没有运行新的 isarch 成员复验、emu 或独立 NEMU。历史 E2/E3/E4 硬件结果继续保留为旧版本证据；重放代码和生成侧 profile 已变化，当前版本硬件结果待复验。
