# 两条源分支独立统一术语

用户要求general、float-only各自包含具体化术语调整且可独立使用，再合入feat/float-support。范围：符号值求解的命名、注释、测试名和术语文档，不改运行逻辑；延迟生成SMT-LIB2文本的materialize接口保持。

general在干净临时工作树修改后快进原分支并保全原dirty；float-only在其干净工作树直接提交；两分支各含TRANSLATOR.md及AGENTS入口。独立编译/既有定向测试后依次merge到目标，核对先前ret_val修复与runner兼容仍在。记录命令和版本，不推远端，不动父gitlink。
