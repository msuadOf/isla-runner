extern crate isla_lib;
use isla_lib::bitvector::b64::B64;
use isla_lib::ir::Name;
use isla_lib::smt::{self, checkpoint, Checkpoint, Config, Context, Event, Model, SmtResult, Solver};
use isla_lib::smt::smtlib::{self, Def, Exp, Ty};
use isla_lib::source_loc::SourceLoc;

fn ordered(cp: &Checkpoint<B64>) -> Vec<String> {
    cp.trace().as_ref().map_or_else(Vec::new, |tr| tr.to_vec().into_iter().rev().map(|ev| format!("{:?}", ev)).collect())
}
fn main() {
    smt::configure_tastic(smt::Tactic::Qfaufbv);
    let loc = SourceLoc::unknown();
    let ctx = Context::new(Config::new());
    let empty = Checkpoint::<B64>::new();
    let isolated_empty = empty.without_assertions();
    let combined_empty = empty.with_suffix_from(&isolated_empty, &isolated_empty);
    assert_eq!(Solver::from_checkpoint(&ctx, combined_empty).check_sat(loc), SmtResult::Sat);

    let mut s = Solver::<B64>::new(&ctx);
    let x = s.declare_const(Ty::BitVec(8), loc);
    let function = s.fresh();
    s.add(Def::DeclareFun(function, vec![Ty::BitVec(8)], Ty::BitVec(8)));
    let y = s.define_const(Exp::App(function, vec![Exp::Var(x)]), loc);
    s.assert_eq(Exp::Var(x), smtlib::bits64(16, 8));
    s.assert_eq(Exp::Var(y), smtlib::bits64(33, 8));
    s.trace_call(Name::from_u32(700));
    let _middle = checkpoint(&mut s);
    let en = s.get_enum(Name::from_u32(701), 3);
    let e = s.declare_const(Ty::Enum(en), loc);
    s.assert_eq(Exp::Var(e), Exp::Enum(en.first_member()));
    s.trace_return(Name::from_u32(700));
    let full = checkpoint(&mut s);
    let isolated = full.without_assertions();
    assert!(!isolated.trace().as_ref().unwrap().to_vec().iter().any(|ev| matches!(ev, Event::Smt(Def::Assert(_), _, _))));

    let helper_ctx = Context::new(Config::new());
    let mut helper = Solver::from_checkpoint(&helper_ctx, isolated.clone());
    helper.trace_call(Name::from_u32(702));
    let first = helper.declare_const(Ty::Bool, loc);
    helper.assert(Exp::Var(first));
    let _suffix_middle = checkpoint(&mut helper);
    let en2 = helper.get_enum(Name::from_u32(703), 2);
    let e2 = helper.declare_const(Ty::Enum(en2), loc);
    helper.assert_eq(Exp::Var(e2), Exp::Enum(en2.first_member()));
    helper.trace_return(Name::from_u32(702));
    let candidate = checkpoint(&mut helper);
    let expected_next = helper.fresh();
    let combined = full.with_suffix_from(&isolated, &candidate);
    let combined_events = ordered(&combined);
    let original_events = ordered(&full);
    let candidate_events = ordered(&candidate);
    let isolated_events = ordered(&isolated);
    assert_eq!(&combined_events[..original_events.len()], original_events.as_slice());
    assert_eq!(&combined_events[original_events.len()..], &candidate_events[isolated_events.len()..]);
    let final_ctx = Context::new(Config::new());
    let mut replayed = Solver::from_checkpoint(&final_ctx, combined);
    assert_eq!(replayed.fresh(), expected_next);
    assert_eq!(replayed.check_sat(loc), SmtResult::Sat);
    let mut model = Model::new(&replayed);
    assert_eq!(model.get_var(y).unwrap().unwrap_exp(), smtlib::bits64(33, 8));

    let unrelated = isolated.without_assertions();
    let panic_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let invalid_ancestor = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| full.with_suffix_from(&unrelated, &candidate)));
    std::panic::set_hook(panic_hook);
    assert!(invalid_ancestor.is_err());
    println!("PASS: 空checkpoint、函数声明/定义、双原段/双辅助段、两枚举、全部事件原序、fresh恢复、模型回读与非祖先拒绝");
}
