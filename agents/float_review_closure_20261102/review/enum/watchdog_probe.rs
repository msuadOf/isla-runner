use isla_lib::bitvector::b64::B64;
use isla_lib::error::SmtError;
use isla_lib::smt::{self, Config, Context, SmtResult, Solver, Tactic};
use isla_lib::source_loc::SourceLoc;
use std::time::{Duration, Instant};

fn main() {
    smt::configure_tastic(Tactic::Qffp);
    smt::configure_z3_timeout(Some(Duration::from_millis(10)));
    let ctx = Context::new(Config::new());
    let mut solver = Solver::<B64>::new(&ctx);
    let started = Instant::now();
    match solver.check_sat(SourceLoc::unknown()) {
        SmtResult::Error(SmtError::Timeout(timeout)) => {
            assert_eq!(timeout.limit, Duration::from_millis(10));
            assert!(started.elapsed() >= Duration::from_millis(40));
            println!("watchdog_timeout=true limit_ms=10 wall_ms={}", started.elapsed().as_millis());
        }
        other => panic!("watchdog 未触发：{other:?}"),
    }
}
