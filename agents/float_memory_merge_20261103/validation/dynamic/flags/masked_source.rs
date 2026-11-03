// 直接执行合流 IR 的 init_masked_source，核 vstart 的 nat 适配边界。
use isla_lib::bitvector::b129::B129;
use isla_lib::bitvector::BV;
use isla_lib::config::ISAConfig;
use isla_lib::executor::{execute_ir_function, Run};
use isla_lib::init::initialize_architecture;
use isla_lib::ir::{AssertionMode, IRTypeInfo, SharedState, Symtab, Val};
use isla_lib::ir_lexer::new_ir_lexer;
use isla_lib::ir_parser::IrParser;
use isla_lib::primop_util::replace_mixed_bits;
use isla_lib::register::RegisterBindings;
use isla_lib::smt::{configure_tastic, Model, SmtResult, Tactic};
use isla_lib::source_loc::SourceLoc;
use std::sync::Mutex;

fn bits(value: u64, width: u32) -> Val<B129> {
    Val::Bits(B129::new(value, width))
}

fn assign<'ir>(
    regs: &mut RegisterBindings<'ir, B129>,
    shared: &SharedState<'ir, B129>,
    name: &str,
    value: u64,
) {
    let value = if name == "vtype" {
        Val::Struct(
            [(shared.symtab.lookup("zbits"), bits(value, 64))]
                .into_iter()
                .collect(),
        )
    } else {
        bits(value, 64)
    };
    regs.assign(shared.symtab.lookup(&format!("z{name}")), value, shared);
}

fn main() {
    configure_tastic(Tactic::Qfaufbv);
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(args.len(), 3, "usage: masked-source-probe <IR> <config>");
    let text = std::fs::read_to_string(&args[1]).unwrap();
    assert!(text.contains("val zinit_masked_source : (%i, %i, %bv) ->  %union zresultzIbzCuzK"));
    let ir = Box::leak(text.into_boxed_str());
    let mut symtab = Symtab::new();
    let defs = IrParser::new()
        .parse(&mut symtab, new_ir_lexer(ir))
        .expect("IR parse");
    let types = IRTypeInfo::new(&defs);
    let config = ISAConfig::parse(
        &std::fs::read_to_string(&args[2]).unwrap(),
        None,
        &symtab,
        &types,
    )
    .expect("config");
    let defs = Box::leak(defs.into_boxed_slice());
    let state = initialize_architecture(
        defs,
        symtab,
        types,
        &config,
        AssertionMode::Optimistic,
        false,
    );
    for (label, start, expected) in [
        ("active", 0, 1),
        ("equal", 1, 0),
        ("greater", 2, 0),
        ("large", u64::MAX, 0),
    ] {
        let mut regs = state.regs.clone();
        assign(&mut regs, &state.shared_state, "vtype", 0x10); // SEW32, LMUL1; VLEN128 => 4 elements.
        assign(&mut regs, &state.shared_state, "vl", 1);
        assign(&mut regs, &state.shared_state, "vstart", start);
        let results = Mutex::new(Vec::new());
        execute_ir_function(
            "zinit_masked_source",
            &[Val::I128(4), Val::I128(0), bits(0xf, 4)],
            &state.shared_state,
            &regs,
            &state.lets,
            &results,
            &|_, _, result, shared, mut solver, results| {
                let value = match result {
                    Ok((Run::Finished(value), _)) => value,
                    Err((error, _)) => panic!("{label}: IR error: {error:?}"),
                    Ok(_) => panic!("{label}: unfinished"),
                };
                assert_eq!(solver.check_sat(SourceLoc::unknown()), SmtResult::Sat);
                let concrete = Model::new(&solver).get_val(&value).unwrap();
                let Val::Ctor(name, payload) = concrete else {
                    panic!("{label}: result is not Ok constructor")
                };
                assert_eq!(name, shared.symtab.lookup("zOkzIbzCuzK"), "{label}: not Ok");
                let Val::Bits(mask) =
                    replace_mixed_bits(*payload, &mut solver, SourceLoc::unknown()).unwrap()
                else {
                    panic!("{label}: Ok payload is not concrete bitvector")
                };
                assert_eq!(mask.len(), 4, "{label}: mask width");
                results.lock().unwrap().push(mask.lower_u64());
            },
        );
        let actual = results.into_inner().unwrap();
        assert_eq!(actual.as_slice(), &[expected], "{label}: start={start:#x}");
        println!("PASS {label} vstart={start:#x} vl=1 mask={:#x}", actual[0]);
    }
    println!("PASS total=4");
}
