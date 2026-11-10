# flags/sat 求解策略独立调查

## 结论

旧显式B的flags与sat Clause在同一冻结程序、输入、seed17和7200秒预算下，QFFP、default、通用smt六臂全部到进程外限且无完整JSON。换tactic没有使这两条Clause完成，不能将旧超时归咎于“恰好选了QFFP”。逐次计时证明有大量检查成本累积；另一条路径记录还出现一次SAT/1038.658秒的真实单查询长尾，但没有观察到任何单次检查耗满7200秒。文本导出解析失败，所有tactic单查询比较都直接使用原始Z3 AST；同捕获公式下default接近QFFP、通用smt更慢。单查询/采样与整轮的性能口径分别保留，不能把某条独立重建查询的速度冒充原增量会话速度。

## 已确认的完整观测

旧 `flags-arithmetic-B-dump` 带 `-D f` 的 7200 秒运行中，10668 次 `Z3_solver_check`/`check_assumptions` 全部返回：SAT 7976、UNSAT 2692、UNKNOWN 0，已完成检查累计 5278.482 秒，最长单次 135.175 秒（#685）。生成文件存在且 `summary.status=finished`。其启动器未记录 `wait()` 退出码或准确进程墙钟，不能写作“exit 0”或给出准确墙钟。旧正式 84 次对照的 flags B 三个 seed17/29/43 均在 7200 秒外限退出 124；当前观测不覆盖这些超时。另一组 `../path-accounting/final-flags-arithmetic/queries.tsv` 后续实测 #685 为 SAT、1038.658 秒，证明该实验条件下单次长尾可达 17.31 分钟；它仍不是单次 7200 秒超时。不能将旧135秒称为所有运行的上限。

旧 `sat-B-dump` 同预算运行中，21104 次进入、21103 次返回：SAT 13961、UNSAT 7142、UNKNOWN 0，已完成检查累计 7052.568 秒，最长已返回单次 6.160 秒（#1378）。外限终止时仅 #21104 尚未返回，不能把它写成单次运行两小时。它的开始时间为 monotonic 515052.727811；监控结束时间 515065.798131 只给出了终止晚于该开始的粗界限，未记录 `wait()` 退出码或精确终止时刻。

这轮与正式 84 次共用冻结 `isarch`、IR/config、官方 Z3、QFFP、`-T 1`、`--smt-timeout 7200s` 和 fixed seed17，差异是实验 `probe.so`、`-D f`、固定核和当时共享负载。旧正式 flags B 三轮 CPU user+sys 都约 7160 秒，因此不能主要归咎于没有得到 CPU。新一轮为何在 seed17 下自然完成仍未控制；负载、日志、进程内状态与频率均可能产生影响，不能宣称因果解释。

## 原始查询与文本边界

`capture_raw.c` 在 `Z3_solver_assert` 入口保留原始 AST 引用，目标检查前合并该 solver 的断言和临时 assumption。flags #47 为 14 条原断言＋1 条 assumption，sat #235 为 52＋1。flags #47 的两次独立捕获 SHA 一致。该文本经 `Z3_benchmark_to_smtlib_string` 输出后，枚举类型声明为 `k!240`，使用位置却是 `k!2400`；官方 Z3 CLI 报 `unknown sort` 且退出 1。故这些文本仅作为 AST 输入一致性的辅助哈希，**没有有效独立文本重放**；不可引用末尾的 `sat` 为结果。

冻结 isarch 的动态导入列表含 `Z3_solver_assert`、`Z3_solver_check`、`Z3_solver_check_assumptions`、`Z3_solver_inc_ref/dec_ref`，不含 `push/pop/reset/assert_and_track`；对应 Isla `smt.rs` 源码只有 `z3_assert` 调用 `Z3_solver_assert`，reset 实现处于注释中。这支持实验hook的断言栈完整性。新建 solver 一次 inc_ref、析构一次 dec_ref；hook 在 dec_ref 时释放该 solver 的保留 AST。实验限于这一冻结二进制，不能将该捕获器泛用到会 push/pop 的别的程序。

为避开打印问题，`capture_raw.c` 在同一个原始 Z3 context 中，用新建 tactic solver 直接装入保存的 AST，串行交叉比较 `qffp/default/smt` 各三次，固定 `random_seed=17`。原增量 solver 最后再 check，用来核对 SAT/UNSAT；新 solver 的独立检查不能等同于增量会话性能。结果写到 `compare/<workload>/compare.tsv`。首轮 flags 版本仅有进程外 7200 秒限时，没有给每个新 solver 显式设置 `timeout`；所有九次自然返回，故不影响已完成 SAT/时间记录，也不据此声称每次受 7200 秒限时。sat 修订版给每个新 solver 显式设置 `timeout=7200000` 毫秒。

flags #47 三轮全部为 SAT，原增量检查亦为 SAT。`qffp` 各 23.21/56.49/36.19 秒，`default` 各 29.03/34.88/42.20 秒，`smt` 各 262.63/121.39/121.98 秒。首轮 `smt` 与另一组路径代理在 CPU106 上短时重叠约 10 秒，故不将该次单独视为纯策略时间；后两轮 `smt` 仍显著慢于另两者。单条 flags 查询不支持“选 qffp 导致 2 小时超时”的说法。完整Clause的最终结果见下表。

另在冻结 flags B、seed17、QFFP 下捕获第685次检查的原始 AST，19条断言＋1条assumption，SHA `3e4d53372dc7add4e561265881ed46649111f44bb0a23f1af629af570ad72aa4`。首次捕获到达检查前约953.63秒；捕获器在调用检查前退出，因此该时间不表示#685的求解耗时。三条独立进程重新到达第685次检查时，AST文本SHA均与首次完全一致，各自用fresh solver直接装入原AST、相同assumption与seed17，单次SAT结果：QFFP 8.669秒、default 8.406秒、通用smt 18.549秒。每个fresh solver显式`timeout=7200000`毫秒；外部9000秒包含到达该检查的前缀，但各次均自然完成，未触及限时。三个目标经简化的`is-qffp`probe均为1。命令、原始文本与结果见`compare-685/`及`compare-685-results.json`。

这些结果说明同一捕获公式在fresh solver下可于约8–19秒求解，且改为default没有获得明显优势。再做一次同进程第685次检查：同SHA原AST先在fresh QFFP solver得SAT/7.475秒，随后**原增量QFFP solver**直接`real_check`亦得SAT/7.243秒，两次都用实际单调时钟计时，进程exit0。证据见`compare-685-original/{fresh.tsv,original.tsv,result.json}`。因此“会话历史导致长尾”也未获实证支持。path-accounting另一轮的1038.658秒缺原AST SHA，同序号不自动等于同公式；即使公式相同，运行间求解时间也可能显著波动。目前不能将该长尾归因于tactic或会话历史。

sat #235 的两次捕获文本 SHA 一致，52 原断言＋1 assumption；三轮 `qffp` 2.79/2.78/2.93 秒，`default` 1.46/3.05/2.65 秒，`smt` 26.13/19.56/26.97 秒，九次及原增量检查全部为 SAT。该查询经 `simplify` 后 `is-qffp` probe 的 C API 结果为 1，配合官方 default 源码说明此次 default 会走 qffp 分支。因此它不是三种独立后端的对比，也不支持 qffp 是本条查询慢的原因。

## 整轮受控对照

`run_full.py` 用冻结 B IR 做 2 工作负载 × 3 tactic，CPU100..105 分别固定独立物理核，seed17、官方 Z3、`-T 1`、每次 SMT 和进程外限均 7200 秒。命令、哈希与 PID 在 `full-launch.json`。**本轮启动的脚本进程是串行 `wait()` 旧实现**，后完成项若先于前项结束则其 `elapsed_s` 会偏大；独立 `observe_full.py` 每 0.1 秒观察进程退出，`full-exit-observed.json` 才作为本轮墙钟依据（观测精度约0.2秒）。`observe_cpu.py` 每秒采样实际 isarch CPU user/sys，数字为近似而非 `/usr/bin/time` 精确值。磁盘上的 `run_full.py` 已改为每臂独立 `wait4()`，只对后续重跑生效。

| 旧B Clause | tactic | 退出 | 观测墙钟秒 | isarch CPU秒约 | 完整JSON |
| --- | --- | ---: | ---: | ---: | --- |
| flags-arithmetic | qffp | 124 | 7200.433 | 7173.45 | 无 |
| flags-arithmetic | default | 124 | 7200.339 | 7169.16 | 无 |
| flags-arithmetic | smt | 124 | 7200.188 | 7175.32 | 无 |
| sat | qffp | 124 | 7200.255 | 7173.57 | 无 |
| sat | default | 124 | 7200.299 | 7165.71 | 无 |
| sat | smt | 124 | 7200.167 | 7168.26 | 无 |

六臂种子拦截日志都显示`fixed=17`，CPU利用约99.5–99.7%；没有任一臂自然完成，也没有完整JSON可给出`summary`。这些是**进程外限超时**，不能直接记作单次SMT达到7200秒，尤其本轮完整六臂没有逐次检查探针。单靠换default或通用smt没有让旧B两条Clause在预算内结束；六臂并行虽各占独立物理核，仍会共享内存/频率等资源，因此不以本轮给精确策略加速倍率。全表与原始证据见`full-verified.csv`、`full-results.json`、`full-exit-observed.json`及`full-cpu-sampled.json`。

## default 逐次检查的采样对照

完整六臂不带逐次 SMT 计时；为区分可能的单次长查询和累计成本，另用 `probe.so` 在 CPU114/115 做 default 两条旧B Clause 的 300 秒采样。与完整六臂同冻结程序、IR/config、seed17、`-T 1` 和 7200 秒 SMT 限时；外限 300 秒只作诊断。`flags-arithmetic` 完成 59/60 次，已返回累计 287.010 秒、最长 71.825 秒、SAT54/UNSAT5/UNKNOWN0，#60 在截止时 pending。`sat` 完成 1378/1379 次，累计 291.951 秒、最长 2.760 秒、SAT940/UNSAT438/UNKNOWN0，#1379 在截止时 pending。两臂采样外限退出 124，均不能写作单次 SMT 超时，更不能写成两小时单查询。CPU user+sys 约 299 秒/臂，未明显因调度失去 CPU。完整证据在 `default-sample-results.json` 和原始 `default-sample/<workload>/queries.tsv`。

同样 300 秒窗的既有 QFFP 实际计时为 flags 255 次返回、最长 22.27 秒；sat 1668 次返回、最长 1.55 秒。default 在这两条 Clause 的当前采样中推进较慢，但启动时间、物理核与共享负载不同，不能从此计算严格同环境加速比。此采样和固定单查询都提示：改用 default 没有立刻消除 flags/sat 的高成本；最终需看完整六臂退出。

同样在 CPU114/115、同一探针和seed条件下，随后做通用 `smt` 的300秒采样。flags 完成 47/48 次，累计 210.601 秒，最长 148.809 秒（#47；#46 为60.815秒），SAT46/UNSAT1/UNKNOWN0；sat 完成238/239次，累计282.689秒，最长20.386秒，SAT163/UNSAT75/UNKNOWN0。两臂各有一次截止时 pending；exit124仅表示300秒外限。CPU user+sys均约299秒。相对前一轮default采样，smt推进更少、慢检查更长；但属于相继时间窗，不能作为严格无共享干扰的倍率。完整证据在`smt-sample-results.json`。

另在 CPU114/115 用当前六臂仍在运行的同一时段，做 A（ITE）版 QFFP 完整 Clause 控制。flags 生成 208 条、exit0、`finished`、墙钟 170.695 秒、CPU user/sys 157.015/11.917 秒；sat 生成 18 条、exit0、`finished`、墙钟 19.739 秒。两者都是 fixed seed17、相同冻结程序/config及7200秒限时，无逐次检查探针。这个控制说明当前共享环境中基线可完成，不把B的长耗时归于机器整体失效；它不替代旧正式三对消融。命令和原始结果见 `a-control-results.json`。

## default 的实际可能路线

官方 Z3 1fd1d3613 的 `src/tactic/portfolio/default_tactic.cpp` 先 `simplify` 再依次检查多个 probe；`is-qffp` 命中时调用 `mk_qffp_tactic`，否则可能落到 `smt`。`src/tactic/fpa/qffp_tactic.cpp` 的 probe 允许浮点、位向量及简单枚举。两条捕获查询都有 FP/BV/枚举且无文本可见的数组或量词；两条实际 AST goal 经 `simplify` 后，C API `is-qffp` probe 都返回 1，说明这些查询的 default 分流进入 qffp。不能仅从这一条查询外推完整 Clause 的每次分流。
