# Power-dev Framework

A reference implementation of the "Power-dev Pattern" for AI agents. This pattern enables multi-tier agent deployments with intelligent escalation to balance cost, latency, and quality.

## Repository Contents

- `agent_server.py`: A FastAPI wrapper for agent logic, supporting standard generation and high-quality refinement endpoints.
- `router.py`: An intelligent router that dispatches tasks to a "cheap" tier and escalates to a "heavy" tier based on real-time quality scores.
- `docker-compose.yml`: A deployment configuration for running tiered agent profiles from a single codebase.
- `power-dev-orchestrator.skill`: A Gemini CLI skill package that automates the architecting of this pattern in other projects.

## Architecture

1. **Cheap Tier**: Optimized for speed/cost. Handles default traffic.
2. **Heavy Tier**: Optimized for quality. Handles low-confidence tasks escalated by the router.
3. **Power Move**: Instead of regenerating from scratch, the Heavy tier "refines" the output of the Cheap tier to save tokens and maintain context.

## Documentation

See [README.md](README.md) (copied from the deployment demo) for detailed usage instructions.
