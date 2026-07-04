**Python AI Engineer – Autonomous Agents** 

**Task**

Build a simple autonomous AI agent that can understand a user request, create its own task or TODO list, execute the required steps, and produce a polished Microsoft Word (.docx) document as the final output. You may use any tools, frameworks, or models, but your solution must demonstrate autonomous planning, decision-making, and end-to-end execution.

**Requirements**

Build a Python API (FastAPI preferred) with POST /agent accepting JSON {"request":"..."}. The system should accept a natural language request, determine the tasks required to complete it, generate its own execution plan, execute each step, and return a meaningful response along with the generated Word document. The document may be a proposal, meeting minutes, project plan, business report, technical design, SOP, product specification, or similar structured business document. Use of mock data is allowed where appropriate.

Use a free or locally runnable LLM such as Groq, Gemini (free tier), Grok (free tier), Ollama, LM Studio, or another open-source model so the assignment can be completed without purchasing API credits.

**One Real Engineering Improvement (Mandatory)**

Implement **ONE** of the following: Conversation memory, Simple RAG, Tool calling, Multi-step planning, Error handling & recovery, Request validation & guardrails, Reflection/self-check, or Retry & fallback logic. Explain what you implemented, why you chose it, and how it improves the agent.

**Two Test Inputs**

Demonstrate one standard business request and one complex request (ambiguous, multi-step, missing information, conflicting requirements, or requiring the agent to decide its own execution plan and make reasonable assumptions).

**Rules**

Do **NOT** use a fully managed no-code AI platform. You may use OpenAI, Claude, Gemini, Groq, Grok, Ollama, LangChain, LangGraph, CrewAI, MCP, FastAPI, AsyncIO, Flask, or similar tools. Mock data is allowed. Focus on autonomous agent design, engineering decisions, and code quality rather than UI or external system integrations.

**Evaluation Criteria**

* Python code quality  
* Software engineering fundamentals  
* Autonomous agent design  
* Task planning and reasoning  
* Tool orchestration  
* API design  
* Problem-solving approach  
* Debugging ability  
* Scalability and architecture thinking  
* Ability to explain technical decisions

