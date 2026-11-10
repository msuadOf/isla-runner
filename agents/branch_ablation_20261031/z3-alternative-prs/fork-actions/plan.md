# Fork预编译包发布

用户授权启用msuadOf/z3的GitHub Actions并发布预编译二进制。Actions设置已enabled/read默认权限，但fork尚无已注册workflow。原release流程包含多种语言包及draft发布，nightly依赖上游app密钥，不直接使用。

新增fork-binaries.yml和scripts/fork_binary_release.py：main源码/打包流程变化自动触发、也支持手动；原生Linux x64/ARM64、macOS x64/ARM64及Windows x64；CMake Release构建CLI/共享库/test-z3，fpa回归、安装、归档解压后FP枚举SAT/枚举值/共享库加载/header存在检查，校验和与构建provenance。无Python/Java/.NET绑定，C/C++接口与CMake/pkgconfig随安装打包。仅发布job授予contents:write，使用GITHUB_TOKEN，无外部密钥/包仓库发布。

验证：本机Linux打包全链路smoke与workflow lint；提交到fork main后触发Actions，回读五平台状态；若发现失败最小修复并重新跑相关workflow。产物不安装生产Isla，不改模型/gitlinks，不将fork工作流塞入上游A/B PR。
