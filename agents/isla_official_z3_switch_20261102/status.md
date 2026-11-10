# Isla正式切换官方Z3：完成／限定验证通过

所有请求检出的Make默认Z3_PREFIX已设为用户级`~/.local/opt/z3-official-1fd1d3613`；安装自官方干净源码提交`1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b`的独立Release构建，库SHA256与此前官方构建一致。未改系统库或全局PATH。

## 代码与二进制

根isla/feat/float-support、runner-float、memory-consistency及runner-memory的Make均显式传native链接搜索目录与同一RPATH；内存分支原先没有Z3_PREFIX的入口已按现有float写法补齐。README记录版本化前缀和覆盖方式。保留之前CLI缺省default、347Clause具体qffp/qfaufbv策略和全部在途源码修改，无报错/回退逻辑新增。

实际运行make build-isarch重编译根、runner-float与runner-memory（各CARGO_BUILD_JOBS=8）；注意runner-memory与memory-consistency共享target，因此无需重复构建；runner-float也使用原已有共享target链接关系，不移动target。四处Release --version均含官方完整SHA，ldd -r无缺失符号、RUNPATH与NEEDED均指向正式前缀/5.3。根Debug另用cargo rustc最终链接参数重链接，也已显示官方SHA。本次正式程序是源码重编译，不是前次隔离ELF替换。完整证据见link-verification.json、relink-root-debug.log、build-*.log。

## 运行与测试

- 根/float各自CLI不传--tastic的FLEQ_S，以及实际Make solve-FLEQ_S（显式qffp）共4次：全部退出0、gen10、status finished、errors/执行超时/SMT超时/未完成均0。
- memory压缩访存C_LD固定0x6088、Machine、mstatus及x9=0x80000000：CLI缺省default和显式qfaufbv两次均退出0、gen1、finished且含memory-events，错误/超时/未完成均0。
- 六次运行全部用正式新Release程序；Make验证在独立输出目录跳过重复build（先前已在真实检出make build-isarch），使用实际recipe和target策略，无需覆盖TASTIC。记录命令、IR/config/binary哈希、wall时间与summary，见smoke-results.json。没有将单条定向访存外推全memory支持。
- 官方新库下release smt_init 2/2通过（含既有fail-fast/线程/SMT及默认策略/显式qffp解析）；四份源码diff-check及格式检查通过。无新增Rust源码改动。

原output未覆盖，旧系统Z3与fork构建保留。配置与README改动尚未commit/push，不移动父gitlink。未全Clause/全77/全部访存回归。普通make从现在起固定新库；如手工绕开make使用cargo，应自行给同样的链接参数，不能只换PATH。
