# 只由 make_solve.py 生成的附加 Makefile 加载；没有业务规则副本。
_scheduler_original_shell := $(SHELL)
_scheduler_original_flags := $(.SHELLFLAGS)
solve-%: private override SHELL := $(SCHEDULER_SHELL)
solve-%: private override .SHELLFLAGS = --target=$@ -c
# 管理目标和组入口仍使用原生 shell，private 阻止接点传播到编译依赖。
solve-pre solve-kill solve solve-fd-float solve-fd-nonmem solve-memory: private override SHELL := $(_scheduler_original_shell)
solve-pre solve-kill solve solve-fd-float solve-fd-nonmem solve-memory: private override .SHELLFLAGS := $(_scheduler_original_flags)
