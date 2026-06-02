# app.py
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from Injectors.identity_strategies import IdentityFuncStrategy
from Injectors.junk_conditional_strategies import JunkConditionalStrategy
from Injectors.junk_strategies import JunkInjectionStrategy
from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
from Encryption.number_obscure_strategies import NumberObscureStrategy
from pipeline import DEFAULT_STAGE_ORDER, ObfuscationConfig, run_pipeline

app = FastAPI(title="Obfuscator API", version="1.0.0")


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

    stage_order: Optional[List[str]] = Field(
        None,
        description="Ordered stage names to run. Valid: " + ", ".join(DEFAULT_STAGE_ORDER),
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
    }


@app.post("/obfuscate", response_model=ObfuscationResponse)
def obfuscate(req: ObfuscationRequest):
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
