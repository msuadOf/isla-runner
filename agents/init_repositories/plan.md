# 依赖仓库初始化脚本计划

状态：已确认并实施。

## 目标

新增 `scripts/01_init.sh`，从空的根仓库工作树初始化 RISC-V 分析链路依赖：`isla`、`sail`、`sail-riscv`、`assembly-gen`、`difftest`，以及 `difftest-xiangshan/xiangshan`。

## 设计

1. 把 URL、目标分支和唯一的 Sail 固定 revision 集中声明在脚本顶部，默认使用 HTTPS；可通过 `--ssh` 切换 GitHub SSH URL。
2. 目录不存在时执行 `git clone --branch <branch> --recurse-submodules`；clone 失败立即退出，不使用 Makefile 中会吞掉错误的 `-git clone`。
3. 目录已存在时先校验它是 Git 仓库、`origin` URL 与预期 GitHub 仓库一致且工作树干净，再 fetch、checkout 目标分支并 `git pull --ff-only`。Sail 继续验证其固定 commit 属于 `origin/sail2`，再 detached checkout 到该 commit。发现未提交修改、remote 不匹配或不可 fast-forward 时 fail-closed，不覆盖用户工作。
5. 脚本只准备源码，不安装 opam/cargo/Python 依赖、不生成 IR、不应用 `sail-riscv.patch`。这些有副作用的步骤继续由独立构建命令负责。
6. 更新 README 的最小用法和行为边界，并以 `bash -n scripts/01_init.sh` 和 `--help` 做静态验证；不在本机执行真实 clone/pull。

## 当前来源与复现边界

| 目录 | 远端 | checkout 分支 |
| --- | --- | --- |
| `isla` | `ariscv/isla` | `dev-isarch-runall-ext` |
| `sail` | `rems-project/sail` | `sail2`，随后固定为 `446fb477c508853595ccc937ed60765aa685ae31` |
| `sail-riscv` | `msuadOf/sail-riscv` | `isla/symbol-excution_6_14` |
| `assembly-gen` | `msuadOf/assembly-gen` | `dev` |
| `difftest` | `msuadOf/difftest` | `dev` |
| `difftest-xiangshan/xiangshan` | `OpenXiangShan/XiangShan` | `kunminghu-v3` |

`assembly-gen` 的本地领先 commit，以及 `isla`、`sail-riscv`、`difftest`、XiangShan 的未提交修改，不在远端初始化脚本可复现范围内。脚本会把干净工作树 fast-forward 到目标分支的远端最新提交；要完整复现当前状态，必须先将这些本地内容提交并推送，或另行保存为受控 patch。
