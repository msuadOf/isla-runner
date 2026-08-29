# assembly-gen 支持 V 扩展上下文初始化

## 目标
让 assembly-gen 能解析 JSON `isa-state` 中的 `vtype`(64bit CSR) 和 `vr0`-`vr31`(256bit 向量寄存器)，生成在 `${test_ins}` 前正确初始化 V 扩展上下文的汇编。

## 已验证的关键技术决策（spike 1.1.1-dev 实测）
1. **vtype 是只读 CSR**：`csrw vtype` 在 spike 触发 `trap_illegal_instruction`。必须用 `vsetvli`(`.insn` 编码) 设置。
2. **vsetvli 编码**：`0x80000000 | (zimm<<20) | 0x7000 | 0x57`，zimm=vtype 低 11 位。例 `vsetvli x0,x0,0x18` = `0x81807057`，已被 spike 正确解码并调用 `set_vl`。
3. **set_vl 校验逻辑**（processor.cc:382）：合法 zimm 接受；非法时（`vsew>ELEN`、`vediv!=1`、`newType>>8!=0` 等）置 `vill`（`vtype=0x8000_0000_0000_0000`）。
4. **vill vtype 处理**：JSON 中 bit63=1 的 vtype（如 `0x8000_0000_0000_0000`）无法用 zimm 直接表达 bit63，改用一个保证非法的 zimm=`0xff`（vediv=3 且 vsew=7）触发 set_vl 拒绝，进入 vill，语义匹配。
5. **vr 加载**：`vl1re64.v`(`.insn 0x0282f007 | (vd<<7)`, rs1=t0) 是 whole-register load，加载 VLEN 位，`require_vector_novtype(true)` 即 vill 下也能加载。实测在 vill vtype 下成功从内存加载到 v0。
6. **VLEN=256**（findings.md zvlen_exp=8）：每 vr 占 32 字节 = 4 个 `.quad`，小端序（低字在前）。
7. **gcc 11.4 不支持 V march**：所有 V 指令用 `.insn <hex>`；`csrw`/`csrs`(zicsr) 可用助记符。
8. **注意（环境）**：默认 `--isa=rv64gcv` 的 spike 因 ELEN 配置问题让所有 zimm 都 vill，属 difftest 运行环境（varch/elen）问题，非 assembly-gen 职责。assembly-gen 忠实生成正确编码即可。

## 改动文件
- `src/value.py`：新增 `to_hex_words(n)` 把位值拆成 n 个 64bit hex（小端序）。
- `src/assemgen_core.py`：RISCV 类新增 vtype/vr 解析与 `${V_INIT}`/`${VR_DATA}` 块生成。
- `resource/riscv/template_handwritten.S`：`${test_ins}` 前加 `${V_INIT}`，尾部加 `${VR_DATA}`，重跑 convert 生成 `template.S`。

## V_INIT 块结构（每用例由 Python 生成）
```
li   t1, MSTATUS_VS
csrs mstatus, t1          # 启用 V 扩展
.insn 0x8<zimm>07057      # vsetvli x0, x0, zimm
# 仅当 isa-state 含 vr0:
la   t0, _vr_data
.insn 0x0282f007          # vl1re64.v v0, (t0)
addi t0, t0, 32
... (v1..v31)
```
## VR_DATA 块结构
```
.section .data.vr_init
.align 3
.globl _vr_data
_vr_data:
.quad <vr0_word0>  # 低 64bit
.quad <vr0_word1>
.quad <vr0_word2>
.quad <vr0_word3>  # 高 64bit
... (vr1..vr31)
```

## TDD 顺序
1. value.py: to_hex_words 测试 + 实现
2. assemgen_core.py: _vtype_zimm / _v_init_block / _vr_data_block 测试 + 实现
3. template 占位符 + convert 重生成
4. 集成验证（JSON -> .S -> gcc -> spike）
