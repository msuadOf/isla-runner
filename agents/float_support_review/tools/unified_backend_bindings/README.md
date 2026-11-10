# 190 条原生 FP 声明的双后端绑定清单

`generate.py` 从原声明、逐名调用表和 67 个 `riscv_*` 策略声明生成一对一 JSON/TSV、仅在证据目录的声明候选、四工具 Sail 函数体片段及策略绑定边界。`verify.py` 对冻结输入和生成表逐名核验，并实际调用 Sail 类型检查器、Isla 插件的 `c` target，比对旧新 IR。两个脚本均不写生产模型。

冻结运行的输入、插件副本、完整命令、日志和结果在根目录 `isla/target/float-solve-evidence/unified-backend-bindings/20260927/`。最终表为 `candidate-final/bindings.json`、`candidate-final/bindings.tsv`，67 条旧 CPP 策略绑定为 `candidate-final/riscv-policy-cpp-boundary.json`，验证结论为 `verify-final3/result.json`。当前 `ieee_fp_primops.sail` 的 `SYMBOLIC` 门控仍在候选中；门控与生产接线由后续统一实现阶段处理。

190 条 typed 声明中，186 条 native FP 候选建议 `cpp: "sail_<Sail名称>"`，但 C++ ABI 和链接尚待 P0 验证。其余 `ite`、`strict_and_bool`、`strict_or_bool`、`isla_bool_to_bit` 保留原 c 原语，C++ 侧建议使用独立的纯 Sail 函数体片段。四工具的小探针已生成 C++ 并编译对象文件，覆盖 bits32、bits128、record 与 Bool；没有运行该对象。`undefined_float*` 仍为 `impure`。当前调用闭包涉及 101 条 typed 声明、45 个 FP 原语与四工具；其余接口不被删减。八条 `from_signed/from_unsigned` 的公开输入仍为任意 `n>0`，八条 FP→128 位整数出口为独立待完成边界。表中的 native CPP 名称是建议，不能据此宣称其 ABI、数值合同或链接已通过。

重跑时在仓库根目录设置 `BINDING_INPUT` 为上述冻结目录、`BINDING_PLUGIN` 为其中的 `input-plugin.cmxs`，然后分别运行：

```sh
python3 agents/float_support_review/tools/unified_backend_bindings/generate.py \
  --source "$BINDING_INPUT/input-ieee_fp_primops.sail" \
  --calls "$BINDING_INPUT/input-native_calls.tsv" \
  --policy "$BINDING_INPUT/input-softfloat_interface.sail" \
  --output "$BINDING_INPUT/candidate-rerun"

python3 agents/float_support_review/tools/unified_backend_bindings/verify.py \
  --source "$BINDING_INPUT/input-ieee_fp_primops.sail" \
  --calls "$BINDING_INPUT/input-native_calls.tsv" \
  --policy "$BINDING_INPUT/input-softfloat_interface.sail" \
  --candidate-dir "$BINDING_INPUT/candidate-rerun" \
  --plugin "$BINDING_PLUGIN" \
  --output "$BINDING_INPUT/verify-rerun"
```

输出目录必须为空。验证只证明 Sail 声明与 Isla `c` 绑定保持原样；C++ 编译、ABI 和数值实现需由 P0/P1 的独立测试覆盖。
