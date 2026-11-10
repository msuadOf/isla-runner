# 官方最新Z3：编译与限定验证完成

官方master在2026-11-02查询head为1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b（Accept enumeration expressions in existing QFFP probes #11506），5.3.4.0。本次直接使用官方干净detached checkout，不包含fork自定义CI或旧A全局前处理。源码构建后仍干净；相关四solver/test文件与维护者最终路线一致。

## 可使用的构建

- 源码：.tmp/z3-official-20261102/src
- 独立Release/Ninja构建：.tmp/z3-official-20261102/build
- 安装前缀（Z3_PREFIX）：.tmp/z3-official-20261102/install
- 命令行：.tmp/z3-official-20261102/install/bin/z3
- 共享库：.tmp/z3-official-20261102/install/lib/libz3.so（SONAME libz3.so.5.3）
- 附带C/C++headers、CMake/pkgconfig信息。

以GCC15.2、CMake4.2.3构建Release，parallel24，BUILD_SHARED_LIBS=ON，无Python绑定。目标shell/libz3/test-z3全部构建、cmake install成功。CLI --version包含准确官方SHA。命令/编译器/哈希见manifest.json；配置、构建和安装日志完整保留。

## 新执行的验证

- test-z3 fpa：PASS（fpa.stdout）。
- 原枚举＋FP最小例：default SAT，约0.53秒。
- 原真实flags-11：default SAT，约8.33秒。两个query均显式SMT7200000ms，单次执行，不作为A/B性能比较。
- 18项C API检查及64次原断言模型求值全true；含枚举域、假设与push/pop恢复。
- 当前Isla debug的独立副本明确链接本次新库：ldd -r无缺失符号，--version指向官方1fd1d3613；default FLEQ_S退出0，17.13秒，gen10/status finished，errors/执行/SMT/模型求值超时/unfinished均0。IR/config与二进制哈希及完整命令见manifest/runtime JSON。此项是debug兼容性smoke，不是正式重新编译或生产切换。

未更改系统Z3、既有fork main/构建、Isla在途源码修改、模型/IR或父gitlink。没有自动将Make默认Z3_PREFIX切换到新前缀。未全Clause/内存回归。可用本安装前缀重新链接Isla；不要仅替换PATH中的z3来推断共享库已切换。
