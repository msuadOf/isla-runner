# 收敛模型 IR 与输入封存

受测模型为独立工作树 `.worktree/sail-riscv-float-converged-20261103` 的干净提交 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`；runner-float 的 Isla 仍为干净 `42000be47596ec088623881d03c0eadc5cf0ba27`。生成命令：

```sh
python3 agents/float_review_closure_20261102/validation/generate.py --model .worktree/sail-riscv-float-converged-20261103 --commit 0f7b8fbc6724103f91f929ef6918f123df75d6c9 --batch model-converged-0f7b8fb --cpus 31,60 --memo-from model-e9d69d2
```

启动前CPU31/95和60/124同胞的一秒利用率均约0–5%；避开214正式批次CPU35/38/49/54。ordinary strict和RV64 V128、RV32、RV64 V256/V512四配置SYMBOLIC均退出0、`source_unchanged=true`。五份memo只按配置从e9已审核缓存独立复制，复制前SHA一致、inode不同，源未变；各次输出缓存SHA见driver记录。`independent-input-audit.json`核166个已跟踪模型文件和149个工具/配置文件，所有工具ctime早于生成开始，受测源码目前未变。模型全树1011文件清单SHA-256 `171176e54b221013d12243b921ccecc41f502d137db99e1e81c85513cb6f013e`；Isla源码1021文件清单SHA-256 `8aba2ee239e602d615e970bf03b45490947fe4ef7e0912c149bf2b20c2c80c00`。

四份实际IR SHA-256：RV64 V128 `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`、RV32 `e17c4fe18552f8ce219b35f846c4c1a2c530dcad0ac9fc8f10d0da2604c3fa4e`、RV64 V256 `47ba73418d6dcb1b1e86db7680ce4df9508e7885a02096e25e213c2c3b2c05e1`、RV64 V512 `2bdea17d36c64545254f50cc5a6902e570a1fea682de3f7c062bf641a85a62a9`；默认RV64是V128同字节别名。

77jobs定向输入 `validation/inputs.model-converged-0f7b8fb-itrace.json` SHA-256 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e`，原`run_clause.py` FLEQ_S dry-run退出0。另封FLEQ_S/C_ADDI4SPN两入口输入 `validation/inputs.model-converged-0f7b8fb-two-clause.json` SHA-256 `0a29115104b44f25924ddb37961b4dfd5967a42a8035bf9b33ac56cdecb7ae18`；两项由独立final harness副本dry-run通过，待其独审后正式运行。

根Isla永久checker SHA-256 `9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf`，README SHA-256 `d22a5f296534f4fbd44151dabbcb337eac7c1b9e766c653881c3c63caf010b87`。新四IR checker与special检查共8次退出0，旧e9 checker快照对新IR以及新checker对e9 IR均退出1；7项原因、NV/DZ、窄饱和及整数包装负变异全拒。独立Sol审查另列，不以这些静态检查替代实际数值、Make或完整Clause预算。
