/* 独立验证官方 qffp 使用的 random_seed 经拦截变为 17。 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <z3.h>

int main(void) {
    Z3_config cfg = Z3_mk_config();
    Z3_context ctx = Z3_mk_context_rc(cfg);
    Z3_del_config(cfg);
    Z3_tactic tactic = Z3_mk_tactic(ctx, "qffp");
    Z3_tactic_inc_ref(ctx, tactic);
    Z3_solver solver = Z3_mk_solver_from_tactic(ctx, tactic);
    Z3_solver_inc_ref(ctx, solver);
    Z3_params params = Z3_mk_params(ctx);
    Z3_params_inc_ref(ctx, params);
    Z3_params_set_uint(ctx, params, Z3_mk_string_symbol(ctx, "random_seed"), 987654321);
    const char *text = Z3_params_to_string(ctx, params);
    puts(text);
    assert(strstr(text, "random_seed 17"));
    Z3_solver_set_params(ctx, solver, params);
    assert(Z3_solver_check(ctx, solver) == Z3_L_TRUE);
    Z3_params_dec_ref(ctx, params);
    Z3_solver_dec_ref(ctx, solver);
    Z3_tactic_dec_ref(ctx, tactic);
    Z3_del_context(ctx);
    return 0;
}
