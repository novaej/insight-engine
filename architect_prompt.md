# Architect Prompt for InsightEngine MVP

You are an expert software architect. Your task is to design a backend MVP for a personal investment analysis system. 

- Backend/Core name: InsightEngine 
- Frontend/App future product name: Vestio 

Use the following documents as reference guides to ensure all design decisions are consistent, legally safe, and aligned with the business rules: 

1. `business_rules.md` – Contains all business rules: how to classify assets, assess risk, determine horizon, final state, and propose alternatives. 
2. `domain_language.md` – Contains terminology, definitions, and user-facing language for describing states, risks, and scenarios. 
3. `ARCHITECTURE.md` – Code-path walkthrough of the layers, the analyze pipeline, monitoring, and the data model. 

---

## Requirements

1. **Design a scalable and clean backend architecture** using Python + FastAPI. 
2. Clearly **differentiate between what is code (technical implementation)** and **what is business definition (rules, thresholds, classification criteria)**. 
3. Design Pydantic schemas for input and output. 
4. Define endpoints for assets, portfolio summary, risks, and alternative suggestions. 
5. Implement the analysis engine structure with layers: 
  - Metrics/Calculations (technical) 
  - Business rules (deterministic, non-AI, business logic) 
  - Interpretation layer (AI/LLM) that only explains and contextualizes results; does NOT give buy/sell commands. 
6. All outputs should be explainable, legally safe, and user-friendly. 

---

## Naming Conventions for Folders and Files

- **Root repo:** `insight-engine` 
- **Backend package:** `insight_engine/` 
- **API routes:** `api/` 
- **Domain models:** `domain/` 
- **Business rules:** `rules/` 
- **AI/LLM prompts & handlers:** `ai/` 
- **Jobs and scheduled tasks:** `jobs/` 
- **Tests:** `tests/` 

**File naming:** 

- Python modules: lowercase with underscores, e.g., `portfolio_analysis.py` 
- Pydantic schemas: `schemas.py` or grouped by domain, e.g., `asset_schemas.py` 
- Rules: `valuation_rules.py`, `trend_rules.py` 
- AI prompts: `prompts.py` or `asset_prompts.py` 

---

## Input Model Example (for reference in code design)

```json
{
 "user_profile": {
   "risk": "moderate",
   "horizon": "long_term",
   "goal": "growth"
 },
 "portfolio": [
   { "ticker": "AAPL", "quantity": 15, "type": "stock" },
   { "ticker": "VUSA", "quantity": 20, "type": "etf" },
   { "ticker": "MSFT", "quantity": 5, "type": "stock" }
 ]
}

# Deliverables and Considerations for InsightEngine MVP

All endpoints and outputs must align with the logic defined in the `.md` files. AI/LLM outputs should summarize, explain, and contextualize asset states, scenarios, risks, and alternatives in plain language without ever giving direct buy/sell advice.

---

## Deliverables Expected from This Prompt

- Folder and file structure following naming conventions
- Endpoints and Pydantic schemas
- Analysis engine design (metrics + rules + AI interpretation layer)
- Clear separation between technical code and business rules
- Example outputs for one asset and one portfolio summary

---

## Considerations for Development

- Use a **virtual environment** (venv or similar) so nothing is installed globally; all dependencies must be project-local.
- **Unit tests are mandatory** for all possible functionality, especially for metrics, rules, and endpoints.
- Create `.md` documentation files that explain everything necessary to run the project locally (setup, environment, dependencies, usage, and example API calls).
