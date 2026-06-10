# app.py
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from Injectors.identity_strategies import IdentityFuncStrategy
from Injectors.junk_conditional_strategies import JunkConditionalStrategy
from Injectors.junk_strategies import JunkInjectionStrategy
from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
from Encryption.number_obscure_strategies import NumberObscureStrategy
from Encryption.string_obscure_strategies import StringObscureStrategy
from pipeline import DEFAULT_STAGE_ORDER, ObfuscationConfig, run_pipeline
from Utils.input_guard import validate_input

_BASE = Path(__file__).parent

# Files shipped to Pyodide's virtual FS for client-side execution
_PACKAGE_FILES = [
    "pipeline.py",
    "Encryption/__init__.py",
    "Encryption/number_obscure_strategies.py",
    "Encryption/number_obscurer.py",
    "Encryption/string_obscure_strategies.py",
    "Encryption/string_obscurer.py",
    "Injectors/__init__.py",
    "Injectors/conditional_injector.py",
    "Injectors/identity_injector.py",
    "Injectors/identity_strategies.py",
    "Injectors/inject_junk.py",
    "Injectors/junk_conditional_strategies.py",
    "Injectors/junk_strategies.py",
    "LoopObfuscation/__init__.py",
    "LoopObfuscation/collatz_seed.py",
    "LoopObfuscation/for_to_while_generic.py",
    "LoopObfuscation/loop_simplifier.py",
    "LoopObfuscation/ob_for.py",
    "LoopObfuscation/obfuscation_strategies.py",
    "NameTracker/__init__.py",
    "NameTracker/naming.py",
    "Renaming/__init__.py",
    "Renaming/renamer.py",
    "Utils/__init__.py",
]

app = FastAPI(title="Obfuscator API", version="1.0.0")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/frontend/index.html")


def _package_files() -> dict:
    return {rel: (_BASE / rel).read_text(encoding="utf-8") if (_BASE / rel).exists() else ""
            for rel in _PACKAGE_FILES}

@app.get("/package", include_in_schema=False)
def get_package():
    return _package_files()

@app.get("/package.json", include_in_schema=False)
def get_package_json():
    return _package_files()


# Pydantic request/response models (API layer only)
class ObfuscationRequest(BaseModel):
    input_path: Path = Field(..., description="Path to the input .py file")
    output_path: Optional[Path] = Field(None, description="Optional path to write the transformed code")

    enable_junk: bool = True
    enable_loops: bool = True
    enable_conditionals: bool = True
    enable_identities: bool = True
    enable_numbers: bool = True
    enable_renaming: bool = True

    junk_strategies: List[str] = ["BitwiseStrategy", "NonConstantTimeStrategy", "ArithmeticStrategy"]
    junk_density: int = 2
    loop_strategy: str = "CollatzStrategy"
    conditional_strategies: List[str] = ["RandomConditionalStrategy"]
    identity_probability: float = 0.2
    number_strategies: List[str] = ["FeistelNumberStrategy", "XorStringNumberStrategy"]
    enable_strings: bool = True
    string_strategies: List[str] = ["XorStringStrategy", "CharArrayStrategy"]

    stage_order: Optional[List[str]] = Field(
        None,
        description="Ordered stage names to run. Valid: " + ", ".join(DEFAULT_STAGE_ORDER),
    )

    phase_configs: Optional[List[dict]] = Field(
        None,
        description="Ordered list of {type, config} dicts. When set, replaces flat per-phase fields.",
    )

    return_code: bool = True
    seed: Optional[int] = Field(None, description="Seed for deterministic output")


class ObfuscationResponse(BaseModel):
    output_path: Optional[Path] = None
    code: Optional[str] = None


@app.get("/strategies")
def get_strategies():
    return {
        "junk": sorted(JunkInjectionStrategy._registry),
        "conditional": sorted(JunkConditionalStrategy._registry),
        "loop": sorted(LoopObfuscationStrategy._registry),
        "identity": sorted(IdentityFuncStrategy._registry),
        "number": sorted(NumberObscureStrategy._registry),
        "string": sorted(StringObscureStrategy._registry),
    }


@app.post("/obfuscate", response_model=ObfuscationResponse)
def obfuscate(req: ObfuscationRequest):
    try:
        source = Path(req.input_path).read_text(encoding="utf-8")
        validate_input(source)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    cfg = ObfuscationConfig(**req.model_dump())
    try:
        transformed = run_pipeline(cfg)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    result = ObfuscationResponse()
    if cfg.output_path:
        Path(cfg.output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cfg.output_path).write_text(transformed, encoding="utf-8")
        result.output_path = cfg.output_path

    if req.return_code or not cfg.output_path:
        result.code = transformed

    return result


# Serve frontend last so API routes take precedence
_FRONTEND_DIR = _BASE / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=_FRONTEND_DIR), name="frontend")
