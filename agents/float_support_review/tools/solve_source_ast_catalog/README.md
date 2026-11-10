# Sail 原生语法导出器

实施合同见 [架构记录](../../solve-fix-architecture.md) 的“原生 Sail 源码目录的实施合同”。本工具以冻结的 56cc 源码、编译器与真实 target 为输入；不修改安装、生产模型或旧证据。

## 数据入口

证据根目录为 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/`，相对于仓库根。

- `attempt-005/`：原始完整 raw、普通 CPP 和 Isla SYMBOLIC AST JSONL，以及实际命令、文件打开记录、schema 和 exporter 源码快照。
- `catalog-003/`：实际文件选择证明、逐字段语法校验、三个模式的节点索引和无物理来源节点清单。
- `exporter-package-v1/manifest.json`：有限语法导出包的绑定和边界；最终以该文件列出的 fixture 版本为准。
- v2 使用独立 `attempt-006/`、`catalog-004/`、`exporter-package-v2/`；`projection-comparison-v2/` 核对 raw 逐字相同，移除新增公开投影后两域全部既有 payload 与 v1 完全一致。消费前仍须绑定对应独审。

每个 AST definition 是一行 JSON，`ast` 完整保留原生语法树。variant 为 `{"type": "Ast.exp", "tag": "E_aux", "args": [...]}`，record 使用原字段名，tuple/list 为数组。`Parse_ast-schema.json` 和 `Ast-schema.json` 定义全部构造子、参数顺序与 record 字段。未知构造子、少孩子或 record 字段不完整时，校验失败。

索引 `*-nodes.jsonl` 通过 `ast_byte_offset` 定位完整 JSONL 行，通过 `structure_path` 定位该行 `ast` 内的节点。`parent_structure_path` 指向最近的已索引语法父节点，参数位置及数组次序保留在路径中。索引只包含报告中 `index_types` 列出的语法 wrapper；完整树是其余字段和结构的权威。

源码 Range 为原文件 UTF-8 字节的半开区间 `[begin,end)`；行从 1 开始，列为从 0 开始的字节列。位置的 `Generated/Unique/Hint/Unknown` 树原样保留，Hint 的两条来源路径分别列出。物理范围逐一核对源 hash、字节界限和行列。空文件名、未知位置或生成位置仍可能没有物理来源，不能据此推断不活动或不可达。

`inputs.json` 的 `source_aliases` 将实际编译器库路径映射到逐文件同 hash 的冻结库。文件选择依据成功的 `openat` 与 pre-initial 项目文件列表共同确认；不从 typed AST 的位置有无推断。223 个 raw 库存中 `instr_kinds.sail` 有明确语法失败，两域均未选中。普通域选中 200 个文件，SYMBOLIC 域选中 201 个，额外为 `isla.sail`。

## 语义边界

typed 导出位于 frontend descatter、配置改写和抽象配置实例化之后，initial rewrite 与 backend rewrite 之前。普通 CPP 域保留原命令的 runtime config；Isla 域保留其独立配置。两者不能合成一个未经预处理的源码域。

v1 的 `tannot` 只导出公开 API 得到的 module 摘要、type AST 和展开后的 type AST。注释正文、uannot 属性、expected/monadic/instantiation 以及完整 Env 未导出。表达式 `meta` 是额外投影；schema 校验不为其全部语义背书。v1 fixture 已核列定的 Bool/bits、constructor/callee 样本，其 mapping pattern 的 Env 分类未导。

后续 v2 候选通过公开 API 补充 uannot attributes（含原始 overloaded 属性）、instantiations，以及 pattern、mapping pattern 和赋值左侧应用的 Env 分类。它单独构建、运行和冻结；不修改或自动替代 v1 证据。callee 所属声明的 module/visibility 仍须联立原生声明，不能把调用点当前 module 当作目标所属 module。

private 需联立同 module、同 id 的 `DEF_val`；不能因为 typed 函数体的 visibility 为 Public 就丢掉 private。当前编译器拒绝同项目两个 module 的同名 private 自动签名声明，该真实失败单独保留；没有把它写成成功 fixture。

原生语法导出成功不证明完整 source 对应、callee 闭包、旧 BF 795 候选分母、动态覆盖或静态不可达。`denominator_complete` 和 `source_branch_closed` 均为 false，后续消费者分别独审这些门槛。

## 验证入口

```sh
python3 -B -m unittest discover \
  -s agents/float_support_review/tools/solve_source_ast_catalog -p 'test_*.py'
```

`build.py` 在独立目录构建，`run_full.py` 用冻结原命令顺序运行三域，`catalog.py` 生成索引。`verify_exporter.py` 用实际冻结 binary 跑多语法 fixture 和负控，`verify_locations.py` 独立重编同份位置 serializer 验证五种原生位置构造子。运行参数与日志以产物 manifest 为准，各次输出目录必须新建。
