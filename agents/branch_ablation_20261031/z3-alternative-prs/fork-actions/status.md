# Fork二进制发布Actions：已启用、首次云端构建进行中

main提交32f4df28新增fork-binaries.yml与fork_binary_release.py；Actions enabled=true，workflow id403325360 active。首次[运行41279354596](https://github.com/msuadOf/z3/actions/runs/41279354596)由main push触发，当前见run-initial.json，不将排队/构建标为发布成功。

覆盖Linux x64/ARM64、macOS x64/ARM64、Windows x64；native CMake Release，输出CLI、共享库、C/C++headers、CMake/pkgconfig、license、BUILD-INFO及SHA256。每包fpa回归及归档解压后FP枚举SAT/枚举值回读、共享库加载/version和header检查。只在所有build成功后用GITHUB_TOKEN发布源码SHA专属release（fork-<12sha>）。不需要用户secret，不发布PyPI/Nuget/Java包，不改变生产Isla。

main源码/构建配置/此工作流变化自动触发，也支持手动workflow_dispatch。workflow只授予默认contents:read，publish单job授予contents:write；fork/repository和main ref保护。Linux Ubuntu24.04；macOS13.3+；Windows需要VC++2015–2022 x64运行时。可下载页为https://github.com/msuadOf/z3/releases，首次包尚待云端成功。

本机验证：Linux本地既有A Release构建下，打包/安装/解压迁移/FP枚举/共享库加载PASS；独立子进程加载共享库避免Windows临时DLL文件锁。fpa PASS；actionlint1.7.12退出0（关闭shellcheck/pyflakes）；YAML解析/5矩阵/权限核对通过。未宣称本机重编译新CI提交或验证macOS/Windows包；这些交给首次云端矩阵。证据见local-package.log、implementation.json和run-initial.json。

## 首轮云端错误与修复

原32f4df28任务41279354596失败：打包脚本指定z3为构建target；实际CMake target是shell、输出文件名z3。本机旧Ninja可按文件名构建掩盖了Make/VS差异。5292580e5已改用shell；全新Make配置的targets列表含shell/libz3/test-z3，且本机已重编译当前提交并重新完成fpa/打包/解压smoke。原失败日志保留linux-initial.log/macos-initial.log；不把原首次排队描述作为PASS。

最新[Actions41279556474](https://github.com/msuadOf/z3/actions/runs/41279556474)自动触发，状态见run-revised.json；产物发布仍待五平台构建成功，未声称已有下载包。

同一目标名错误也影响此前公共复现README/issue构建命令，已同步将两处--target z3改为--target shell；证据分支新增972455591，仅文档两行修改、实验输入与数据不变。issue评论原位更新并逐字回读，链接固定新证据commit，历史2dec1be仍可查。

## 首次正式发布已成功

Actions41279556474的五平台build与publish均success，已发布https://github.com/msuadOf/z3/releases/tag/fork-5292580e5840（5包+5校验文件）。本机已下载Linux x64包校验通过，并用Isla隔离副本完成default FLEQ_S运行，详细证据见../isla-integration/status.md。此前pending状态保留历史。

## 2026-11-02现行方案修订

用户要求改用维护者方案；main现为d5aa015a24e266578164157d7b0268c2babf3008，采用已合并PR11506最新qffp内dt2bv方案，原全局A前处理已移除。旧A提交/包/性能保持历史范围。新版CI正在重建，详见[当前方案与证据](../../../z3_maintainer_route_20261102/status.md)。
