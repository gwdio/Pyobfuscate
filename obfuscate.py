import argparse
import sys
from pathlib import Path

from pipeline import DEFAULT_STAGE_ORDER, ObfuscationConfig, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obfuscate",
        description="Obfuscate Python source code via AST transformations.",
    )

    # I/O
    p.add_argument("--input", default="IO/input.py", metavar="FILE", help="Input .py file (default: IO/input.py)")
    p.add_argument("--output", default="IO/output.py", metavar="FILE", help="Output .py file (default: IO/output.py)")
    p.add_argument("--print", dest="print_output", action="store_true", help="Print result to stdout instead of writing file")

    # Reproducibility
    p.add_argument("--seed", type=int, default=None, metavar="N", help="Random seed for deterministic output")

    # Per-phase toggles
    p.add_argument("--no-junk", dest="enable_junk", action="store_false", help="Skip junk injection")
    p.add_argument("--no-loops", dest="enable_loops", action="store_false", help="Skip loop obfuscation")
    p.add_argument("--no-conditionals", dest="enable_conditionals", action="store_false", help="Skip conditional wrapping")
    p.add_argument("--no-identities", dest="enable_identities", action="store_false", help="Skip identity injection")
    p.add_argument("--no-numbers", dest="enable_numbers", action="store_false", help="Skip number obfuscation")
    p.add_argument("--no-renaming", dest="enable_renaming", action="store_false", help="Skip identifier renaming")

    # Tuning knobs
    p.add_argument("--junk-density", type=int, default=2, metavar="N", choices=range(1, 6), help="Junk injection density 1–5 (default: 2)")
    p.add_argument("--identity-prob", type=float, default=0.2, metavar="P", help="Identity wrapping probability 0.0–1.0 (default: 0.2)")

    # Stage ordering
    p.add_argument(
        "--stages",
        nargs="+",
        metavar="STAGE",
        default=None,
        help=f"Ordered stages to run (default: {' '.join(DEFAULT_STAGE_ORDER)})",
    )

    # Per-phase strategy selection
    p.add_argument(
        "--junk-strategies",
        nargs="+",
        metavar="NAME",
        default=["BitwiseStrategy", "NonConstantTimeStrategy", "ArithmeticStrategy"],
        help="Junk strategy class names",
    )
    p.add_argument("--loop-strategy", default="CollatzStrategy", metavar="NAME", help="Loop obfuscation strategy class name")
    p.add_argument(
        "--conditional-strategies",
        nargs="+",
        metavar="NAME",
        default=["RandomConditionalStrategy"],
        help="Conditional strategy class names",
    )
    p.add_argument(
        "--number-strategies",
        nargs="+",
        metavar="NAME",
        default=["FeistelNumberStrategy", "XorStringNumberStrategy"],
        help="Number obfuscation strategy class names",
    )

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    cfg = ObfuscationConfig(
        input_path=Path(args.input),
        output_path=None if args.print_output else Path(args.output),
        seed=args.seed,
        enable_junk=args.enable_junk,
        enable_loops=args.enable_loops,
        enable_conditionals=args.enable_conditionals,
        enable_identities=args.enable_identities,
        enable_numbers=args.enable_numbers,
        enable_renaming=args.enable_renaming,
        junk_density=args.junk_density,
        identity_probability=args.identity_prob,
        stage_order=args.stages,
        junk_strategies=args.junk_strategies,
        loop_strategy=args.loop_strategy,
        conditional_strategies=args.conditional_strategies,
        number_strategies=args.number_strategies,
        return_code=args.print_output,
    )

    try:
        result = run_pipeline(cfg)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.print_output:
        print(result)
    else:
        Path(args.output).write_text(result, encoding="utf-8")


if __name__ == "__main__":
    main()
