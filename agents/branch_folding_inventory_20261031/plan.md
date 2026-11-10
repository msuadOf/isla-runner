# 分支合并改动盘点

目标：只读盘点当前float模型相对4f2ac293的显式分支合并，包括ITE、严格布尔、onehot和掩码选择；区分局部路径、单函数数值验证、整Clause性能及覆盖证据。不实施批量回退。

入口：nan_unbox恢复记录、float独立review、solve-fix-performance及当前模型源码。输出逐类位置、被合并条件和历史证据适用范围；原工作区不变。
