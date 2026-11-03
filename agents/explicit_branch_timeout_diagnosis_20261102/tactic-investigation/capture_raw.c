#define _GNU_SOURCE
#include <z3.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Experiment only: retain the ASTs passed to assert before the tactic sees them. */
struct state {
    Z3_solver solver;
    Z3_context context;
    Z3_ast *assertions;
    unsigned count, capacity;
    struct state *next;
};
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static struct state *states;
static unsigned long sequence;
static int target_hit;

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

static void compare_tactics(Z3_context c, struct state *p, unsigned n, Z3_ast const assumptions[]) {
    const char *path = getenv("ISLA_COMPARE_LOG");
    if (!path) return;
    FILE *f = fopen(path, "w");
    if (!f) abort();
    static const char *names[3] = {"qffp", "default", "smt"};
    static const unsigned order[3][3] = {{0, 1, 2}, {2, 0, 1}, {1, 2, 0}};
    Z3_lbool (*real_check)(Z3_context, Z3_solver, unsigned, Z3_ast const[]) =
        dlsym(RTLD_NEXT, "Z3_solver_check_assumptions");
    void (*real_assert)(Z3_context, Z3_solver, Z3_ast) = dlsym(RTLD_NEXT, "Z3_solver_assert");
    void (*real_dec_ref)(Z3_context, Z3_solver) = dlsym(RTLD_NEXT, "Z3_solver_dec_ref");
    fprintf(f, "round\tposition\ttactic\tassertions\tassumptions\tresult\tseconds\treason\n");
    fflush(f);
    Z3_goal goal = Z3_mk_goal(c, true, false, false);
    Z3_goal_inc_ref(c, goal);
    for (unsigned i = 0; i < p->count; i++) Z3_goal_assert(c, goal, p->assertions[i]);
    for (unsigned i = 0; i < n; i++) Z3_goal_assert(c, goal, assumptions[i]);
    Z3_tactic simplify = Z3_mk_tactic(c, "simplify");
    Z3_tactic_inc_ref(c, simplify);
    Z3_apply_result simplified = Z3_tactic_apply(c, simplify, goal);
    Z3_apply_result_inc_ref(c, simplified);
    Z3_probe qffp_probe = Z3_mk_probe(c, "is-qffp");
    Z3_probe_inc_ref(c, qffp_probe);
    unsigned subgoals = Z3_apply_result_get_num_subgoals(c, simplified);
    for (unsigned i = 0; i < subgoals; i++) {
        Z3_goal subgoal = Z3_apply_result_get_subgoal(c, simplified, i);
        fprintf(f, "probe\t%u\tis-qffp-after-simplify\t%u\t%u\t%.0f\t0\t\n",
            i, p->count, n, Z3_probe_apply(c, qffp_probe, subgoal));
    }
    fflush(f);
    Z3_probe_dec_ref(c, qffp_probe);
    Z3_apply_result_dec_ref(c, simplified);
    Z3_tactic_dec_ref(c, simplify);
    Z3_goal_dec_ref(c, goal);
    if (getenv("ISLA_PROBE_ONLY")) {
        fclose(f);
        return;
    }
    const char *only = getenv("ISLA_COMPARE_ONE");
    for (unsigned round = 0; round < (only ? 1U : 3U); round++) {
        for (unsigned position = 0; position < (only ? 1U : 3U); position++) {
            const char *name = only ? only : names[order[round][position]];
            Z3_tactic tactic = Z3_mk_tactic(c, name);
            Z3_tactic_inc_ref(c, tactic);
            Z3_solver solver = Z3_mk_solver_from_tactic(c, tactic);
            Z3_solver_inc_ref(c, solver);
            Z3_tactic_dec_ref(c, tactic);
            Z3_params params = Z3_mk_params(c);
            Z3_params_inc_ref(c, params);
            Z3_params_set_uint(c, params, Z3_mk_string_symbol(c, "random_seed"), 17);
            Z3_params_set_uint(c, params, Z3_mk_string_symbol(c, "timeout"), 7200000);
            Z3_solver_set_params(c, solver, params);
            Z3_params_dec_ref(c, params);
            for (unsigned i = 0; i < p->count; i++) real_assert(c, solver, p->assertions[i]);
            double started = now();
            Z3_lbool result = real_check(c, solver, n, assumptions);
            double elapsed = now() - started;
            const char *reason = result == Z3_L_UNDEF ? Z3_solver_get_reason_unknown(c, solver) : "";
            fprintf(f, "%u\t%u\t%s\t%u\t%u\t%d\t%.9f\t%s\n",
                round, position, name, p->count, n, result, elapsed, reason);
            fflush(f);
            real_dec_ref(c, solver);
        }
    }
    fclose(f);
}

static struct state *get_state(Z3_context c, Z3_solver s) {
    for (struct state *p = states; p; p = p->next)
        if (p->solver == s) return p;
    struct state *p = calloc(1, sizeof(*p));
    if (!p) abort();
    p->solver = s;
    p->context = c;
    p->next = states;
    states = p;
    return p;
}

void Z3_solver_assert(Z3_context c, Z3_solver s, Z3_ast a) {
    static void (*real_assert)(Z3_context, Z3_solver, Z3_ast);
    if (!real_assert) real_assert = dlsym(RTLD_NEXT, "Z3_solver_assert");
    pthread_mutex_lock(&mutex);
    struct state *p = get_state(c, s);
    if (p->count == p->capacity) {
        p->capacity = p->capacity ? p->capacity * 2 : 64;
        p->assertions = realloc(p->assertions, p->capacity * sizeof(Z3_ast));
        if (!p->assertions) abort();
    }
    Z3_inc_ref(c, a);
    p->assertions[p->count++] = a;
    pthread_mutex_unlock(&mutex);
    real_assert(c, s, a);
}

void Z3_solver_dec_ref(Z3_context c, Z3_solver s) {
    static void (*real_dec_ref)(Z3_context, Z3_solver);
    if (!real_dec_ref) real_dec_ref = dlsym(RTLD_NEXT, "Z3_solver_dec_ref");
    pthread_mutex_lock(&mutex);
    struct state **cursor = &states;
    while (*cursor) {
        if ((*cursor)->solver == s) {
            struct state *p = *cursor;
            *cursor = p->next;
            for (unsigned i = 0; i < p->count; i++) Z3_dec_ref(c, p->assertions[i]);
            free(p->assertions);
            free(p);
            break;
        }
        cursor = &(*cursor)->next;
    }
    pthread_mutex_unlock(&mutex);
    real_dec_ref(c, s);
}

static void before_check(Z3_context c, Z3_solver s, unsigned n, Z3_ast const assumptions[]) {
    pthread_mutex_lock(&mutex);
    unsigned long id = ++sequence;
    const char *target = getenv("ISLA_CAPTURE_QUERY");
    if (target && strtoul(target, NULL, 10) == id) {
        struct state *p = get_state(c, s);
        if (p->context != c) abort();
        Z3_ast *all = malloc((p->count + n) * sizeof(Z3_ast));
        if (!all) abort();
        memcpy(all, p->assertions, p->count * sizeof(Z3_ast));
        memcpy(all + p->count, assumptions, n * sizeof(Z3_ast));
        const char *content = Z3_benchmark_to_smtlib_string(
            c, "isla-raw-assertions", "ALL", "unknown", "",
            p->count + n, all, Z3_mk_true(c));
        const char *path = getenv("ISLA_CAPTURE_PATH");
        if (!path) abort();
        FILE *f = fopen(path, "w");
        if (!f) abort();
        fprintf(f, "; query=%lu raw_assertions=%u assumptions=%u\n%s\n", id, p->count, n, content);
        if (fclose(f)) abort();
        free(all);
        if (getenv("ISLA_CAPTURE_ONLY")) _Exit(0);
        if (getenv("ISLA_ORIGINAL_FIRST")) {
            target_hit = 1;
            pthread_mutex_unlock(&mutex);
            return;
        }
        compare_tactics(c, p, n, assumptions);
        if (getenv("ISLA_COMPARE_ONLY")) _Exit(0);
        target_hit = 1;
    }
    pthread_mutex_unlock(&mutex);
}

Z3_lbool Z3_solver_check(Z3_context c, Z3_solver s) {
    static Z3_lbool (*real_check)(Z3_context, Z3_solver);
    if (!real_check) real_check = dlsym(RTLD_NEXT, "Z3_solver_check");
    before_check(c, s, 0, NULL);
    double started = now();
    Z3_lbool result = real_check(c, s);
    double elapsed = now() - started;
    if (target_hit && getenv("ISLA_COMPARE_STOP")) {
        const char *log_path = getenv("ISLA_ORIGINAL_LOG") ? getenv("ISLA_ORIGINAL_LOG") : getenv("ISLA_COMPARE_LOG");
        FILE *f = fopen(log_path, "a");
        if (!f) abort();
        fprintf(f, "original\t0\tqffp-incremental\t0\t0\t%d\t%.9f\t%s\n", result, elapsed,
            result == Z3_L_UNDEF ? Z3_solver_get_reason_unknown(c, s) : "");
        fclose(f);
        if (getenv("ISLA_ORIGINAL_FIRST")) {
            pthread_mutex_lock(&mutex);
            compare_tactics(c, get_state(c, s), 0, NULL);
            pthread_mutex_unlock(&mutex);
        }
        _Exit(0);
    }
    return result;
}

Z3_lbool Z3_solver_check_assumptions(Z3_context c, Z3_solver s, unsigned n, Z3_ast const assumptions[]) {
    static Z3_lbool (*real_check)(Z3_context, Z3_solver, unsigned, Z3_ast const[]);
    if (!real_check) real_check = dlsym(RTLD_NEXT, "Z3_solver_check_assumptions");
    before_check(c, s, n, assumptions);
    double started = now();
    Z3_lbool result = real_check(c, s, n, assumptions);
    double elapsed = now() - started;
    if (target_hit && getenv("ISLA_COMPARE_STOP")) {
        const char *log_path = getenv("ISLA_ORIGINAL_LOG") ? getenv("ISLA_ORIGINAL_LOG") : getenv("ISLA_COMPARE_LOG");
        FILE *f = fopen(log_path, "a");
        if (!f) abort();
        fprintf(f, "original\t0\tqffp-incremental\t0\t%u\t%d\t%.9f\t%s\n", n, result, elapsed,
            result == Z3_L_UNDEF ? Z3_solver_get_reason_unknown(c, s) : "");
        fclose(f);
        if (getenv("ISLA_ORIGINAL_FIRST")) {
            pthread_mutex_lock(&mutex);
            compare_tactics(c, get_state(c, s), n, assumptions);
            pthread_mutex_unlock(&mutex);
        }
        _Exit(0);
    }
    return result;
}
