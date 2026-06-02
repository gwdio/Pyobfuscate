# app.py
import ast
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# === Libraries ===
from Encryption.number_obscure_strategies import (
    FeistelNumberStrategy,
    XorStringNumberStrategy,
    SimpleFeistelNumberStrategy,
)
from Encryption.number_obscurer import NumberObscurerInjector
from Injectors.conditional_injector import ConditionalInjector
from Injectors.identity_injector import IdentityFuncInjector
from Injectors.identity_strategies import MixedIdentityStrategy
from Injectors.inject_junk import JunkInjector
from Injectors.junk_conditional_strategies import RandomConditionalStrategy
from Injectors.junk_strategies import (
    ArithmeticStrategy,
    BitwiseStrategy,
    NonConstantTimeStrategy,
    LambdaStrategy,
)
from LoopObfuscation.ob_for import Ob_For
from LoopObfuscation.obfuscation_strategies import PlainStrategy, CollatzStrategy
from Renaming.renamer import Renamer
from NameTracker.naming import Naming

# ------------------------------------------------------------------------------
# Deterministic seeding for global `random` (no big refactor)
# ------------------------------------------------------------------------------
import random

@contextmanager
def seeded(seed: Optional[int]):
    """Temporarily set the global random seed, then restore previous RNG state."""
    if seed is None:
        yield
        return
    state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(state)

# Optional: add NumPy seeding too if you know some strategies call np.random
# import numpy as np
# @contextmanager
# def seeded(seed: Optional[int]):
#     if seed is None:
#         yield
#         return
#     state_py = random.getstate()
#     state_np = np.random.get_state()
#     random.seed(seed)
#     np.random.seed(seed)
#     try:
#         yield
#     finally:
#         random.setstate(state_py)
#         np.random.set_state(state_np)

# Prevent concurrent requests from interleaving and clobbering RNG state
_PIPELINE_LOCK = threading.RLock()

# ------------------------------------------------------------------------------
# API setup
# ------------------------------------------------------------------------------
app = FastAPI(title="Obfuscator API", version="1.0.0")

# ---- registries to map simple strings -> classes ----
JUNK_STRATEGIES = {
    "arithmetic": ArithmeticStrategy,
    "bitwise": BitwiseStrategy,
    "non_constant_time": NonConstantTimeStrategy,
    "lambda": LambdaStrategy,
}
COND_STRATEGIES = {
    "random": RandomConditionalStrategy,
}
LOOP_STRATEGIES = {
    "plain": PlainStrategy,
    "collatz": CollatzStrategy,
}
NUMBER_STRATEGIES = {
    "feistel": FeistelNumberStrategy,
    "simple_feistel": SimpleFeistelNumberStrategy,
    "xor_string": XorStringNumberStrategy,
}

# ---- request/response models ----
class ObfuscationConfig(BaseModel):
    input_path: Path = Field(..., description="Path to the input .py file")
    output_path: Optional[Path] = Field(
        None, description="Optional path to write the transformed code"
    )

    # strategy toggles
    enable_junk: bool = True
    enable_loops: bool = True
    enable_conditionals: bool = True
    enable_identities: bool = True
    enable_numbers: bool = True
    enable_renaming: bool = True

    # selections / knobs
    junk_strategies: List[Literal["arithmetic", "bitwise", "non_constant_time", "lambda"]] = [
        "bitwise",
        "non_constant_time",
        "arithmetic",
    ]
    junk_density: int = 2

    loop_strategy: Literal["plain", "collatz"] = "collatz"
    conditional_strategies: List[Literal["random"]] = ["random"]
    identity_probability: float = 0.2
    number_strategies: List[Literal["feistel", "xor_string", "simple_feistel"]] = [
        "feistel",
        "xor_string",
    ]

    # output options
    return_code: bool = True  # include transformed code in response body

    # reproducibility
    seed: Optional[int] = Field(None, description="Seed for deterministic output")

class ObfuscationResult(BaseModel):
    output_path: Optional[Path] = None
    code: Optional[str] = None

# ------------------------------------------------------------------------------
# Core pipeline
# ------------------------------------------------------------------------------
def run_pipeline(cfg: ObfuscationConfig) -> str:
    if not cfg.input_path.exists():
        raise FileNotFoundError(f"Input file not found: {cfg.input_path}")

    with _PIPELINE_LOCK:
        with seeded(cfg.seed):
            code = cfg.input_path.read_text(encoding="utf-8")
            tree = ast.parse(code, mode="exec")

            naming = Naming()
            naming.analyze(tree)

            # Junk
            if cfg.enable_junk and cfg.junk_strategies:
                selected = [JUNK_STRATEGIES[k] for k in cfg.junk_strategies]
                tree = JunkInjector(naming, selected, cfg.junk_density).apply(tree)

            # Loops
            if cfg.enable_loops:
                loop_cls = LOOP_STRATEGIES[cfg.loop_strategy]
                tree = Ob_For(naming, loop_cls).apply(tree)

            # Conditionals
            if cfg.enable_conditionals and cfg.conditional_strategies:
                cond_selected = [COND_STRATEGIES[k] for k in cfg.conditional_strategies]
                tree = ConditionalInjector(naming, cond_selected, 1).apply(tree)

            # Identities
            if cfg.enable_identities:
                tree = IdentityFuncInjector(MixedIdentityStrategy(), cfg.identity_probability).apply(tree)

            # Numbers (can apply multiple)
            if cfg.enable_numbers and cfg.number_strategies:
                for ns in cfg.number_strategies:
                    tree = NumberObscurerInjector(naming, NUMBER_STRATEGIES[ns]).apply(tree)

            # Renaming last
            if cfg.enable_renaming:
                tree = Renamer(naming.get_namespace()).apply(tree)

            tree = ast.fix_missing_locations(tree)
            return ast.unparse(tree)

# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
@app.post("/obfuscate", response_model=ObfuscationResult)
def obfuscate(cfg: ObfuscationConfig):
    try:
        transformed = run_pipeline(cfg)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # In production, sanitize this message.
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    result = ObfuscationResult()
    if cfg.output_path:
        cfg.output_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.output_path.write_text(transformed, encoding="utf-8")
        result.output_path = cfg.output_path

    if cfg.return_code or not cfg.output_path:
        result.code = transformed

    return result
