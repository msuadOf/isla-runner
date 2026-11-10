# 56cc 原生源码目录实施

授权与范围见 `../../solve-fix-architecture.md` 的“原生 Sail 源码目录的实施合同”。本目录独占实施，产物仅写 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/` 新试次。

## 步骤

1. 同冻结 compiler-libs 解析 Sail 的 `Parse_ast.ml` 与 `Ast.ml` 类型声明，生成 constructor/field schema 和穷尽原生 OCaml serializer；生成器不解析 Sail 模型语法。
2. raw 工具逐冻结 `.sail` 调用 `Initial_check.parse_file`；typed target 采用空 rewrites，普通/SYMBOLIC 分进程。所有原生构造子与子字段都被机器保存。
3. 多语法 fixture 与未知类型/遗漏字段/错误来源/域混合负控先行。
4. 复用实际 56cc 项目、宏、配置、库；按真实 pre-initial 文件集核输入，顺序导出两模式。
5. 建立结构节点、完整 SourceLoc、类型和调用分类，按 source hash/span/结构路径匹配。所有没有具体来源的对应列 OPEN。
6. 从精确 constructor clause/mapping arm 而非全 execute 起点计算闭包，对账历史 172 roots / 795 候选。
7. 冻结 manifest、差异、未决与验证；导出成功不推出 denominator_complete。

## 产物

`inputs.json`、`constructor-schema.json`、raw/typed AST JSONL、节点/调用/来源关系 JSONL、roots、legacy-diff、OPEN 清单、manifest/index。抽象 compiler 环境只通过公开 API 导出必要信息；不以 marshal 内容替代结构化 AST。

## 当前实施与验证

已实现原生 schema 提取、穷尽 serializer、保留原 target hooks 的两域 exporter、实际文件选择核验、逐字段 payload 校验和结构索引。`attempt-005` 两域成功；raw 库存 223 中 222 成功，未被两域选中的 `instr_kinds.sail` 语法失败保留。

v1 有限导出包已通过独审，入口见 [README](README.md)。多语法 fixture、两次真实编译的错误 target/宏域负控，以及构造子、少孩子、private、module、bits 和 span 负控已检出；五种原生位置构造子另验。BF 消费方已接手从完整 typed 结构构建分母，不把索引生成数计为新增覆盖。

v2 在独立 attempt-006 补公开 uannot attributes/instantiations 与 MP/P/LE 应用 Env 分类，两域均成功并通过完整 schema 校验。与 v1 逐行对照确认 raw 完全相同、剥离新增投影后既有完整树相同。扩展 fixture 与 11 项负控通过；完整 raw→typed 来源关系、目标声明归属及精确 root 闭包仍由分母消费者单独闭合，本工具不据导出或分类计数赋予覆盖 PASS。
