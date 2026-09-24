# V 扩展去重后 IR 与执行限制配置同步计划

## 目标

让当前 Sail-RISC-V V 扩展修改生成的 RV64、VLEN=128、ELEN=64 IR 与 `isla/scripts/run.mk` 使用的严格执行限制配置一致，恢复 `make solve-MASKTYPEI` 及全量 `make solve` 的配置校验，并保持各 region 的原有语义范围。

## 已核实的基线

- `isla/rv64d.ir` 的 SHA-256 为 `7c626989a03056c43c67c81de8f40f611cef4c43ed1069a81526b37856d7e37b`；`isla/configs/workarounds/` 下 79 份 TOML 全部以 `strict=true` 绑定此哈希。
- 当前三份已修改 Sail 源文件与之前性能测试保存的 `new-src/` 快照逐字节相同；那次 VLEN=128 新 IR 的哈希为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。正式更新时仍需从当前源码重新生成并以产物哈希为准。
- 21 份配置的 67 个 region 指向本次改动的 `vext_arith_insts.sail`、`vext_control.sail`、`vext_utils_insts.sail`；其中 `MASKTYPEI` 的范围已知应从 `1448:4–1458:5` 移到 `1367:4–1377:5`。其余 region 要逐一核对源码锚点。
- `isla/rv64d.ir` 是被 Git 跟踪的正式产物；只更新 TOML 而不更新它会使当前默认 `make solve` 立即失配。

## 实施步骤

1. 先写校验测试，覆盖每份严格配置的哈希与目标 IR 一致、region 起止点有效，且迁移前的旧配置对新 IR 会报哈希不匹配。先确认旧状态下测试失败。
2. 使用当前 `sail-riscv` 源码和 RV64/VLEN=128/ELEN=64 配置重新生成 IR，核对生成日志、配置参数及哈希；更新 `isla/rv64d.ir`。
3. 将 79 份 workaround 的 `ir_sha256` 同步为新产物哈希。根据旧、新 Sail 源码的对应代码锚点迁移 67 个受影响 region 的行列坐标及相关注释；其他文件中的 region 保持原坐标，并逐项验证所指源码。
4. 运行校验测试、配置解析测试和 `git diff --check`。用新 IR 验证至少 `MASKTYPEI` 与其他绑定配置的 clause 能通过 strict 校验；按资源情况运行代表性 `make solve-*`。全量 `make solve` 耗时较长，实际执行情况在状态文件中如实记录。
5. 在 `status.md` 记录产物哈希、配置数量、迁移结果、命令与测试结论，并将可复用的代码事实写入 `agents/findings.md`。

## 边界

- 保留 `strict=true` 与原有限额策略；不通过放宽哈希校验规避问题。
- 保留工作区其他未提交修改和历史 `output/`；校验输出使用独立目录。
- 不修改 Sail 模型语义或 Isla 执行器逻辑。
