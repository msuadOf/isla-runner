# 最终0f7b8fbc模型的315项定向验收版本门

最终模型提交 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`，独立工作树 `.worktree/sail-riscv-float-converged-20261103` 干净。相对已验 `e9d69d2f28586c089244c8e37ee4c904c5114458` 的第一父提交链为 `3d9ceebb8ae81b45ccafcde7cab81c0ab5b49bd8` → `7eb4bd5c137c500209678f2f6eb007b572179b74` → `0f7b8fbc6724103f91f929ef6918f123df75d6c9`。只变 `model/core/ieee_fp_exceptions.sail`、三个 `model/extensions/FD/softfloat_symbolic_f{16,32,64}.sail` 与 `model/extensions/V/vext_fp_utils_insts.sail`，Git `diff --no-ext-diff e9d69d2 0f7b8fbc` SHA-256 `01ad2e7f97de170aa7e400979b5c00af49e3f473e8b65946d16faa2fe39c74ae`。

`run_directed.py` 从已签 `8475d90d35d3d52195bbeb6bab4ab5cfe28d669536cb82aa61610c55e2efe311` 增加上述固定提交链、文件集合与差异哈希守卫，脚本新 SHA-256 `12ea69e349660ccdb79d129f41968d35657a67502c70b028082a2053c9325cf7`。精确变更 `guard-final-0f7b8fbc.diff` SHA-256 `06c5c4fe3954fb765c0964fde17344459d16098149afd191258933db2a7642df`；逆替后字节哈希恢复旧脚本。launch继续同时记录实际模型、旧独立SoftFloat预期来源 `8ad5e8e`、差异基线 `e9d69d2` 和实际delta SHA。`expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891` 不变，315条固定输入不扩充。

旧e9冻结inputs的 `--dry-run` 在新脚本下退出0，证明既有版本门未回退。正式最终IR/inputs到位后，先核新清单和脚本独立预签，再以CPU17/29新目录重新执行315条；旧e9结果不继承。当前仅完成准备，无最终动态PASS。
