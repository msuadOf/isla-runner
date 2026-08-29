# assembly-gen V 扩展上下文初始化 - 状态

## 状态：已完成（待用户确认 commit）

## 改动文件
- `assembly-gen/src/value.py`：新增 `to_hex_words(n)`（256bit 拆 4 个 64bit hex，小端序）
- `assembly-gen/src/assemgen_core.py`：RISCV 新增 `_vtype_zimm_int`/`_vsetvli_insn`/`_v_init_block`/`_vr_data_block`；parse_template 替换 `${V_INIT}`/`${VR_DATA}`
- `assembly-gen/resource/riscv/template_handwritten.S`：`${test_ins}` 前加 `${V_INIT}`，尾部加 `${VR_DATA}`
- `assembly-gen/resource/riscv/template.S`：convert 重生成

## 验证结果
- 单元测试：value.py 12 passed，assemgen_core.py 34 passed，全量 62 passed（无回归）
- 集成（gen[9] vrgather.vv v4,v27,v12, vtype=0x18, 含 vr0-31）：.S 编译通过(50KB ELF)，spike 实测 vsetvli(0x81807057)/vl1re64.v 正确解码，vr0 加载值=0x...4000000000000000 与 JSON 一致
- vill 用例（gen[0] vtype=0x8000...0000 无vr）：V_INIT 用 0x8ff07057(zimm=0xff)，无 vr 加载，VR_DATA 空

## 待办（环境，非本任务）
- difftest 的 spike 需配 elen≥64（如 zve64）才能让 e64 vtype 合法；默认 `--isa=rv64gcv` 让所有 zimm 都 vill（环境问题）
- assembly-gen 是独立 git repo，含其他未提交改动（1.txt/.codex/docs），commit 时需只 stage 本任务文件
