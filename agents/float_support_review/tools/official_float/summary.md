# 官方 make 浮点非访存批次摘要

固定旧候选 IR `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75` 的77项目标均已记录退出结果。底层39项退出0、37项外限124、1项SMT查询超时退出1，整组未通过。退出0仅为运行层证据，不代表数值/flags语义PASS，不适用于后续类型复用候选。

完整77行结果、参数、原始证据位置和Astra复核结论统一见[续跑记录](../../official-continuation.md)。复跑方法见[README](README.md)，目标集合见[targets77.txt](targets77.txt)。
