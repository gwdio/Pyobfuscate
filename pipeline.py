import ast
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Import strategy modules so subclasses register via __init_subclass__
import Encryption.number_obscure_strategies as _num_strats
import Injectors.junk_strategies as _junk_strats
import Injectors.junk_conditional_strategies as _cond_strats
import Injectors.identity_strategies as _id_strats
import LoopObfuscation.obfuscation_strategies as _loop_strats

from Encryption.number_obscure_strategies import NumberObscureStrategy
from Encryption.number_obscurer import NumberObscurerInjector
from Injectors.conditional_injector import ConditionalInjector
from Injectors.identity_injector import IdentityFuncInjector
from Injectors.identity_strategies import MixedIdentityStrategy
from Injectors.inject_junk import JunkInjector
from Injectors.junk_conditional_strategies import JunkConditionalStrategy
from Injectors.junk_strategies import JunkInjectionStrategy
from LoopObfuscation.ob_for import Ob_For
from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
from Renaming.renamer import Renamer
from NameTracker.naming import Naming

DEFAULT_STAGE_ORDER = ["junk", "loops", "conditionals", "identities", "numbers", "renaming"]


@dataclass
class ObfuscationConfig:
    input_path: Path

    output_path: Optional[Path] = None

    # per-phase toggles
    enable_junk: bool = True
    enable_loops: bool = True
    enable_conditionals: bool = True
    enable_identities: bool = True
    enable_numbers: bool = True
    enable_renaming: bool = True

    # strategy selections (use class names from registry)
    junk_strategies: List[str] = field(default_factory=lambda: ["BitwiseStrategy", "NonConstantTimeStrategy", "ArithmeticStrategy"])
    junk_density: int = 2
    loop_strategy: str = "CollatzStrategy"
    conditional_strategies: List[str] = field(default_factory=lambda: ["RandomConditionalStrategy"])
    identity_probability: float = 0.2
    number_strategies: List[str] = field(default_factory=lambda: ["FeistelNumberStrategy", "XorStringNumberStrategy"])

    # ordered list of stages; None means use DEFAULT_STAGE_ORDER
    stage_order: Optional[List[str]] = None

    # output options
    return_code: bool = True
    seed: Optional[int] = None


def _resolve(registry: dict, name: str, phase: str):
    if name not in registry:
        valid = ", ".join(sorted(registry))
        raise ValueError(f"Unknown {phase} strategy '{name}'. Valid options: {valid}")
    return registry[name]


def run_pipeline(cfg: ObfuscationConfig) -> str:
    input_path = Path(cfg.input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    stages = cfg.stage_order if cfg.stage_order is not None else DEFAULT_STAGE_ORDER

    rng = random.Random(cfg.seed)

    code = input_path.read_text(encoding="utf-8")
    tree = ast.parse(code, mode="exec")

    naming = Naming()
    naming.analyze(tree)

    for stage in stages:
        if stage == "junk" and cfg.enable_junk and cfg.junk_strategies:
            selected = [_resolve(JunkInjectionStrategy._registry, k, "junk") for k in cfg.junk_strategies]
            tree = JunkInjector(naming, selected, cfg.junk_density, rng).apply(tree)

        elif stage == "loops" and cfg.enable_loops:
            loop_cls = _resolve(LoopObfuscationStrategy._registry, cfg.loop_strategy, "loop")
            tree = Ob_For(naming, loop_cls, rng).apply(tree)

        elif stage == "conditionals" and cfg.enable_conditionals and cfg.conditional_strategies:
            cond_selected = [_resolve(JunkConditionalStrategy._registry, k, "conditional") for k in cfg.conditional_strategies]
            tree = ConditionalInjector(naming, cond_selected, 1, rng).apply(tree)

        elif stage == "identities" and cfg.enable_identities:
            tree = IdentityFuncInjector(MixedIdentityStrategy(), cfg.identity_probability, rng).apply(tree)

        elif stage == "numbers" and cfg.enable_numbers and cfg.number_strategies:
            for ns in cfg.number_strategies:
                tree = NumberObscurerInjector(naming, _resolve(NumberObscureStrategy._registry, ns, "number"), rng).apply(tree)

        elif stage == "renaming" and cfg.enable_renaming:
            tree = Renamer(naming.get_namespace(), rng).apply(tree)

    tree = ast.fix_missing_locations(tree)
    return ast.unparse(tree)
