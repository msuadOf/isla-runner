# Z3统一求解策略源码调查

目标：读取与当前libz3一致的4.16.0源码，解释qffp/default/smt/qfaufbv的真实流水线差异；验证不按workload手选策略的统一候选，关注7200秒Clause预算内完成性。

范围：Z3 tactic注册、fpa/qffp、smt默认策略、QF_AUFBV流程、fpa2bv与模型转换；当前Isla策略接入只读。先源码与单查询受控实验，完整Clause/数组/枚举/SAT/UNSAT/model-eval另列验收。不承诺任意SMT任务有统一最坏时间保证。只写本专题目录，不改生产分支。
