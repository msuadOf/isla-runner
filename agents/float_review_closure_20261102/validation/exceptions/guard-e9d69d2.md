# e9d69d2 定向oracle版本门准备

候选模型 `e9d69d2f28586c089244c8e37ee4c904c5114458` 的直接父提交是 `21418d0b0d4942fae20061ed580ee04aff4a8a61`。两版之间仅 `model/core/ieee_fp_exceptions.sail` 一文件变化，Git diff SHA-256 `9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd`；该差异由数值事实构造、finite gate 与ROD jam相关源码组成，**本版本门仅绑定精确差异，不把等价性当作已动态证明**。

执行器 `run_directed.py` SHA-256 `8475d90d35d3d52195bbeb6bab4ab5cfe28d669536cb82aa61610c55e2efe311`。相对上版已签执行器 `613e0441923a42650165da75a14bed730704bb16d08f09cda056c65008d12cd9` 的精确补丁见 `guard-e9d69d2.diff`（SHA-256 `c71166866d64da987ff0b3f7abacbc1f65ca8d489f5e512200001e540ed8bd99`）；逆替补丁后字节哈希复原旧版。新分支固定候选完整commit、父提交、唯一变动文件及diff哈希；`launch.json` 将记录实际模型、`expected.json` 的来源 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde` 和214→e9差异。独立SoftFloat `expected.json` SHA-256 `6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891` 不变，数值315项须用e9新IR再次执行才能签新结果。

已用214正式冻结inputs只读 `--dry-run`，旧版本门仍退出0。生成agent报告e9四份strict IR均exit0/source unchanged；新V128 IR SHA-256 `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad`。截至本记录，正式e9 `inputs.<批次>.json` 未封存，故**尚未运行新IR动态批次**。待正式清单、精确哈希和独立预签齐备，在分配CPU17/29上对独立新目录先dry-run再后台运行315项；原214结果不改署候选。
