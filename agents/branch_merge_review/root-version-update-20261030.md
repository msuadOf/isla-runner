# 根仓float/memory版本更新（2026-10-30）

用户要求更新根仓两个议题分支并commit，已在各自干净独立工作树完成。

- float根提交bb9d2710f98109297a0804addf465e681140376d：Isla b0138b7c2ff8addb81f68f42669600a2a9c2b813（feat/float-support）；Sail-RISC-V18389a897264eede4e8c6cc791f3700974def840（feat/sail-riscv-general-float-by-model-20261022）。
- memory根提交173120783f6ad5a18d673818510c7ed4b64bf7c7：Isla保持47ac90cd53d4542179c3c255dc0db34886f10ec6（feat/memory-consistency）；Sail-RISC-V更新1fa931176a64b3fb8f68b7f0d502f090f6a6ebb2（feat/sail-riscv-memory-by-model-20261022）。

两条分支各自提交gitlink、specs/topic-version.json、版本说明及TODO/RESULTS更新；不复制原master工作区其他dirty文档。组件对象只从本机源仓fetch，正式origin URL不变；未推远端，未重新核实GitHub可获取性。

验证：两套manifest commit=gitlink=实际checkout；子模块无dirty；IR SHA256等于manifest；分别在runner-float/runner-memory运行./init.sh --submodules-only退出0；git diff --cached --check通过；提交后两根工作树干净。原master的init.sh检查因原isla HEAD与原gitlink不一致而按约定退出1并拒绝更新，无状态修改；该检查不属于这两套议题版本的成功证据。

本轮没有重新生成IR、编译或运行成套符号执行/硬件测试；Sail-RISC-V源码与已提交IR的精确重生关系仍未新增证明。原master、原isla/sail-riscv工作树、未提交改动和旧stash均保持。相关版本入口见根specs/topic-versions.md及两分支自身manifest。
