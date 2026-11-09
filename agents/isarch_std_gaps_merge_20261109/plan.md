# std-gaps 正式合入 isarch

用户已授权合入完整 feat/sail-std-gaps。目标模型基线34903a1e，源7d7e76f3；Isla87895be0，runner d1e29e11。

仅在独立副本整合，不动原 dirty 工作区或备份。热点为模型4份V源码与24份workaround、Isla当前v128 IR与来源、runner gitlink和验证记录。保留x0与分页提交完整历史。

步骤：保留合并提交；普通与SYMBOLIC严格类型检查；检查当前源码区域并按实际模型重生v128 IR及别名；运行path merge/executor、Python全量和原生fuzz smoke；定向核对segment组界、vstart及全寄存器早退；最后固定三仓提交、生成bundle和只允许快进导入的收尾脚本，源分支成为祖先后才删除。

验证与实施分别记录。原Git元数据预计只读；如受限，交付Claude在沙箱外执行的--apply脚本。只更新当前v128 IR，其他历史IR不继承新模型PASS。7项预算1→0按源提交保留，不能把smoke通过解释成向量全覆盖。
