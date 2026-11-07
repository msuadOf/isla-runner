# 枚举分支 IR 更新状态

2026-11-07：五入口IR从模型 `d79d8b32` 重生完成，Isla执行器/插件源码基准 `d7c25993` 包含 `4d085b14`。来源与最终哈希通过；本机定向验证通过；**待发布**，未执行Git写操作或gitlink更新。新主IR为 `1220297d…a3ad2059`。

结果：普通严格检查、四配置生成与五入口安装；Rust1185通过/6忽略；永久IR26步、负变异104、数值315、状态300、混合JSON9、vstart8、helper4、ExecuteAs和四个定向Make入口通过。混合编码54项、Make生成27条JSON的162项编码核对通过。79配置/130区域/22锚点通过，79个旧哈希仅告警，workaround未修改。

首批IR因缺新扩展显式配置失败；按模型模板补RV64=true/RV32=false后新缓存重跑成功。315首次预检缺oracle源码副本，补齐后315/315通过；两次失败保留原件。旧 `4d085b14/bf861b3e` PASS仍仅适用历史版本。

详细版本、五哈希、逐项验证、未做和遗留见 [final-report.md](final-report.md)；复现入口见 [reproduce.md](reproduce.md)，范围见 [plan.md](plan.md)。原始日志统一在 `output/memory-enum-20261107/`。未测全域、新页表功能专用语义测试和硬件，未复跑F1/Poison归因及旧基线长尾；无新独立签收。IR/provenance仍未提交。
