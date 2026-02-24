from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from story_engine.core.core.story_engine.hpq_pipeline import HPQPipeline, HPQOptions
from story_engine.core.core.orchestration.unified_llm_orchestrator import UnifiedLLMOrchestrator

app = FastAPI(title="Story Engine Agent Server")

# Global pipeline instance initialized with env vars
_pipeline: Optional[HPQPipeline] = None

class GenerateRequest(BaseModel):
    beat: Dict[str, Any]
    characters: List[Dict[str, Any]]
    previous_context: str = ""
    candidates: Optional[int] = None
    threshold: Optional[float] = None

class RefineRequest(BaseModel):
    text: str
    model: Optional[str] = None

def get_pipeline() -> HPQPipeline:
    global _pipeline
    if _pipeline is None:
        opts = HPQOptions(
            candidates=int(os.getenv("HPQ_CANDIDATES", "3")),
            threshold_avg=float(os.getenv("HPQ_THRESHOLD_LOW", "7.5")),
            threshold_high=float(os.getenv("HPQ_THRESHOLD_HIGH", "8.3")),
            max_tokens_fast=int(os.getenv("MAX_TOKENS_FAST", "600")),
            max_tokens_hq=int(os.getenv("MAX_TOKENS_HQ", "800")),
            temperature_fast=float(os.getenv("TEMP_FAST", "0.7")),
            temperature_hq=float(os.getenv("TEMP_HQ", "0.6")),
            canary_pct=float(os.getenv("CANARY_PCT", "0.0")),
        )
        _pipeline = HPQPipeline(opts=opts)
    return _pipeline

@app.get("/health")
async def health():
    return {"status": "ok", "profile": os.getenv("AGENT_PROFILE", "default")}

@app.post("/generate")
async def generate(req: GenerateRequest):
    pipeline = get_pipeline()
    # Temporarily override options if requested
    original_opts = pipeline.opts
    if req.candidates is not None or req.threshold is not None:
        pipeline.opts = HPQOptions(
            **{**original_opts.__dict__, 
               "candidates": req.candidates if req.candidates is not None else original_opts.candidates,
               "threshold_avg": req.threshold if req.threshold is not None else original_opts.threshold_avg}
        )
    
    try:
        result = await pipeline.craft_scene_hpq(
            req.beat, req.characters, req.previous_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pipeline.opts = original_opts

@app.post("/refine")
async def refine(req: RefineRequest):
    pipeline = get_pipeline()
    model = req.model or await pipeline._select_hq_model()
    
    if not req.text:
        raise HTTPException(status_code=400, detail="No text provided for refinement")
    
    try:
        refined = await pipeline._finalize_hq(req.text, model=model)
        return {"final": refined, "model_hq": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
