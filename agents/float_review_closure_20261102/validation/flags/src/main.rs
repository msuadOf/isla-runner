// 直接调用实际 IR 的 accrue_fflags，避免指令写目标寄存器掩盖 changed 的作用。
use isla_lib::bitvector::b129::B129;
use isla_lib::bitvector::BV;
use isla_lib::config::ISAConfig;
use isla_lib::executor::{execute_ir_function, LocalFrame, Run};
use isla_lib::init::initialize_architecture;
use isla_lib::ir::{AssertionMode, IRTypeInfo, SharedState, Symtab, UVal, Val};
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
    width: u32,
) {
    let value = Val::Struct(
        [(shared.symtab.lookup("zbits"), bits(value, width))]
            .into_iter()
            .collect(),
    );
    regs.assign(shared.symtab.lookup(&format!("z{name}")), value, shared);
}

fn read_reg(
    frame: &LocalFrame<'_, B129>,
    shared: &SharedState<'_, B129>,
    solver: &mut isla_lib::smt::Solver<B129>,
    name: &str,
) -> u64 {
    let value = frame
        .regs()
        .get_last_if_initialized(shared.symtab.lookup(&format!("z{name}")))
        .unwrap();
    let Val::Struct(fields) = value else {
        panic!("{name} is not a struct")
    };
    let mut model = Model::new(solver);
    let concrete = model
        .get_val(&fields[&shared.symtab.lookup("zbits")])
        .unwrap();
    drop(model);
    let Val::Bits(value) = replace_mixed_bits(concrete, solver, SourceLoc::unknown()).unwrap()
    else {
        panic!("{name} is not concrete bits")
    };
    value.lower_u64()
}

fn main() {
    configure_tastic(Tactic::Qffp);
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(
        args.len(),
        3,
        "usage: float-flags-state-probe <IR> <config>"
    );
    let text = std::fs::read_to_string(&args[1]).unwrap();
    let function = text
        .split("fn zaccrue_fflags(zflags) {")
        .nth(1)
        .expect("accrue_fflags IR");
    let function = function.split("\n}\n").next().expect("accrue_fflags end");
    let first = function
        .find("zcsr_name_write_callback(\"fflags\",")
        .expect("fflags callback");
    let second = function
        .find("zcsr_name_write_callback(\"fcsr\",")
        .expect("fcsr callback");
    assert!(first < second, "CSR callback order changed");
    assert!(
        !function.contains("zlong_csr_write_callback"),
        "unexpected mstatus callback"
    );
    assert!(
        !function.contains("zdirty_fd_context_if_present"),
        "unexpected indirect mstatus callback"
    );
    assert_eq!(function.matches("zcsr_name_write_callback(").count(), 2);
    println!("CALLBACK_CONTRACT fflags,fcsr; no mstatus callback");

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
    let xlen = match state
        .lets
        .get(&state.shared_state.symtab.lookup("zxlen"))
        .unwrap()
    {
        UVal::Init(Val::I64(value)) => *value,
        value => panic!("xlen is not concrete: {value:?}"),
    };
    assert!(xlen == 32 || xlen == 64);
    let sd = 1_u64 << (xlen - 1);
    let fs_mask = 0b11_u64 << 13;
    // 这些位与 FS/SD 不重叠；RV32 也检查 64 位 mstatus 载体的高位保持。
    let sentinel = 0xa000_000a_0200_0600_u64 & !sd & !fs_mask;
    let cases = [
        ("zero", 0_u64, 0_u64),
        ("same_nv", 0x10, 0x10),
        ("new_nv", 0, 0x10),
        ("old_nx_new_nv", 0x01, 0x10),
        ("new_multiple", 0x04, 0x13),
    ];
    let mut checked = 0;
    for (label, old, incoming) in cases {
        for fs in [1_u64, 2, 3] {
            for initial_sd in [0_u64, sd] {
                for other in [0_u64, sentinel] {
                    let initial_status = other | initial_sd | (fs << 13);
                    let initial_fcsr = 0x1234_56a0_u64 | old;
                    let mut regs = state.regs.clone();
                    assign(&mut regs, &state.shared_state, "fcsr", initial_fcsr, 32);
                    assign(
                        &mut regs,
                        &state.shared_state,
                        "mstatus",
                        initial_status,
                        64,
                    );
                    let observed = Mutex::new(Vec::new());
                    execute_ir_function(
                        "zaccrue_fflags",
                        &[bits(incoming, 5)],
                        &state.shared_state,
                        &regs,
                        &state.lets,
                        &observed,
                        &|_, _, result, shared, mut solver, observed| {
                            let (return_value, frame) = match result {
                                Ok((Run::Finished(value), frame)) => (value, frame),
                                Err((error, _)) => panic!("{label}: IR error: {error:?}"),
                                Ok(_) => panic!("{label}: unfinished"),
                            };
                            assert!(matches!(return_value, Val::Unit));
                            assert_eq!(solver.check_sat(SourceLoc::unknown()), SmtResult::Sat);
                            let fcsr = read_reg(&frame, shared, &mut solver, "fcsr");
                            let mstatus = read_reg(&frame, shared, &mut solver, "mstatus");
                            observed.lock().unwrap().push((fcsr, mstatus));
                        },
                    );
                    let actual = observed.into_inner().unwrap();
                    assert_eq!(actual.len(), 1, "{label}: expected one finished path");
                    let changed = (old | incoming) != old;
                    let expected_fcsr = initial_fcsr | incoming;
                    let expected_status = if changed {
                        (initial_status & !fs_mask) | fs_mask | sd
                    } else {
                        initial_status
                    };
                    assert_eq!(actual[0], (expected_fcsr, expected_status),
                        "{label}: xlen={xlen} FS={fs} SD={} other={other:#x} old={old:#x} incoming={incoming:#x}",
                        initial_sd != 0);
                    println!(
                        "PASS {label} xlen={xlen} fs={fs} initial_sd={} other={other:#x} old_fcsr={initial_fcsr:#010x} initial_mstatus={initial_status:#018x} incoming={incoming:#04x} changed={changed} expected_fcsr={expected_fcsr:#010x} expected_mstatus={expected_status:#018x} fcsr={:#010x} mstatus={:#018x}",
                        initial_sd != 0,
                        actual[0].0,
                        actual[0].1
                    );
                    checked += 1;
                }
            }
        }
    }
    println!("PASS total={checked} xlen={xlen}");
}
