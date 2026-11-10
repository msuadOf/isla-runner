# 根float提交前独立核验

结论：**PASS_STAGED_CONTENT_AUTHORIZED_FOR_ROOT_COMMIT**。已逐文件核对暂存的2171个变更路径，未发现阻断；主agent可以复制并暂存本记录两文件后提交。

- 两个160000 gitlink准确固定模型`0f7b8fbc6724103f91f929ef6918f123df75d6c9`与Isla`591693df2bc32019ea300511509ed683df09522e`；对应正式远程分支已独立回读一致。
- 清单2157个文件、25557577字节逐项核对主工作区、float副本与Git暂存blob，全部一致，无symlink混入。变更路径严格等于清单、两个索引、组件发布记录、九个根文档/版本文件和两个gitlink。
- 最终315项的result、command、config和实际output各315份均已暂存；已签最终审查、交付报告和memory交接的精确哈希保持。
- `specs/topic-version.json`准确保留限定矩阵、历史53次超时和OPEN延期范围。受测程序来源仍为42000be，146个Rust/Cargo/.cargo文件与最终Isla逐字一致；没有冒称591重新构建。根政策/版本文件暂存diff检查通过，三个根状态文档仅追加本轮结项；原始补丁证据保持已签字节。

逐项哈希、范围和加入本记录前的暂存树见[机器记录](final-root-refseal.json)。本核验不新增动态测试PASS，也不扩大全77预算或控制流覆盖承诺。

本记录在所审2171路径之后加入，不在自身写入包含自身的根commit/tree。根提交和推送后，真实SHA与独立远程回读另存本地外部收据，不为收据再创建根提交。原[最终限定签收](../review/acceptance/final-signoff.md)保持原封字节。
