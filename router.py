from __future__ import annotations

import os
import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("power-dev-router")

app = FastAPI(title="Power-dev Intelligent Router")

CHEAP_URL = os.getenv("CHEAP_URL", "http://agent-cheap:8000")
HEAVY_URL = os.getenv("HEAVY_URL", "http://agent-heavy:8000")
THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", "7.5"))

class GenerateRequest(BaseModel):
    beat: Dict[str, Any]
    characters: List[Dict[str, Any]]
    previous_context: str = ""

@app.get("/health")
async def health():
    return {"status": "ok", "router": True}

@app.post("/generate")
async def route_generate(req: GenerateRequest):
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Try cheap first
        logger.info(f"Routing to cheap agent: {CHEAP_URL}")
        try:
            resp = await client.post(f"{CHEAP_URL}/generate", json=req.model_dump())
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.error(f"Cheap agent failed: {e}. Escalating to heavy by default.")
            # Fallback directly to heavy if cheap is down
            return await call_heavy_full(client, req)

        score = result.get("best_avg", 0.0)
        logger.info(f"Cheap agent result score: {score}")

        # 2. Check threshold for escalation
        if score < THRESHOLD:
            logger.info(f"Score {score} < {THRESHOLD}. Escalating to heavy tier.")
            # Escalate: Pass the best cheap candidate to heavy for refinement
            refine_payload = {
                "text": result.get("final", ""),
                "model": os.getenv("LM_HQ_MODEL")
            }
            try:
                refine_resp = await client.post(f"{HEAVY_URL}/refine", json=refine_payload)
                refine_resp.raise_for_status()
                heavy_result = refine_resp.json()
                
                # Merge results
                result["final"] = heavy_result.get("final")
                result["escalated"] = True
                result["refinement_model"] = heavy_result.get("model_hq")
                return result
            except Exception as e:
                logger.error(f"Heavy refinement failed: {e}. Returning cheap result.")
                result["escalation_error"] = str(e)
                return result
        
        # 3. Score is good enough, return cheap result
        result["escalated"] = False
        return result

async def call_heavy_full(client, req):
    """Fallback to full heavy generation if cheap fails."""
    logger.info(f"Routing full generation to heavy agent: {HEAVY_URL}")
    try:
        resp = await client.post(f"{HEAVY_URL}/generate", json=req.model_dump())
        resp.raise_for_status()
        result = resp.json()
        result["escalated"] = True
        result["fallback_full_heavy"] = True
        return result
    except Exception as e:
        logger.error(f"Heavy agent also failed: {e}")
        raise HTTPException(status_code=502, detail=f"All agent tiers failed: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
