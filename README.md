# 🤖 Self-Reflecting Autonomous AI Document Agent

A production-ready Python API containing an **Autonomous AI Agent** that parses natural language requests, plans its own workflow, gathers context, drafts structured reports, self-evaluates document quality, and compiles polished Microsoft Word (`.docx`) files. 

Built from scratch using **FastAPI**, **Groq (Llama 3.3 70B)**, and **python-docx**.

---

## 🗺️ System Architecture & Workflow

```
                   ┌───────────────────────────────────────┐
                   │          User Input Request           │
                   └──────────────────┬────────────────────┘
                                      │
                                      ▼
                   ┌───────────────────────────────────────┐
                   │             Task Planner              │ ◀───┐
                   │   Decomposes request into sub-tasks   │     │
                   └──────────────────┬────────────────────┘     │
                                      │                          │
                                      ▼                          │
                   ┌───────────────────────────────────────┐     │
                   │           Executor Engine             │     │
                   │   Iterates and dispatches to tools    │     │
                   └──────────────────┬────────────────────┘     │
                                      │                          │
                                      ▼                          │
                   ┌───────────────────────────────────────┐     │ (Quality score < 70)
                   │        Self-Reflection Engine         │ ────┘
                   │    Critiques & scores text (0-100)    │  Triggers auto-re-write
                   └──────────────────┬────────────────────┘
                                      │
                                      ▼ (Passes Quality Gate)
                   ┌───────────────────────────────────────┐
                   │           DOCX Generator              │
                   │      Applies professional styles      │
                   └──────────────────┬────────────────────┘
                                      │
                                      ▼
                   ┌───────────────────────────────────────┐
                   │   FastAPI Response & File Download    │
                   └───────────────────────────────────────┘
```

### Component Overview

| Component | File Path | Responsibility |
|:---|:---|:---|
| **API Layer** | `app/main.py` | Exposes `POST /agent` and handles file serving. |
| **Planner** | `app/agent/planner.py` | Parses user requests, resolves ambiguities (makes assumptions), and designs task paths. |
| **Executor** | `app/agent/executor.py` | Loops through tasks sequentially, preserving memory across steps. |
| **Reflector** | `app/agent/reflector.py` | Quality assurance check (criticizes and repairs weak sections). |
| **Tools** | `app/agent/tools.py` | Specialized agents for research, outlines, writing, and proofreading. |
| **Doc Generator**| `app/docgen/word_generator.py` | Assembles document styling, custom colors, page numbers, and tables. |
| **LLM Client** | `app/llm/gemini_client.py` | Drop-in async wrapper with exponential backoff and rate-limit recovery. |

---

## 🛠️ Mandatory Engineering Improvement: Multi-Step Planning + Reflection

Instead of one-shot generation, this agent implements a **double-loop optimization system**:

1. **Multi-Step Task Planning:** The agent maps out a custom execution plan depending on the request (research, outlining, custom sections writing, final review).
2. **Self-Reflection (Quality Gate):** Once the document is drafted, a separate verification LLM acts as an editor. It reviews the work against the user's initial prompt and scores it from `0` to `100`.
   - **Quality Score >= 70:** Document passes straight to compilation.
   - **Quality Score < 70:** The Reflector flags specific weak sections and issues. The agent loops back to rewrite/patch those sections using the writer tools (capped at 1 retry to avoid infinite API consumption).

*Why this matters:* This loop guarantees high-quality, coherent results even for extremely ambiguous inputs (which was proven during manual test validations).

---

## ⚡ Setup & Installation

### 1. Clone & Set Up Directory
Ensure you are in the project root folder.

### 2. Configure Virtual Environment
```bash
# Create environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a `.env` file in the root directory:
```env
# Get a free API Key at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## 🚀 Running & Verification

### Start the Server
```bash
uvicorn app.main:app --reload
```
Once started, the API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Run Test Inputs
We have included a comprehensive test script that runs both the standard and complex test scenarios:
```bash
python test_agent.py
```

---

## 📊 Test Cases Implemented

### 🔹 Test Case 1: Standard Business Request
* **Query:** `"Create a project proposal for a mobile app that helps users track their daily water intake. The app should include reminders, progress tracking, and health insights."`
* **Output:** Generates a structured Project Proposal document complete with mock market analytics, app features table, technical requirements, and financial forecasts.

### 🔹 Test Case 2: Complex / Vague Request
* **Query:** `"We had a meeting yesterday about Q3 strategy. Some people wanted to expand into Europe, others preferred focusing on the US market. Budget is tight but we also need to hire. The CEO mentioned something about AI integration but wasn't specific. Put together something useful from this."`
* **Output:** Autonomously classified as a **Business Report**. The agent documented 4 critical assumptions made to fill in details, structured strategic comparison options, budget considerations, and generated Q3 strategic recommendations.

---

## 📄 Sample Outputs

The repository tracks generated documents from our two standard evaluation runs inside the `outputs/` folder. You can download and inspect them directly:
* **Test Case 1 (Standard):** [Project Proposal Document](outputs/Project_Proposal_Mobile_App_for_Daily_Water_Intake_20260704_135246.docx)
* **Test Case 2 (Complex/Ambiguous):** [Q3 Strategic Report Document](outputs/Q3_Strategy_Business_Report_20260704_135620.docx)

---

## 🎨 Professional Document Designs
Our generated `.docx` files are not just plain text. The `word_generator.py` compiler formats them professionally:
* **Custom Color Palette:** Uses deep Navy (`#1A3C6E`) for primary headers, Slate Blue (`#3A7CBD`) for subheadings, and dark gray for text.
* **Cover Page:** Creates clean Title pages with sub-labels, dividers, and generation timestamps.
* **Layouts & Elements:** Properly compiles markdown-style bullet points, numbering systems, and injects clean bordered tables for data-dense sections.
* **Footers:** Dynamic page numbering fields built natively into the document footer using OpenXML fields.

---

## 💡 Key Design Decisions & Tradeoffs

1. **Custom Agent Orchestration (vs. LangChain/CrewAI):** Built without heavy multi-agent frameworks. This keeps latency low, dependency footprints minimal, and allows granular control over the execution context and retry loops.
2. **Robust Rate-Limit Recovery:** Configured the LLM client to parse Groq's `retry-after` header during API rate-limits (`429`), sleeping dynamically rather than raising immediate exceptions.
3. **Structured API Outputs:** Every task step, status, assumption, and reflection metric is exposed in the JSON response, ensuring total visibility into the agent's decision-making process.
