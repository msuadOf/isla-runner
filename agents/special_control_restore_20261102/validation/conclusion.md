# 特殊值显式分支：定向验证结论

当前源提交 `a9fd9476fc1bf471070a38e01ee9233d10d742d3` 的128位VLEN新IR，56项任务全部通过；实际生成156条JSON、3518项断言无失败。单任务2.468～53.174秒，无超时、错误或截断。

这证明所列定向输入的执行与生成结果成立，不等于全域性能或全模型控制流完整覆盖。

|范围|实际结果|
|---|---|
|FLEQ H/S/D，各sNaN/qNaN|六任务各8条；normal/normal、左NaN、右NaN、双NaN均有实际输入，fflags与非x0比较结果正确|
|半精度/双精度sqrt|正1返回1；负1返回canonical NaN并置NV|
|普通转换/向量比较/宽归约|VFUNARY0、FVVMTYPE、FVFMTYPE、RFWVVTYPE固定opcode，mask1/2实际结果与NV来源正确|
|BF16真正融合边界|VV/VF两边界五RM共20任务：独立SoftFloat FMA结果/flags一致，并与独立MUL后ADD的(result,累计flags)不同|
|BF16三来源sNaN|向量源、另一向量/标量源、累加器分别单独置NV；JSON记录实际初态与结果|
|BF16多lane异常累计|mask1→NV16；mask2→OF\|NX5；mask3→21；mask0→0；完整目的组与其余VR守恒正确|
|BF16 vl0|含sNaN源时无活动运算，不产生异常，目的保持|
|BF16窄/宽转换|mask1活动normal、mask2活动sNaN的结果与NV正确|

完整任务、命令、IR/程序/配置哈希、独立oracle逐lane输入输出及全部断言见 `runs/`、`final.json`、`summary.json`。旧IR红测与包装预检保留在 `old-probe/`，不混入新模型PASS。

原FLEQ_H qNaN旧IR只生成normal/normal和左NaN，两组各2条；当前新IR新增右NaN与双NaN两组，六任务三格式均核实。

正式 `make solve-FLEQ_S` 入口使用同一新IR、同一冻结程序及定向配置复验，3.692秒退出0、summary finished、8条JSON的四种左右NaN组合与结果/flags正确。该入口禁用更短路径预算，外限及SMT均7200秒，跳过已冻结程序的重复build。

正式入口8条JSON与当前BF16 VV/VF融合各1条，共10条实际指令的三表示均经GCC与Clang汇编并提取字节，60/60核对通过，见 `toolchains/results.json`。
