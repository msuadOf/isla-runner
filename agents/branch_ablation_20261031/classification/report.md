# 分类、NaN 结果与窄转换饱和的单因素消融

三项改动各自严格重生完整 IR。NaN 结果和窄转换的 A 臂在固定 60 秒预算内三次完成，B 臂三次均删失；这证明当前预算下 A 臂的**完成性优势**，不能从删失记录计算加速倍数，也无法比较 B 臂最终见证覆盖。分类项两臂均删失，性能和见证结论均无法判断。本轮没有改生产源码、IR、配置或旧输出。

## 版本、控制域和变体

- 根 float `1c7a354e`、Isla `80231ce9`、模型 `9c339044`。基线 `isla/ir/rv64d_v128_e64.ir` SHA-256 `10bea88ca9bc2938cc9f8d303fc3f851c0a256a31ef894bd84d5c7e2e8142bbf`，模型文件逐项匹配 `isla/ir/provenance/manifest.json`。`nan_unbox` 在两臂均保持已恢复的显式 `if`。
- 工具链 Sail SHA-256 `2e89d5f5467195ea0a2fb4b072133a0ee73933db3e8808b8a6518c7ef59ec807`，Isla 插件 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`，生成配置 `isla/ir/provenance/rv64d.json` SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`；编译参数与基线 provenance 一致，命令见各 `generation.json`。
- 执行二进制 `.worktree/isla-initial-state-20261029/target/release/isarch` SHA-256 `e9fd5a0bba97c736e88f2bb06f3d46c542de0f10744b9d644b38731ffa279204`。每个子项两臂使用同一配置；路径预算 30 秒、单次 SMT 预算 10 秒、外限 60 秒，`-T 1`、`qfaufbv`、Homebrew Z3。三个子项同时跑，但分别绑 CPU 48、49、50。每项双臂预热后按 `A B / B A / A B` 取得三对正式样本。

| 子项 | A/B 目标变更与完整 Clause | 固定初态 | B IR SHA-256 | 源码差分 |
| --- | --- | --- | --- | --- |
| 分类 | `fp_class_onehot_pure` 从十位布尔拼接改为同义显式分类 `if`；`VFUNARY1` 中的 `vfclass.v` 实际调用它 | `vtype=0x18`（SEW64、LMUL1）、`vl=1`、`vstart=0`；源向量保持符号化 | `4a2a51300354c3618f764e530de25aad54be40781c41275d96292254dcb5ba7d` | [class_if/source.diff](class_if/source.diff) |
| NaN 结果 | 仅 `riscv_f32_symbolic_bits` 中 NaN canonical 选择 `ite→if`；完整 `F_UN_RM_FF_TYPE_S` 即 `fsqrt.s` | FD 默认符号初态，含符号源 FPR | `a9d62f68cc723c3d1c5df4fb70400bc05e83fb92fb0d8a842ddea59dd744c1b9` | [nan_f32_if/source.diff](nan_f32_if/source.diff) |
| 窄转换饱和 | 仅 `riscv_f16ToI16_pure` 中 overflow 的 flags/value 选择 `ite→if`；`VFUNARY0` 的 `vfcvt.x.f.v` 和 `vfcvt.rtz.x.f.v` 实际调用 | `vtype=0x8`（SEW16、LMUL1）、`vl=1`、`vstart=0`；源向量保持符号化 | `d29e971b0872c7d11135cb3f96e036cfe6ee0ee93d61c8338a44520b9d3246bf` | [sat_f16_i16_if/source.diff](sat_f16_i16_if/source.diff) |

对应执行配置 SHA-256：分类 `f8db454645ce83708d1a437bf28408a5bc4ad689681662ebea4fcf65d8fd4e5f`、NaN `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`、饱和 `da35c576ca2a247660bbaba43f66989ea227498e92211adbeb1547ca7308326f`。每个变体的源文件哈希见 `source.json`，生成命令和产物哈希见 `generation.json`。[IR结构核验](ir-comparison.json)对 2053 个函数去除源位置和 Sail 匿名变量编号后，三个 B 分别仅目标 helper 不同；函数数、其余定义和初态域未变。此规范化只用于结构差异核对，原始 IR 哈希仍如上记录。

## 正式结果

下表是三次正式样本的中位数和范围。B 的 `60s` 只是删失时间，不能作 B 的完成用时。`/usr/bin/time -v` 记录的 maxRSS 单位为 KiB。

| 子项/臂 | 完成/删失 | 墙钟（秒） | 用户/系统 CPU（秒） | maxRSS（KiB） | 终态、见证 |
| --- | --- | --- | --- | --- | --- |
| NaN A | 3/0 | 5.014（5.014–5.015） | 3.83（3.79–3.87）/1.04（1.03–1.05） | 232172（232116–232348） | 每次 26 见证：退休20、非法6；退休结果 NaN10、非NaN10，`summary.status=finished`，partial=否 |
| NaN B | 0/3 | ≥60（删失） | 59.31（59.29–59.40）/0.61（0.53–0.65） | 286772（283528–314724） | 无最终 JSON；终态、NaN/非NaN 分布和 partial 数量不可用 |
| 饱和 A | 3/0 | 6.415（6.414–6.417） | 5.53（5.53–5.58）/0.73（0.72–0.78） | 254384（254200–254444） | 每次 18 见证：退休12、非法6；目标有符号转换4条源 lane 均为零，overflow 假4/真0，未见新增 NV；`summary.status=finished`，partial=否 |
| 饱和 B | 0/3 | ≥60（删失） | 59.53（59.52–59.54）/0.39（0.38–0.40） | 244176（242208–249392） | 无最终 JSON；invalid真/假分布和 partial 数量不可用 |
| 分类 A | 0/3 | ≥60（删失） | 57.80（57.22–57.90）/2.05（1.92–2.59） | 283308（275168–286536） | 无最终 JSON；十类分布和 partial 数量不可用 |
| 分类 B | 0/3 | ≥60（删失） | 57.65（57.56–57.82）/2.21（2.01–2.26） | 281284（269088–284152） | 无最终 JSON；十类分布和 partial 数量不可用 |

本固定二进制没有可核实的动态 fork 总数输出，因此所有样本的 fork 数记“未知”，不把生成数或 IR Jump 数冒充 fork。对删失样本，进程在外限停止且没有 JSON，无法判断内部已走过多少路径；`partial` 视为未可核验。原始命令、退出码、stdout、资源日志和完整 JSON 位于各 `runs/fixed-*` 目录，[machine-readable summary](summary.json)给出逐次记录。早期使用 CPU48–51 亲和集的 `class`/`class64`/`nan`/`sat` 预热与 `nan formal-*` 属探索运行，不计此表。

## 独立建议和剩余义务

- **NaN 结果选择：保留当前 ITE。**同一完整 `fsqrt.s` Clause 下，当前 A 三次完成并见证 NaN/非NaN；显式 `if` 的 B 三次都在 60 秒删失。本结果支持限定预算内完成性收益，但 B 无最终见证，不能断言其覆盖增减或精确时间。
- **窄转换饱和：保留当前 ITE，覆盖义务仍在。**A 三次完成，B 三次删失；A 每次目标转换四条都选择零源 lane，仅见 overflow 假，不见 overflow 真或新增 invalid/NV。这暴露默认见证集合不足，但不能凭此推断 B 一定补足。后续若评估该语义条件，需同一 Clause 的定向 true/false 见证与完成预算，再讨论取舍。
- **分类：暂不据此回退或宣称性能优势。**同一缩小的合法 SEW64/vl1 上两臂均到外限；十类见证不可用。应另行准备可完成且仍保持分类输入符号化的完整 Clause 入口，再作配对；小 helper 结果不能替代本轮 Clause 证据。

未测义务：三项 B 的完整终态和语义等价、分类十类分布、饱和 invalid 双侧见证及其它格式/SEW/LMUL 的推广。NaN 项只修改 f32 的结果规范化，不代表 f16/f64 的对应选择；饱和项只修改 f16→有符号16位，不代表所有窄转换。历史微测只用于选入口，没有充当本轮 PASS。
