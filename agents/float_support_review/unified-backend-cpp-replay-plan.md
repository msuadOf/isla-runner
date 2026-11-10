# 共享 Sail C++ 完整指令 witness replay 方案

日期：2026-09-27。状态：只读设计及历史生成头ABI探针完成；新P1共享C++模型尚待实际生成、编译与运行。本方案服务用户要求的“以C++ model快速校验Isla”：每条输入执行真实物理word译码和完整Sail指令，比较完整AST、返回与102项架构状态。helper三方比较仍保留，不能代替本入口。

## 范围、入口与分工

首版只消费`isla/scripts/run.mk`的`FD_NONMEM_RV64`集合，即77个RV64非访存浮点clause。集合由同批文件生成和固化，不手抄；排除10个访存clause及`FMVH_X_D/FMVP_D_X`两条RV32限定项。worker接收已经过审核的物理word，不取指、不装载ELF、不调用`try_step`、不处理内存模型。

建议新增独占工具目录`agents/float_support_review/tools/unified_backend_cpp_replay/`，实现`prepare.py`、`run.py`、`runner.cpp`、生成的状态/AST适配与测试fixture。不改现`solve_replay`消费者及其结果，不改77项清单，不进入内存worktree。模型候选由`tools/unified_backend_model`负责人维护；构建、真实生成头及库由`tools/unified_backend_build`负责人提供；本入口链接其冻结产物。主agent依现有任务授权分配实施，无需另起用户确认流程。

建议公共命令形状：

```sh
python3 agents/float_support_review/tools/unified_backend_cpp_replay/run.py \
  --solve-manifest "$RUN_DIR/replay-manifest.json" \
  --cpp-manifest "$CPP_DIR/build-manifest.json" \
  --runner "$CPP_DIR/bin/isla-cpp-witness-replay" \
  --output "$RUN_DIR/cpp-replay"
```

所有路径只是预定工具合同；当前没有宣称该命令可运行。C++ worker采用`runner INIT_MANIFEST CASES_JSON RESULTS_JSON`，一次进程读入同一冻结模型与配置，顺序处理批量case。首版并行只用独立进程worker。历史生成模型在namespace层定义`zghz...`临时GMP对象，runtime配置也为进程全局；SoftFloat TLS不等于整个Sail模型线程安全。

## 可复用的现设施

| 已有入口 | 复用方式 |
| --- | --- |
| [solve_replay/protocol.md](tools/solve_replay/protocol.md) | 原样保留`run-id/clause/case-id`主键、物理word、entry-domain、pre/post和终态配额规则。 |
| [audit.py](tools/solve_replay/audit.py)的`audit_run`、`word`、`check_state`、`normalize_instruction`、`normalized_state_value`、`validate_replay_results` | Python端导出完整队列、校验输入/trace/provenance、比较实际AST/ret/post；共享比较函数，不复制一套宽位串/结构顺序规则。C++结果可复用`paths`形状，另明确`backend=cpp`、不伪造SMT唯一性证明字段。 |
| [negative_words.py](tools/solve_replay/negative_words.py)、`decoder_negative_cases` | 复用已审核的不可编码constructor→物理word负例；保留负例来源及缺口。无word不进入CPP执行队列。 |
| [sail-riscv/c_emulator/CMakeLists.txt](../../sail-riscv/c_emulator/CMakeLists.txt)的`riscv_model`库、`sail_runtime`、SoftFloat和jsoncons | 给同一冻结构建新增小runner目标，链接实际共享模型库。复用现JSON依赖、GMP和平台接口，避免复制生成模型或改用旧tuple wrapper。 |
| [riscv_platform_if.h](../../sail-riscv/c_emulator/riscv_platform_if.h) | 新`ReplayModel : public hart::Model`覆写外部回调；`ModelImpl`为final，不能再继承它。需要无操作观察回调时复用其既有接口定义。 |
| [高半部fixture](tools/solve_replay/fixtures/replay-vector-high-half.json)、[完整FLI fixture](tools/solve_replay/fixtures/p1-fli-case80.json) | 首批ABI/指令/完整状态正例，复用高64位、fcsr和word负控制。旧fixture需按受测版本明确历史或重生成，不自动成为P1同版验收。 |

`run_batch.py`现有入口绑定Rust runner路径、源码manifest及decoder证书，不能直接把CPP可执行文件冒充Rust runner传入。新增薄编排器导入公共审核/比较函数，并增加CPP构建与环境合同。

当前1dcc有50个自然完成目标、18477条gen的Isla全状态重放证据；其余27项超时，不能写77项全量通过。P1新源码/IR/config变化后这些证据均保留历史适用范围。

## 实际C++ ABI与所有权

本轮读取了已有历史构建的`sail_riscv_model.h/.cpp`及当前生成配置。该构建的真实公开API为：

```cpp
namespace hart {
class Model : protected PlatformInterface {
public:
  void model_init();
  void model_fini();
  void zext_decode(zinstruction *result, uint64_t word);
  void zexecute(zExecutionResult *result, zinstruction decoded);
  bool have_exception;
  // 其余寄存器均为公开字段；见下表。
};
}
```

`ext_decode`与`execute`目前通过模拟器调用闭包保留下来；replay构建应显式加`--c-preserve ext_decode --c-preserve execute`，避免依赖其它根函数是否保留。最终必须以P1生成头校验签名，编译失败即暴露ABI漂移。

历史生成器把构造/清理函数`CREATE(zinstruction)`、`KILL(zinstruction)`、`CREATE(zExecutionResult)`放在生成`.cpp`内的static函数，外部TU不能直接链接它们。首版允许显式把输出初始化为无资源constructor：

```cpp
hart::zinstruction decoded{};
decoded.kind = hart::Kind_zILLEGAL;
decoded.variants.zILLEGAL = 0;
hart::zExecutionResult ret{};
ret.kind = hart::Kind_zIllegal_Instruction;
ret.variants.zIllegal_Instruction = UNIT;
```

历史`KILL(zinstruction)`的1045行switch没有任何嵌套`KILL`调用，指令payload不拥有动态资源；本次77项的合法结果只接受`Retire_Success(unit)`和`Illegal_Instruction(unit)`。`prepare.py`须从新生成类型表递归确认已接受constructor只含bits/整数/Bool/enum/这些字段的tuple；一旦出现lbits、list或其它有资源payload，停止并生成同TU生命周期桥接，不能用C++“trivially copyable”代替Sail所有权证明。未知ExecutionResult直接报告不支持并让该worker失败，不静默忽略或当作成功。

## 输入与状态映射

输入继续使用完整`gen`记录：`test-ins-encdec`严格为32位；`requested-instruction`、`decoded-instruction`、`ret_val`均必填；`isa-state-complete`和`isa-state-post`各恰好102个同名字段。`isa-state`旧稀疏字段不能作为恢复来源。

| JSON字段 | 逻辑宽度 | 已核历史CPP字段 | 装配及输出要求 |
| --- | --- | --- | --- |
| `x1`–`x31` | 64 | `model.zx1`等，`sbits` | 设置`.len=64`、`.bits=raw`；最终固定宽度生成若变为`uint64_t`，依实际头选择并静态核验。 |
| `f0`–`f31` | 64，FLEN=64 | `model.zf0`等，`sbits` | 保存全部原始64位，包括NaN boxing；不经host float，不调用会unbox的读取helper。 |
| `vr0`–`vr31` | 128 | `model.zvr0`等，`lbits` | `model_init`分配后设置`.len=128`并用GMP按16进制整数填充`*bits`；不得浅拷贝`mpz_t*`。 |
| `cur_privilege` | 枚举 | `model.zcur_privilege : hart::zPrivilege` | 显式按`User/Supervisor/Machine/...`名字映射生成枚举，不按序号cast；受测输入域仍须满足原manifest约束。 |
| `mstatus` | 64 | `model.zmstatus.zbits : uint64_t` | 完整写入和比较，包含FS/VS、SD及其它位；不预设Dirty，不归一化无关位。 |
| `fcsr` | 32 | `model.zfcsr.zbits : uint64_t` | 检查高位范围，直接设置全部32位；frm、sticky fflags及保留位都来自witness。 |
| `vl`、`vstart` | 64 | `model.zvl/zvstart : sbits` | 直接恢复，不能调用有副作用的CSR写入口。 |
| `vtype` | 64 | `model.zvtype.zbits : sbits` | 保留vill/LMUL/SEW/vta/vma及原始其它位，不能重算。 |
| `vcsr` | 3 | `model.zvcsr.zbits : uint64_t` | 直接恢复并按3位输出；不得误作32位fcsr。 |

Bits字符串先去合法下划线，检查声明宽度和数值不越界；禁止仅`stoull`截掉128位高半部。所有输出为统一`N'h...`完整宽度十六进制，Python继续按数值/宽度比较。字段缺失、多余、位宽错误或未知enum均失败。

`vrN`字符串是位向量数值，最高十六进制位对应高位，元素0/掩码bit0位于低位。GMP字符串导入无宿主端序问题。不得交换lane顺序、拆成只比较活动lane、忽略tail/mask区域，或先按SEW转换成host数组。高半部fixture的`vr0=0x123456789abcdef0fedcba9876543210`及`vr3`非重复高64位作为强制门槛。

恢复初态必须直接赋存储字段；`set_F/set_V`、CSR accessor等会产生Dirty、WARL、mask或callback效果，不能作为loader。执行后读取同一原始字段。

## 初始化、配置与未导出辅助状态

正确顺序为：

1. 校验CPP生成源与IR来自同一冻结Sail模型/库/配置；冻结并加载IR生成采用的具体RV64、FLEN64、VLEN128、ELEN64配置。普通CPP使用runtime JSON时，先`sail_config_set_string()`，再建立模型；固定配置CPP亦记录实际生成选项。
2. 构造`ReplayModel`并调用`model_init()`，分配GMP对象并执行生成的模型寄存器初值。历史生成代码末尾已调用`zinitializze_registers(UNIT)`，不要再次无条件调用。
3. 应用同批Isla配置实际使用的固定register defaults，例如`misa={bits=0x800000000034112f}`；记录每项来源、位宽和CPP字段。不把被102项witness覆盖的默认mstatus等当最终初态。
4. 覆盖完整102项witness；立即导出并逐项比较一次，证明loader精确恢复，之后才执行decoder。

不得在第3/4步后调用`zinit_model/reset/init_boot_requirements`。当前`init_model`调用`reset_sys/reset_vmem`，模拟器boot还写x10/x11及PC，它们会改变witness或引入与Isla初始化不符的额外状态。这里直接进入`execute`，没有PC递增、时钟tick、取指、trap处理器或退休计数更新。

模型形状和环境必须输出一份`cpp-init-contract.json`：源树/JSON/TOML哈希、Sail编译器及C插件、生成头/源、riscv_model/runtime/SoftFloat库、所有编译宏、XLEN/FLEN/VLEN/ELEN、固定寄存器、配置原语及callback行为。不能只验证VLEN一致。尤其`PlatformInterface::sys_enable_experimental_extensions`默认返回true，而当前Isla配置为false；`ReplayModel`必须明确覆写false。其余默认平台回调也须逐个归类，不能假定默认实现等同于TOML的`const_primops`。

物理PC/x0未在当前102项导出；架构x0由Sail `zero_reg`返回0。禁止把C++字段默认零解释成已知PC/x0 witness。当前77项的可接受decode/execute必须没有对这些未导出物理字段的语义读取；复用同批Isla decoder/execute检查及源码证据。若受测版本新增实际PC读取，输入合同不足，报告`missing-input-state`，先补出具体证据/字段再放行。

其它辅助状态不能整体当作don't-care。首版明确采用以下门槛：

- 对从同批Isla独立重放已取得“decoded/ret/102 post对全部残余辅助状态观察唯一”的case，复用其证据哈希；核CPP模型初值与固定defaults构成同域的具体实例。历史1dcc证明不能覆盖P1新IR。
- 新case若尚无该证明，可以做CPP具体重放并报告`concrete-match/concrete-mismatch`，不能直接升格为完成验收。要成为正式PASS，提供同版唯一性证据，或经审核的完整读取依赖表，证明所有影响观察值的读取均来自102输入、固定配置或已匹配的模型初值。
- 发现未导出且未证明不影响结果的读取，列出字段/来源并停止该case的验收。不得把差异强归于浮点算法，也不能在CPP随意设0后把匹配当作所有辅助状态已覆盖。

这一门槛复用现有证据，CPP批量运行自身不需要每条调用Z3；缺证据的case仍能迅速给出具体差异，后续按缺口补验证。

首版每条case建立新模型对象，`model_init → defaults → witness → decode → execute → model_fini`，同一worker进程处理多个case。先保证case互不污染，再记录初始化与执行各自耗时。后续只有核定完整写集合和恢复集合后，才复用一个模型并批量恢复状态；`Model`不可直接memcpy或浅拷贝。

## 译码、完整AST与返回合同

调用真实`zext_decode(&decoded, word)`，不从`requested-instruction`构造执行AST，不通过汇编文本重新编码选择指令。先把实际decoded AST与记录比较，成功后才允许执行。普通`entry-domain=decoded`要求实际constructor属于冻结77项且requested/decoded完全一致；`decode-rejected`要求实际`ILLEGAL`及其完整32位payload一致。未知constructor不得执行，保证不把恶意/损坏word引入访存或其它不在范围的语义。

`instruction_to_str`当前源码只是`assembly`或`.insn`字符串，无法证明RM、funct、operand及全部payload相同。必须生成typed AST visitor：

- 从同批IR的instruction constructor、tuple字段、enum类型/成员表导出`instruction-schema.json`，再与P1 CPP头内`Kind_z...`、`variants.z...`和`ztup0/...`逐项对齐；生成77项及`ILLEGAL`的C++switch，未知项硬失败。
- CPP visitor只读取实际decoded字段；按冻结IR schema输出与`stable_instruction_text`兼容的完整文本，再直接复用`normalize_instruction`比较。不能把expected AST文本写回输出，也不能只比较constructor名称或重编码word。
- tuple按位置映射C++`ztupN`，保留IR的精确字段键；enum按实际值映射成员名称及schema中的编号，不假定C++和Z3 ordinal天然相等。当前打印约定只做一次zdecode，避免把类型内部`zrounding_mode`重复decode而制造伪差异。
- 生成器必须完整覆盖所有允许constructor的所有叶字段，编译阶段及负例验证不可漏字段。JSON格式化顺序可归一，位宽、数值、枚举身份及嵌套结构不能省略。

decoder不应改架构状态：运行前后比较102输入及固定环境字段，并记录无架构写/外部活动的回调账本；复用绑定新IR的静态decoder纯读证书。C++编译器的内部配置缓存写不属于架构写，但不得据此容忍Sail寄存器写。动态状态相等只能补充静态闭包审核，不能证明没有短暂写回后恢复。

随后调用`model.zexecute(&ret, decoded)`一次。直接比较`ExecutionResult`完整constructor/payload：当前允许的两种输出精确打印为`Retire_Success(())`、`Illegal_Instruction(())`。Illegal是正常执行结果，不调用trap处理器，不重写PC/privilege，不自动假定post不变；按官方完整post比较。`have_exception=true`、Sail assertion、MatchFailure、`ExecuteAs`、内存相关返回或其它未支持结果均报告失败；不把它们映射成`Illegal_Instruction`或吞掉。

现77项不需要压缩指令的`ExecuteAs`续执行。未来扩域须单独扩展合同，当前不顺带接入。

## 外部活动与状态观察

`ReplayModel`的freg/vreg/xreg/CSR写callback记录事件并返回UNIT，不修改模型；decoder阶段任何此类写回调失败。execute阶段允许这些观察回调，但最终验收依据原始102字段。

fetch、内存读写、PTW、reservation、终端输出、trap/redirect/PC写等入口在本范围不应被调用；实际调用须明确失败并带case-id。仅观察性的print可写stderr或关闭，不能混入结果JSON。不能用PlatformInterface默认无操作内存callback掩盖错误译码/越域执行；同批constructor白名单和执行闭包检查共同约束这一范围。这里不定义任何内存读值或一致性语义。

比对完整FPR/VPR、fcsr/frm/fflags、mstatus FS/VS/SD、cur_privilege与向量上下文。callback次数、运行时内部缓存、host地址不是当前102项架构协议；单列日志不能替代这些状态比较。也不能因CPP/Isla共用Sail就宣称模型ISA语义独立正确，原生SoftFloat flags及规范/DUT证据仍承担其独立覆盖。

## 实施顺序与验证

1. **冻结及schema**：由P1构建owner交真实共享模型库/头/配置manifest；加decoder/execute保留项。导出初始化合同和102状态/77 AST schema，生成reader/writer/visitor并对象编译。检查CPP实际进入共享helper、未调用旧67个策略级cpp extern。
2. **状态codec红绿**：完整fixture写入后原样读回102项；错误位宽、缺字段、额外字段、非法enum、不同vr高半部必须先失败。翻转fcsr/mstatus/未写FPR/未写VPR高半部预期都应被拒绝。
3. **真实指令闭环**：最先FLI、FADD.S/D、FMINM、动态RM、FCVT负整数、VFADD高半部、BF16 VF/VV、vl=0/全mask、非法FS/VS及非法LMUL。包括word翻转、AST单字段翻转、ret翻转、decoder写状态负控制。每例调用实际word→decoder→execute。
4. **同版批量**：复用审核后的所有gen及可构造decoder负例，一进程多case，显式记输入/输出总数、每条错误与完整状态差异。抽取A→B→A状态顺序样例验证case隔离；不得抽样后声称全量。
5. **性能交付**：分开记录模型/配置初始化、装配、decoder、execute、序列化和总吞吐。先给实际CPP速度，不承诺预定倍数；再决定是否值得实现复用模型的恢复优化。

结果至少分开报告`input_audit_complete`、`cpp_build_verified`、`initialization_compatible`、`decoder_ast_match`、`ret_match`、`post_state_match`、`aux_observation_evidence`、`cpp_replay_complete`、`whole77_complete`。单条CPP匹配不能把solve超时、源码branch未闭合或缺失case补成PASS。错误worker退出非零并保留已完成结果；主进程必须核对提交/返回ID守恒。

## 本轮实际核验与未测边界

证据在ignored目录[`.tmp/unified-backend-cpp-replay-plan/`](../../.tmp/unified-backend-cpp-replay-plan/)。[probe_api.py](../../.tmp/unified-backend-cpp-replay-plan/probe_api.py)使用真实高半部fixture生成102项字段恢复代码、`misa`固定值、decoder/execute与tag读取；对已存在的历史生成头执行`g++ -std=c++17 -fsyntax-only`，退出0。[commands](../../.tmp/unified-backend-cpp-replay-plan/commands.json)和[manifest](../../.tmp/unified-backend-cpp-replay-plan/manifest.json)记录实际头/源/fixture/探针哈希。

此结果只证明上述历史ABI可编译，未链接或运行模型；probe中的断言未执行。历史头的动态XLEN/FLEN表示不保证与P1固定配置头完全相同。新共享CPP完整指令replay、所有初始化域、AST visitor、77项批量和性能均尚未实施/验证。

## 实施初版独立复核（2026-09-27）

已只读复核`tools/unified_backend_cpp_replay/`初版的IR schema导出、CPP头对齐、完整状态codec与runner。受审副本和哈希保存在ignored [implementation-review](../../.tmp/unified-backend-cpp-replay-plan/implementation-review/manifest.json)。实际IR tuple顺序、CPP `ztupN`位置、enum成员集合及按值switch、77+ILLEGAL全payload递归无资源检查未发现漏字段；runner先比较真实decoder AST再调用execute，保持完整102项比较，当前只报告`concrete-match`，没有把未建立aux合同的历史模型结果升级为正式PASS。

交接用语`hartcallbacks=false`经主agent澄清，只指实际API `PlatformInterface::sys_enable_experimental_extensions=false`，不存在另外的配置键或CLI开关。按该真实名称、print/rvfi关闭和回调白名单实施。

复核反馈与边界：

- decoder前后固定环境比较起初仅含misa，实施者已扩为全部`fixed-registers`；新记录的mseccfg/menvcfg/senvcfg还需同样核decode后未变。源码修订不代替负控制运行。
- 初版在捕获`have_exception`后先调用`model_fini()`再返回case结果；实际生成的`model_fini`在异常为真时会`exit`，因此会丢失当前case的JSONL。实施者已接收修正：先落盘并flush该失败case，再让worker失败退出；不清除异常继续。主协调器须把尚未返回的case记为未完成，不能丢弃。Sail异常注入验证待其交付。
- 初版尚无正式`run.py`编排器，原始AST与规范化期望、合法entry-domain、ID唯一性及源/头/库/配置哈希绑定仍属进入正式路径前的门槛。历史smoke的直接runner输入不是完整生产协议。

本节未重跑实施者的历史16项控制；其3正13负结果仍以实施者的实际日志为依据。新P1完整模型和隐藏CSR初始化前沿证据仍待绑定，未改动对新架构的验收结论。

### 第二轮实现复核与故障注入

后续源码受审副本见[implementation-review-r02](../../.tmp/unified-backend-cpp-replay-plan/implementation-review-r02/manifest.json)，此编号仅表示独审源码快照。已确认runner在`have_exception`时先写出并flush当前失败case，再退出worker；全部固定register和mseccfg/menvcfg/senvcfg均在decoder后检查不变。新增`run.py`重新从原始`decoded-instruction`计算期望规范串，核对entry-domain、clause、唯一ID与构建文件哈希；当前正式完成标志仍为false。此处是源码复核，Sail异常/forbidden callback/decoder写状态的实际注入结果尚待实施者交付。

独立故障注入发现并验证修复了协调器的截断JSONL路径：

- 原版`run.py` SHA-256 `4769d7bdc003bda5720792f9f603651f591404f21144cfd02d260317f77175ea`在worker超时、留下1条完整结果和1条截断末行时抛出`JSONDecodeError`，未写`summary.json/results.json`。原始反例见[truncated-worker-review](../../.tmp/unified-backend-cpp-replay-plan/truncated-worker-review/review.json)。
- 修订版SHA-256 `e483a609b4535c0f669a295dc46f91d70639af7ebc2a2d998d0ac67e7ff0a7ab`在同样注入下保留第1条完整失败结果，将第2个ID记为`worker-missing-result`，记录worker退出124及第2行解析错误，协调器退出1且完整落盘。2个提交ID均有明确结果；[修复复验](../../.tmp/unified-backend-cpp-replay-plan/truncated-worker-review-fixed/review.json)通过。探针仅替换worker启动为模拟超时，不执行模型，不构成浮点或指令语义验证。
- `input_audit_complete`起初只取`runner_complete`。实施者已改为保存完整`input-audit.json`、单列runner/assembly/trace三维度，并以三者合取报告输入审计完整性；增加既有`reviewed-illegal`记录入口。此项已核源码，未重新运行整批solve审计。

实施者的历史模型r03日志报告16项控制按预期通过、所选72条指令全部具体匹配，三隐藏CSR实际初值与同1dcc的Isla初始化提取值一致；独审仅核读其汇总，未重跑这两组。历史源码与新P1同源绑定、完整辅助状态观察证据和77项全量仍待完成；上述修复不会把历史匹配升级为新架构PASS。最终构建入口还须绑定实际读取的ABI清单和P1模型构建清单，不能只核另一目录中同名文件的哈希。

随后独立运行实施者已构建的历史CPP异常注入二case控制，实际首条结果包含`decoder Sail exception`及`worker-fatal: Sail exception; model_fini not entered`，worker退出2；协调器保留首条失败、将第二个ID记为missing，退出1且落盘。两个提交ID守恒，[异常路径复验](../../.tmp/unified-backend-cpp-replay-plan/sail-exception-review/review.json)通过，关闭本独审提出的`model_fini`吞当前结果缺口。此测试使用真实历史模型加`CPP_REPLAY_TEST_SAIL_EXCEPTION`控制宏，只验证异常传播/结果记录，不能替代无控制宏的P1语义测试。
