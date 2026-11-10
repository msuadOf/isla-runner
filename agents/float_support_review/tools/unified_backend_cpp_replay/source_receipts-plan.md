# 单次官方回放的原 trace 哈希凭据

## 授权与范围

在 441c 原 89 条回归封包后实施。仅新增 `source_receipts.py`、对应测试及新的入口；
既有 `trace_reuse.py`、prepare、wave、sharded、冻结执行与独证保持不变。
此项不建立通用文件缓存，不改变 source、assembly、数值或 phase 的验收判断。

本轮 VFMERGE 原 trace 为 44,122,131,855 字节。冻结成功控制流在同一父进程中
包含以下六次完整哈希；worker 的分片输入不持有原 trace 绑定。

| 调用位置 | 新入口初版行为 |
| --- | --- |
| prepare 初始 target 绑定 | 真实哈希，不创建 audit 凭据 |
| 原 audit_run documents 校验 | 真实哈希并创建本 epoch 的内存凭据 |
| prepare 末尾绑定漂移校验 | 校验凭据全部绑定后复用 |
| wave 导入 base bindings | 校验凭据全部绑定后复用 |
| sharded 父输入 validate_input | 校验凭据全部绑定后复用 |
| sharded 最终完整来源漂移校验 | 强制绕过复用，真实哈希 |

目标为三次真实读取、三次受限复用；开发阶段不重扫现有 44 GB trace。
最终按实际调用日志报告次数、字节及耗时，不将进程累计 I/O 当作 trace 独占成本。

## 凭据合同

仅允许本次冻结合同列出的原 trace，凭据是不可序列化的进程内对象。
凭据绑定父 PID、单 audit epoch、规范路径、原始请求路径、实际与预期 SHA256、
scope、validator、options、完整 terminal 对象摘要及持有的只读文件描述符。

创建、复用与最终检查均比较路径与持有 FD 的设备号、inode、长度、mtime_ns、
ctime_ns。仅有相同路径或 mtime 不足以复用。创建必须来自原 audit_run 的真实
整文件哈希；首次 prepare 检查不能代为创建。其他 IR、CPP、配置、manifest
等文件继续真实哈希。

最终门必须真实重读全文件，核验字节摘要与全部身份绑定；缺少最终门或任何
漂移均不得产生全通过结论。凭据不能跨进程、跨 epoch 或跨新运行使用。

## 实施与验证

1. 先以小文件写失败测试，再实现单 allowlist、单 epoch 的凭据对象。
2. 负控覆盖同长度修改并恢复 mtime、inode 替换、符号链接替换、FD/path 不同、
   expected SHA / validator / options 改变、未创建、跨 epoch / PID、最终新读漂移。
3. 新入口用显式上下文连接六处调用，并记录真实 hash/reuse 的次数、字节与耗时。
   原先入口和已冻结工具不修改。
4. 用真实小 fixture 跑完整六调用路径，随后进行小规模真实回放。
5. 另行独审实现与负控；通过后才用于下一大包。旧运行结果不迁移。

## 尚待落实

入口需要明确标识 audit 创建门与 sharded 最终门，不能靠第几次调用猜测阶段。
新入口异常退出须恢复模块引用、关闭保留 FD，并使凭据失效。

最终门采用精确生成方案：读取并核验旧 sharded 文件的预期 SHA，要求插入位置的
精确 anchor 各出现一次，机械生成新文件。在末尾来源 drift 遍历前后分别插入
`begin_final_verification()` 与 `require_final_verified()`。生成器、原文件、新文件、
精确 diff 及 callbacks 均绑定；只允许列定插入。实际执行生成文件，不按错误消息
文本拦截 `require`。缺 anchor、重复 anchor、源 SHA 改变或额外 diff 均拒绝。
