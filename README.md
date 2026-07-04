# Autonomous AI Agent

A Python-based autonomous AI agent that accepts natural-language requests, creates its own execution plan, runs each step via tool-calling, self-evaluates the output, and produces polished Microsoft Word (`.docx`) documents.

## Architecture

```
User Request  →  Planner  →  Executor  →  Reflector  →  DOCX Generator
                   │            │             │
                   ▼            ▼             ▼
              Task List    Tool Calls    Quality Check
              (LLM)       (LLM+Tools)   (LLM Review)
```

### Component Overview

| Component      | File                           | Purpose                                                       |
| -------------- | ------------------------------ | ------------------------------------------------------------- |
| **API Layer**  | `app/main.py`                  | FastAPI app with `POST /agent` and `GET /download/{filename}` |
| **Planner**    | `app/agent/planner.py`         | Decomposes requests into task lists using LLM                 |
| **Executor**   | `app/agent/executor.py`        | Walks through tasks, calling tools sequentially               |
| **Tools**      | `app/agent/tools.py`           | Research, outline, write, and review tools                    |
| **Reflector**  | `app/agent/reflector.py`       | Self-check that evaluates and improves output                 |
| **DOCX Gen**   | `app/docgen/word_generator.py` | Professional Word document creation                           |
| **LLM Client** | `app/llm/gemini_client.py`     | Groq (Llama 3.3 70B) API wrapper with retry logic             |
| **Models**     | `app/models/schemas.py`        | Pydantic request/response schemas                             |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Copy the example environment file and add your Groq API key:

```bash
cp .env.example .env
# Edit .env and add your key:
# GROQ_API_KEY=your_key_here
```

Get a free API key at: https://console.groq.com

### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 4. Test the Agent

```bash
python test_agent.py
```

Or use curl:

```bash
curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a project proposal for a mobile water tracking app"}'
```

## Engineering Improvement: Multi-Step Planning with Self-Reflection

### What I Implemented

A two-phase quality system:

1. **Multi-step planning** — The agent uses the LLM to decompose any request into a structured task list (research → outline → write sections → review), then executes each step sequentially with context accumulation.
2. **Self-reflection** — After execution, a separate LLM call evaluates the complete document against the original request, scoring it on completeness, coherence, and quality. If the score falls below 70/100, weak sections are automatically re-written (max 1 retry to prevent infinite loops).

### Why I Chose It

Multi-step planning combined with reflection is the most impactful improvement for an autonomous agent because:

- **Planning** demonstrates the agent's ability to reason about _what_ needs to be done, not just _how_ — the core of autonomy.
- **Reflection** adds a crucial feedback loop. Without it, the agent is a one-shot generator. With it, the agent can self-correct, which is essential for handling complex or ambiguous requests.
- Together, they cover two of the listed improvements (multi-step planning + reflection/self-check) while being tightly integrated.

### How It Improves the Agent

1. **Better handling of ambiguity** — The planner explicitly identifies assumptions and documents them in the response.
2. **Higher quality output** — The reflection phase catches missing content, inconsistent tone, and logical gaps.
3. **Transparency** — The full task plan and reflection results are returned to the user, making the agent's reasoning visible.
4. **Robustness** — Error handling at every step means a single failure doesn't crash the entire pipeline.

## API Reference

### `POST /agent`

**Request:**

```json
{
  "request": "Create a project proposal for a mobile water tracking app"
}
```

**Response:**

```json
{
  "request_id": "a1b2c3d4e5f6",
  "original_request": "...",
  "document_type": "Project Proposal",
  "assumptions": ["Assumed target platform is iOS and Android", "..."],
  "task_plan": [
    {
      "step_number": 1,
      "action": "research",
      "description": "...",
      "status": "completed"
    },
    {
      "step_number": 2,
      "action": "outline",
      "description": "...",
      "status": "completed"
    }
  ],
  "reflection": {
    "passed": true,
    "score": 85,
    "issues": [],
    "improvements_made": []
  },
  "filename": "Water_Tracking_App_Proposal_20250704.docx",
  "download_url": "/download/Water_Tracking_App_Proposal_20250704.docx",
  "message": "Document generated successfully with 6 sections."
}
```

### `GET /download/{filename}`

Downloads the generated `.docx` file.

### `GET /health`

Returns `{"status": "healthy"}`.

## Test Inputs

### Test 1 — Standard Business Request

> "Create a project proposal for a mobile app that helps users track their daily water intake. The app should include reminders, progress tracking, and health insights."

Expected: A well-structured project proposal with clear sections.

### Test 2 — Complex / Ambiguous Request

> "We had a meeting yesterday about Q3 strategy. Some people wanted to expand into Europe, others preferred focusing on the US market. Budget is tight but we also need to hire. The CEO mentioned something about AI integration but wasn't specific. Put together something useful from this."

Expected: The agent should identify this as meeting minutes or a strategy memo, make assumptions about the missing context, and produce a coherent document that addresses the conflicting viewpoints.

## 📄 Sample Outputs

The repository tracks generated documents from our two standard evaluation runs inside the `outputs/` folder. You can download and inspect them directly:
* **Test Case 1 (Standard):** [Project Proposal Document](outputs/Project_Proposal_Mobile_App_for_Daily_Water_Intake_20260704_135246.docx)
* **Test Case 2 (Complex/Ambiguous):** [Q3 Strategic Report Document](outputs/Q3_Strategy_Business_Report_20260704_135620.docx)

## Design Decisions

1. **No LangChain/CrewAI** — Built a custom agent loop to demonstrate understanding of agent architecture rather than relying on framework abstractions.
2. **Groq (Llama 3.3 70B)** — Free tier, extremely fast inference, high quality reasoning, and the assignment allows it.
3. **Async-first** — All LLM calls use async `httpx` to keep the FastAPI event loop responsive.
4. **Graceful degradation** — If any single step fails, the executor continues with remaining steps rather than aborting.
5. **Structured responses** — The full task plan, assumptions, and reflection are returned so the consumer can see _how_ the agent reasoned, not just the final output.
