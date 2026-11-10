# 内存协同正确性修复与独立审阅

2026-11-02。**本轮F1–F5已修复并通过独立Sol复审，无未关闭P1/P2；保留原有结构。** 用户要求的实施、集成验证及实施后独审均已完成。[独审报告](independent-review/report.md)限定本轮修复的接纳范围，不代表整个指令集或硬件验收。

## 修改与结构

| 原问题 | 最终行为与实现位置 |
| --- | --- |
| F1 concrete/数组初态分离 | MemoryCallbacks装入已知快照，普通RAM具体/符号读取共享SeqMemory当前数组；保留稀疏非零页表初态、零缺省、写后读及普通RAM地址回绕。Custom/Constrained继续专属分派，无法确定的混合后端访问明确报告错误。 |
| F2 GPR初值漏导出 | RV32/RV64沿Target原必输出机制，从同一最终Model补齐x1–x31；现有消费者在pre-memory等前导后恢复这些GPR。 |
| F3 早退不清零vstart | 模型process_vlre/process_vsre仅在原正常早退出口先set_vstart(zeros())再退休，保留非陷阱策略和其余循环。 |
| F4 返回值仍含符号编号 | 同一最终Model通过get_val递归具体化ret_val，符号形式仅用于失败诊断。 |
| F5 必需字段失败被吞 | 必需地址、读值、写数据、独占结果及汇编/编码字段求值失败进入incomplete diagnostics，summary.partial且不进gen；正常无解/非法编码过滤与首写自由初值null仍按各自原义处理。 |

没有另建执行器或重写Sail的PMA/PMP。普通写Bool是非必需字段；SC平台响应抽象与寄存器完整后态不在本轮扩展范围。

实施细节及精确命令分别见 [内存](memory/report.md)、[见证输出](witness/report.md)、[模型和IR生成](model/report.md)。最初过程中的编译作用域错误、页表深Store链栈溢出及生成器调度冲突都保留在过程记录，不能以这些中间状态的GREEN替代最终验证。

## 来源与IR同步

Sail-RISC-V基线为c70482a7、Isla基线为bdd047bc，工作树修改尚未提交，未移动分支或父仓gitlink。起点记录及原有patch见 [before.json](before.json)；既有scripts/run.mk补丁逐字保留，README原有修改保留并修订本轮合同说明。

普通及SYMBOLIC全模型严格检查均通过。四配置从冻结的159个模型文件实际生成，五个生产IR路径已同步；`ir/provenance/manifest.json`明确标记model_dirty=true，提交字段是补丁前基线，另保存完整模型补丁及SHA256。源文件、生成配置及五IR哈希核对见 [安装记录](installed-ir-check.json)。没有手工修补生产IR。

唯一受影响的vmtype预算start_line 652→658、end_line 673→679；79份配置、130个region及22处注释锚点核对通过，详见 [预算验证](workaround-check.log)。strict=false下的基准IR哈希告警按既有约定保留。

## 验证证据

- [RED集成](red-integration/checks.json)：旧Release及原IR确证同址零快照被符号地址绕过、x5/x6等初态遗漏及异常返回值Sym。
- [vstart RED/GREEN](model/report.md)：VLEN128、evl16，vstart为15/16/17/全1，load/store共8项；RED正常活动对照2通过、早退6失败；修复后8/8正常退休且后态清零。最终v4二进制与已安装IR再次核对 [8/8](model/green-final/result.json)。
- [最终完整IR集成](final-integration/checks.json)：最终v4 Release及已安装默认IR的12组指令、19条JSON，65/65断言；覆盖Concrete固定/符号AMOMAX、sd x5/x6、AMO/SC源x6、异常地址、segment越界、vstart及压缩访存。11组finished、1组既有动态宽度限制partial。
- [GCC/Clang编码核对](assembly.json)：19条JSON文本共38/38通过；最终19条文本/编码多重集完全相同，见 [最终核账](final-assembly-equivalence.json)。
- 消费端既有Python测试80/80通过，日志 [pipeline-before.log](pipeline-before.log)；消费源码未改，新的GPR前导恢复另由集成断言核对。
- 正式`make build-isarch`最终v4通过；官方Z3链接、执行器及四个生产Rust文件哈希见 [最终构建来源](final-build-inputs.json)。最终完整Isla lib **163/163**、格式及diff检查通过，日志为 [isla-unit-v4.log](isla-unit-v4.log)、[构建日志](release-build-v4.log)、[格式日志](format-final-v4.log)。前版161/162仅作过程证据。
- 正式 [make solve-C_MUL](make-final/result.json) 退出0、summary.finished、1条gen，错误/采样/超时/未完成计数均0。输出在独立目录，`-o build-isarch`仅跳过已经实际完成的正式构建，不替换执行脚本。

正式make MRET冒烟退出0并有4条gen，但summary为partial，1条Poison未完成终态；该产物只证明入口运行，没有被记作全路径PASS。自由地址store仍有一条既有SymbolicLength路径，summary正确partial，详见对应集成JSON。两项都未被隐藏为finished。

## 独审与边界

独立Sol未参与实现，先审当前diff和调用者，再核对证据。独审先后指出汇编/编码求值与编码回环错误出口的诊断缺口，已交回实施者沿现有错误记录机制补齐，最终复审和独立探针见 [独审报告](independent-review/report.md)。

Sol使用最终v4二进制独立运行两组完整IR探针，分别验证Concrete零快照与符号AMO、sd x6初态和重放顺序，均退出0且finished；命令/哈希/断言见独审目录`.tmp/`内的independent-check.json。上述结果为其亲自运行，区别于对主agent测试日志的核账。

本轮没有运行硬件、完整指令集覆盖或完整LR/SC序列，也没有新增全部寄存器后态合同。Concrete初态的运行期write_byte扩展需先同步数组状态；当前MemoryBuilder在安装回调前完成预置，不在安装后调用该API。基线Excluded顶端回绕范围检查等其他议题不因本轮普通RAM回绕测试而得到验收。
