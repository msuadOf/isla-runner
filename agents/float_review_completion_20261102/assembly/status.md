# 汇编表示合同

模块、主接线和三批真实CLI定向验证完成。五项模块测试通过；新增6个固定样例双工具链36项符合预期。真实BF16-vl0/vl1各6条（各保留2条Illegal）、C_ADDI4SPN 1条，共13条三表示、78项GCC/Clang检查符合预期，含4项预期Clang拒绝原助记符，精确.insn/.byte均逐字节匹配。压缩例保留16'h1fe0，最终Retire_Success、x8=0x403。受测binary冻结，尚不包含后续SMT统计快照补丁。详见 [报告](report.md)、[真实摘要](production-e2e/summary.json)、[独立review](review.md)。未修改系统或共享target，生产源码仅新增representation.rs，exec/mod接线由主agent完成。
