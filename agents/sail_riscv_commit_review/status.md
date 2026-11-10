# Sail-RISC-V 提交审阅状态

2026-10-24：按用户要求删除本地 `feat/sail-riscv-by-category-20261019`；对应工作树保留为detached `3ea3cbaf`，未删除文件。两条20261022新模型分类分支保留。下方旧分支记录仍作为历史来源，不代表该分支引用现存。

2026-10-22：按用户要求从4f2ac293完成两条模型分类分支。`feat/sail-riscv-memory-by-model-20261022@1fa93117`两提交，分别移植segment组界和vstart策略；`feat/sail-riscv-general-float-by-model-20261022@18389a89`先4通用＋后10浮点，通用边界0de6edd1，末端完整tree等于3ea3cbaf。每提交含model文件，151路径配套保留；最终32次普通／SYMBOLIC严格类型检查退出0。初次漏带VPR测试经树核对发现，补回通用第02层后重做并复验；历史初次日志保留。两新worktree干净，原索引原始字节／两层补丁／所有旧分支与工作树／父gitlink及根仓float/memory指针保持，未push。未重生IR或新增数值／C++／硬件验收，工具链与旧fixture限制保留。[交付与逐提交索引](topics-20261022.md)、[计划](topics-20261022-plan.md)、[最终核账](topics-20261022/final-audit.json)。

2026-10-21远端分支删除：用户追加授权后，已在 `msuadOf/sail-riscv` 删除GitHub分支 `fix/zfa-bf16-assembly`，push退出0；随后 `ls-remote --heads origin refs/heads/fix/zfa-bf16-assembly` 退出0且无输出，确认不存在。初次请求经现有代理TLS EOF失败，仅在本次子进程清除代理环境后直连成功，未改全局代理或Git配置。下条仅删除本地引用的记录保留为前一步历史。

2026-10-21远端跟踪引用清理：按用户要求删除本地 `origin/fix/zfa-bf16-assembly`（原fbacdfff），未删除GitHub上的分支或操作PR。若远端分支仍存在，后续fetch可重新取得该引用。

2026-10-21分支清理：按用户要求删除本地 `feat/sail-riscv-review-20261016`（原cfde70ec）和 `feat/sail-riscv-review-20261016-readable`（原755fea6e）。原 `.worktree/sail-riscv-split-20261016` 保留，改为detached cfde70ec，文件／索引／补丁／状态不变；原主工作区163项暂存内容保留。保留功能归组分支3ea3cbaf，三者最终tree相同；未操作远端。下方旧分支交付记录按当时状态保留。[清理核账](branch-cleanup-20261021.json)。

2026-10-21：按用户要求完成独立subagent代码审阅，精确范围 `4f2ac293..3ea3cbaf`。未发现新的确证数值／最终状态回归；确认P1工具链交付缺口（普通Sail0.20.1最小C++探针失败、补丁版同输入成功）、P2三个测试入口失配。源树相同的既有C++库上，18算术包装×5RM的180000随机＋524880边界调用（含重复）结果／flags一致；限普通C++列定包装，非67项／SYMBOLIC／向量全量验收。建议小修优先，共用后端先闭合工具链，向量优化先修回归。未改生产源码；报告及小型证据已随根仓float@3bb9e8d保存。[独立报告](independent-review-20261021.md)。

2026-10-19：按model功能类别重组已完成，`feat/sail-riscv-by-category-20261019@3ea3cbaf`，工作树 `.worktree/sail-riscv-by-category-20261019`。准确基线 `4f2ac293`，11个模型功能提交＋1个忽略规则提交；最终完整tree与 `755fea6e` 相同，151路径保留。22次新中间树普通/SYMBOLIC严格类型检查通过；两处散落的SEW修复集中归组，配套文件保留。原两个工作树/全部旧分支/索引/gitlink保持，新工作树干净，未push；本轮未验新IR/数值/C++/硬件。见 [提交索引、来源和验证](commits-by-category-20261019.md)。

2026-10-18：用户授权后已发布 [上游PR #2030](https://github.com/riscv/sail-riscv/pull/2030)，官方master基线e5acebb0上新增 `fbacdfff`，1提交/5文件。修复FLI与四条BF16汇编，四小常量改可读十六进制浮点，补原生Sail单测。Sail0.20.3全模型严格类型检查、定向C/C++、104文本/LLVM编码、32往返、GNU12项及格式/拼写通过；DCO通过，完整CMake/CTest及其他CI尚未验收。原子仓/索引/gitlink保留。[提交与证据](pr-1a135b24-20261018.md)。

2026-10-18：联网核实官方最新 `master@e5acebb0`（0.16），`1a135b24` 的 FLI 常量索引文本与四条 BF16 分隔错误均未修复。实际抽取上游映射的104条文本被LLVM全部拒绝；临时应用模型补丁后104条文本/编码及32映射往返通过。GNU实测把0x10静默编码成16.0而非1.0。已有issue/PR检索未见专门修复，#1008为相关通用议题。原子仓/索引/gitlink保留，未发布issue。[上游核查与上报建议](upstream-1a135b24-20261018.md)。

2026-10-18：确认FLI索引2至5的四个长小数精确等于对应二次幂；GNU as2.45.50/LLVM MC22.1.8对普通小数、科学计数和十六进制浮点写法共24次FLI.S汇编均成功且编码保持。推荐 `0x1p-16` 等可读写法，未改生产映射，未验H/D。[补充证据](fli-syntax-20261017.md#2026-10-18-四个小常量的可读写法)。

2026-10-17：完成 `1a135b24` FLI语法官方资料核对及15次独立汇编/编码检查。GNU as2.45.50/2.46及GCC14.2接受 `0x10`，但生成16.0而非索引16对应的1.0；LLVM MC/Clang22.1.8拒绝该写法。两组浮点文本对照编码一致。修正“GNU/LLVM都拒绝”的外推，未改变生产源码/索引/gitlink，未运行模型或硬件。见 [复核与官方依据](fli-syntax-20261017.md)。

2026-10-16 接续：按用户指定起点，对 `1a135b24..cfde70ec`（包含起点，共22提交）完成实际diff与既有证据的合并价值评估，见 [逐提交建议](merge-value-20261016.md)。区分优先修复、基础依赖和需补验证的重构；确认d59577a0还包含widening reduction的SEW8合法域修复。只更新审阅记录，未运行新功能测试或执行合并，既有验证边界不变。

2026-10-16：用户授权后，已在 `.worktree/sail-riscv-split-20261016`、`feat/sail-riscv-review-20261016` 完成23个按功能拆分的提交，HEAD `cfde70ec`。163件改动完整复制，151件非缓存文件入库；12件pyc保留本地。最终tree与原索引排除pyc后完全一致，原工作区HEAD/分支/索引原始字节/补丁/文件及父gitlink保持。新worktree干净，未push。实际提交和逐批文件见 [提交索引](commits-20261016.md)。

本轮42次精确树普通/SYMBOLIC严格类型检查、104文本/编码与32FLI往返、flags方程、完整C++构建、两项RV64 BF16 CTest、共享类型及E/non-E AMO、14项move/merge探针通过。vector helper旧对照构造器因不存在的old_fp_min_pure调用失败；旧fixture/结构脚本、外部Sail补丁与workaround坐标限制仍保留。未验全量IR/指令/数值/硬件或每一层C++构建，不能记整体语义PASS。详细命令/日志哈希见 [验证证据](split-20261016/validation.json)。

以下为原提案与历史审阅状态，不再表示尚待用户授权拆分。

2026-10-15：重新核对 HEAD、gitlink、全部163个暂存路径与 binary diff 哈希，均与下述审阅一致；新增 [14批逐文件说明](file-details.md)，覆盖151个非缓存路径及12个排除项，明确共享文件的函数/hunk边界。未改 Sail-RISC-V 源码或索引，未重跑功能测试，也未实际拆分提交。

2026-10-14：调查完成，提交方案供用户判断，未提交或改变 Sail-RISC-V 索引/源码。当前 `feat/isla-workarounds@4f2ac293` 与父 gitlink 一致，163 个暂存文件（24 修改、139 新增），无未暂存/未跟踪内容。分组建议见 [report.md](report.md)，范围和步骤见 [plan.md](plan.md)。

本轮当前源码汇编回归 104 文本/编码及 32 FLI 往返通过，4 项 lane 源码结构检查通过；旧合法性 fixture、纯比较旧快照恢复失败，min/max 检查器结构已过时；workaround 坐标检查失败，暂存补丁空白检查失败。12 个已暂存 Python 缓存应从未来候选排除，现索引保持原样。

14 个建议提交单元分开表示维护清理、可独立修复、公共接口及浮点依赖链。通用 Bool/ITE 声明先行；完整共用浮点后端依赖仓库外 Sail 编译器补丁。旧 PASS 仍按原冻结版本理解，本轮未构建中间候选或验收完整模型/全指令/硬件。下一步是用户选择接纳批次，再按隔离候选逐批构建和验证。
