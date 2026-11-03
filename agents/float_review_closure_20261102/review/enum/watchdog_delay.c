/* 仅供短探针：人为延后受保护的真实调用，观察 Rust watchdog。 */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
#include <z3.h>

Z3_lbool Z3_solver_check(Z3_context ctx, Z3_solver solver) {
    Z3_lbool (*original)(Z3_context, Z3_solver) = dlsym(RTLD_NEXT, "Z3_solver_check");
    assert(original);
    usleep(80000);
    return original(ctx, solver);
}

void Z3_interrupt(Z3_context ctx) {
    void (*original)(Z3_context) = dlsym(RTLD_NEXT, "Z3_interrupt");
    assert(original);
    fputs("watchdog_called_Z3_interrupt\n", stderr);
    original(ctx);
}
