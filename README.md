# Power-dev Tiered Agent Deployment

This directory contains a "Power-dev" deployment pattern for the `story-engine` agent. It uses a single codebase to run two runtime profiles with an intelligent router for escalation.

## Architecture

1.  **Codebase**: `story-engine` (FastAPI wrapper in `scripts/agent_server.py`).
2.  **Tier 1 (Cheap)**: Optimized for speed and low cost (e.g., Gemma 2 9B). It uses the fast stage of the `HPQPipeline` and returns a quality score.
3.  **Tier 2 (Heavy)**: Optimized for quality (e.g., Llama 3.1 70B). It performs high-quality "line editing" and refinement.
4.  **Router**: A policy-driven front door that calls Tier 1 first and conditionally escalates to Tier 2 if the quality score is below **7.5**.

## How to Run

### Prerequisites
- Docker & Docker Compose
- An AI endpoint (e.g., `ai-lb` or direct LLM server) accessible at `${LM_ENDPOINT}`.

### Startup
```bash
# In story-engine/deploy/power-dev/
docker-compose up -d
```

### Usage
Submit a generation request to the router on port `8080`:

```bash
curl -X POST http://localhost:8080/generate 
  -H "Content-Type: application/json" 
  -d '{
    "beat": {"name": "The Confrontation", "purpose": "Tension rises between Pilate and Caiaphas", "tension": 0.8},
    "characters": [
      {"name": "Pontius Pilate", "role": "Prefect"},
      {"name": "Caiaphas", "role": "High Priest"}
    ]
  }'
```

The router will return a JSON response containing:
- `final`: The generated scene text (from cheap or heavy tier).
- `best_avg`: The quality score from the cheap tier.
- `escalated`: Boolean indicating if the heavy tier was called.
- `refinement_model`: The model used for refinement if escalated.

## Benefits
- **Cost Savings**: Fast, cheap models handle high-confidence tasks (scores >= 7.5).
- **Quality Assurance**: Complex or low-quality generations are automatically refined by powerful models.
- **Unified Logic**: One shared codebase for all tiers, differing only by environment variables.
