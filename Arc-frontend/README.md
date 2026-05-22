# Azure AI Architecture Diagram Generator

## Overview

A production-grade, multi-agent AI system that generates, validates, and optimizes Azure cloud architecture diagrams from natural language requirements. Built with a Next.js/React frontend and an 8-agent Python backend orchestrated via LangGraph state machines.

**Core Capabilities:**
- Generate complete Azure architectures from free-text requirements
- 8 specialized AI agents with inter-agent communication
- Multi-format export: Draw.io XML, Mermaid, Terraform
- Reverse engineer from Visio, Draw.io, images (GPT-4o Vision), and Terraform
- Well-Architected Framework (WAF) compliance scoring
- Human-in-the-loop checkpoints and iterative refinement
- Knowledge base with reinforcement learning

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js / React)                          │
│                                                                                 │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ Generate Tab │  │ Reverse Engineer │  │ Validate   │  │ Session History   │  │
│  │             │  │      Tab         │  │    Tab     │  │       Tab         │  │
│  └──────┬──────┘  └────────┬─────────┘  └─────┬──────┘  └─────────┬─────────┘  │
│         │                  │                   │                   │             │
│  ┌──────┴──────────────────┴───────────────────┴───────────────────┴──────────┐  │
│  │                    API Layer (fetch → Backend REST API)                     │  │
│  └────────────────────────────────────┬───────────────────────────────────────┘  │
└───────────────────────────────────────┼──────────────────────────────────────────┘
                                        │ HTTP/SSE
┌───────────────────────────────────────┼──────────────────────────────────────────┐
│                         BACKEND (Python / Flask)                                  │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         API Router (app.py)                                  │ │
│  │  /api/generate  /api/validate  /api/reverse-engineer  /api/chat  /api/...   │ │
│  └──────────────────────────────┬──────────────────────────────────────────────┘ │
│                                 │                                                │
│  ┌──────────────────────────────┼──────────────────────────────────────────────┐ │
│  │              WORKFLOW ORCHESTRATION (LangGraph / Pipeline)                    │ │
│  │                                                                              │ │
│  │   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐                   │ │
│  │   │ LangGraph   │    │ Multi-Agent  │    │   Agent      │                   │ │
│  │   │ StateGraph  │    │  Pipeline    │    │ Orchestrator │                   │ │
│  │   │ (primary)   │    │ (fallback)   │    │  (parallel)  │                   │ │
│  │   └──────┬──────┘    └──────┬───────┘    └──────┬───────┘                   │ │
│  │          └──────────────────┼────────────────────┘                           │ │
│  └─────────────────────────────┼────────────────────────────────────────────────┘ │
│                                │                                                  │
│  ┌─────────────────────────────┼────────────────────────────────────────────────┐ │
│  │                     8 SPECIALIZED AI AGENTS                                   │ │
│  │                                                                               │ │
│  │  ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐            │ │
│  │  │ 0. Component   │  │ 1. Azure Ref     │  │ 2. Security        │            │ │
│  │  │   Extraction   │──│   Architecture   │──│    Agent           │            │ │
│  │  │   Agent        │  │    Agent         │  │                    │            │ │
│  │  └────────────────┘  └──────────────────┘  └─────────┬──────────┘            │ │
│  │                                                       │                       │ │
│  │  ┌────────────────┐  ┌──────────────────┐  ┌─────────┴──────────┐            │ │
│  │  │ 3. Performance │  │ 4. Architecture  │  │ 5. Connection      │            │ │
│  │  │    Agent       │──│    Agent (CORE)  │──│    Expert Agent    │            │ │
│  │  │                │  │                  │  │                    │            │ │
│  │  └────────────────┘  └──────────────────┘  └─────────┬──────────┘            │ │
│  │                                                       │                       │ │
│  │  ┌────────────────┐  ┌──────────────────┐  ┌─────────┴──────────┐            │ │
│  │  │ Cost Optim.    │  │ 6. Requirements  │  │ 7. Architecture    │            │ │
│  │  │ Agent          │  │   Validation     │──│    Review Agent    │            │ │
│  │  │ (parallel)     │  │    Agent         │  │   (Final Gate)     │            │ │
│  │  └────────────────┘  └──────────────────┘  └────────────────────┘            │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        SUPPORTING SERVICES                                   │   │
│  │                                                                              │   │
│  │  ┌──────────────┐ ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐  │   │
│  │  │ DrawIO XML   │ │ Azure Docs     │ │ Knowledge    │ │ Diagram          │  │   │
│  │  │ Generator    │ │ Scanner/Index  │ │ Base + RL    │ │ Modification     │  │   │
│  │  └──────────────┘ └────────────────┘ └──────────────┘ └──────────────────┘  │   │
│  │  ┌──────────────┐ ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐  │   │
│  │  │ Reverse      │ │ Diff Analyzer  │ │ AI Validator │ │ Icon Generator   │  │   │
│  │  │ Engineer     │ │                │ │              │ │ (Azure SVGs)     │  │   │
│  │  └──────────────┘ └────────────────┘ └──────────────┘ └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                         AZURE OPENAI (GPT-4o)                                 │   │
│  │              AsyncAzureOpenAI client  |  Temperature: 0.1  |  Vision          │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Pipeline (Detailed)

### Sequential Workflow (Primary Path)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         AGENT EXECUTION PIPELINE                               │
│                                                                               │
│  Requirements ──→ [0] Component Extraction                                    │
│                        │ Extracts: APIs, NFRs, tech stack, data needs,       │
│                        │ business rules, integration points, RG hints         │
│                        ▼                                                      │
│                   [1] Azure Reference Architecture                             │
│                        │ Maps to: 100+ proven patterns from Azure Arch Center │
│                        │ Identifies: applicable design patterns               │
│                        ▼                                                      │
│                   [2] Security Agent                                           │
│                        │ Produces: Zero Trust design, identity (Entra ID),    │
│                        │ network (NSG, Firewall, Private Link), data          │
│                        │ protection (Key Vault), compliance frameworks        │
│                        │ (SOC2, HIPAA, GDPR, PCI-DSS), threat detection      │
│                        ▼                                                      │
│                   [3] Performance Agent                                        │
│                        │ Produces: scaling strategy, caching (Redis, CDN),    │
│                        │ CQRS/Event Sourcing, load balancing, DB tuning,     │
│                        │ async patterns                                       │
│                        ▼                                                      │
│                   [4] Architecture Agent ★ CORE                                │
│                        │ Designs: full service topology, categorized services,│
│                        │ containers, connections, resource groups              │
│                        │ Patterns: N-tier, microservices, event-driven,       │
│                        │ serverless, hub-spoke                                │
│                        │ Uses: Few-Shot examples + Knowledge Base             │
│                        ▼                                                      │
│              ┌────[Quality Gate]────┐                                          │
│              │  Score < threshold?  │                                          │
│              │  YES → Retry (max 3) │                                          │
│              │  NO  → Continue      │                                          │
│              └──────────┬───────────┘                                          │
│                        ▼                                                      │
│                   [5] Connection Expert Agent                                  │
│                        │ Validates: layer flow (Users→Edge→Gateway→           │
│                        │ Compute→Data), orphan detection, duplicate removal,  │
│                        │ professional labeling                                 │
│                        ▼                                                      │
│                   [6] Requirements Validation Agent                            │
│                        │ Checks: all original requirements covered,           │
│                        │ gap analysis, remediation actions, multi-RG          │
│                        │ grouping validation                                  │
│                        ▼                                                      │
│                   [7] Architecture Review Agent (Final Gate)                   │
│                        │ Performs: WAF assessment (5 pillars), service         │
│                        │ compatibility matrix, iterative corrections,         │
│                        │ routes fixes back upstream if needed                  │
│                        ▼                                                      │
│                   Draw.io XML Generation                                       │
│                        │ Algorithmic layout → professional diagram             │
│                        ▼                                                      │
│                   Output: XML + Mermaid + Terraform + Scores                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Agentic AI Features

| Feature | Description |
|---------|-------------|
| **Chain-of-Thought** | Each agent emits visible thinking steps for transparency |
| **Inter-Agent Communication** | Shared `message_bus` — agents broadcast insights and warnings to downstream agents |
| **Self-Reflection** | Agents reflect on their own outputs before passing downstream |
| **Tool Usage** | Agents invoke tools: `search_azure_docs`, `validate_architecture`, icon lookup |
| **Agent Personas** | Distinct identities with emoji avatars and thinking styles |
| **Human-in-the-Loop** | Workflow pauses at checkpoints for user approval/rejection/modification |
| **Quality Gates** | `calculate_quality_score()` (0.0–1.0) with auto-retry on low scores |
| **Conditional Routing** | LangGraph routes back to architecture agent if quality < threshold |
| **MemorySaver Checkpointing** | Enables resumable, crash-safe workflows |
| **Reinforcement Learning** | Knowledge base learns from user feedback to improve future outputs |

---

## LangGraph State Machine

```
                 ┌─────────────────────────────────────────────────────┐
                 │              LangGraph StateGraph                    │
                 │                                                     │
  START ────────→│ component_extraction                                │
                 │        │                                            │
                 │        ▼                                            │
                 │ azure_references                                    │
                 │        │                                            │
                 │        ▼                                            │
                 │ security_analysis ──[retry if quality < threshold]  │
                 │        │                                            │
                 │        ▼                                            │
                 │ performance_analysis                                │
                 │        │                                            │
                 │        ▼                                            │
                 │ architecture_design ──[conditional]──┐              │
                 │        │                            │              │
                 │        │ (quality OK)    (quality low → retry)     │
                 │        ▼                            │              │
                 │ connection_optimization ◄────────────┘              │
                 │        │                                            │
                 │        ▼                                            │
                 │ validation                                          │
                 │        │                                            │
                 │        ▼                                            │
                 │ final_review                                        │
                 │        │                                            │
                 └────────┼────────────────────────────────────────────┘
                          ▼
                         END → Response
```

**WorkflowState** (TypedDict): Structured state object passed between nodes with type safety, including requirements, extracted components, security/performance insights, architecture, connections, validation results, and quality scores.

---

## API Endpoints

### Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Generate architecture (LangGraph or standard mode) |
| POST | `/api/generate-stream` | Async generation with SSE progress |
| POST | `/api/multi-agent-workflow` | Full multi-agent pipeline with metadata |
| POST | `/api/clarify` | AI-powered requirements clarification |
| GET | `/api/progress/{session_id}` | Poll generation progress |
| GET | `/api/progress-stream/{session_id}` | SSE real-time progress stream |

### Validation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/validate` | Multi-agent architecture validation |
| POST | `/api/validate/image` | Validate from uploaded image |
| GET | `/api/validation-report/{id}` | Detailed validation report |
| POST | `/api/compare` | Compare two architectures |
| POST | `/api/diff-report` | Diff analysis between versions |

### Reverse Engineering
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reverse-engineer/drawio` | From Draw.io XML |
| POST | `/api/reverse-engineer/visio` | From Visio .vsdx files |
| POST | `/api/reverse-engineer/image` | From PNG/JPG (GPT-4o Vision) |
| POST | `/api/reverse-engineer/terraform` | From Terraform ZIP |
| POST | `/api/reverse-engineer/analyze-story` | Generate architecture story |

### Chat & Interaction
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/message` | Chat interface for diagram interaction |
| POST | `/api/diagram/improve` | AI-powered diagram improvement |
| POST | `/api/interaction/{id}/respond` | Human-in-the-loop response |

### Knowledge Base & Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge/stats` | KB statistics |
| POST | `/api/knowledge/feedback` | Submit feedback (RL learning) |
| POST | `/api/knowledge/search` | Search patterns |
| GET | `/api/sessions` | List sessions |
| POST | `/api/session/{id}/resume` | Resume session |

---

## Data Flow (End-to-End)

```
┌─────────┐     ┌─────────────┐     ┌──────────────────────┐     ┌───────────────┐
│  User   │────→│  Next.js UI │────→│  Python Backend API  │────→│ Azure OpenAI  │
│  Input  │     │  (React)    │     │  (Flask + LangGraph) │     │   GPT-4o      │
└─────────┘     └─────────────┘     └──────────────────────┘     └───────────────┘
                       │                       │
                       │                       ├──→ 8 Agents (sequential pipeline)
                       │                       ├──→ DrawIO XML Generator
                       │                       ├──→ Mermaid Generator
                       │                       ├──→ Terraform Generator
                       │                       ├──→ AI Validator
                       │                       └──→ Knowledge Base
                       │                              │
                       │◄─────────────────────────────┘
                       │         JSON Response:
                       │         - architecture (services, connections)
                       │         - diagrams (XML, Mermaid, Terraform)
                       │         - validation (scores, issues, recommendations)
                       │         - agent metadata (timeline, quality scores)
                       ▼
              ┌─────────────────┐
              │  User sees:     │
              │  • Diagram      │
              │  • Code tabs    │
              │  • WAF scores   │
              │  • Downloads    │
              └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons, Radix UI |
| **Backend** | Python, Flask, AsyncIO |
| **AI/LLM** | Azure OpenAI GPT-4o (text + vision), temperature 0.1 |
| **Orchestration** | LangGraph StateGraph (primary), MultiAgentPipeline (fallback) |
| **Diagram Engine** | Custom Draw.io XML generator, Mermaid, Terraform HCL |
| **Knowledge** | File-based KB with RL feedback loop |
| **File Parsing** | Draw.io XML, Visio .vsdx (python-pptx), Image (GPT-4o Vision) |

---

## Configuration

| Parameter | Value |
|-----------|-------|
| LLM Model | `gpt-4o` via Azure OpenAI |
| Temperature | `0.1` (deterministic) |
| Max Tokens | 3000 (6000 for Architecture Agent) |
| Agent Timeout | Base 60s + 30s per retry |
| Max Retries | 3 |
| Quality Thresholds | Excellent ≥ 90, Good ≥ 70, Acceptable ≥ 50 |
| CORS Origins | localhost:3000, localhost:5173 |

---

## Project Structure

```
Ai-architecture/
├── architecture-diagram-generator/     # Frontend (Next.js)
│   ├── app/                            # Pages, layout, globals.css
│   ├── components/                     # UI components
│   │   ├── generate-tab.tsx            # Main generation interface
│   │   ├── reverse-engineer-tab.tsx    # Reverse engineering UI
│   │   ├── validate-tab.tsx            # Validation interface
│   │   ├── session-history-tab.tsx     # Session management
│   │   ├── ai-agents-progress.tsx      # Live agent progress display
│   │   ├── improvement-chat.tsx        # Iterative refinement chat
│   │   ├── clarifying-questions-dialog.tsx
│   │   ├── DiagramEmbed.tsx            # Draw.io diagram renderer
│   │   └── ui/                         # Shared UI primitives (50+ components)
│   ├── hooks/                          # Custom React hooks
│   ├── lib/                            # Config, utilities
│   └── types/                          # TypeScript type definitions
│
├── architecture-Backend/               # Backend (Python)
│   ├── app.py                          # Flask API router (40+ endpoints)
│   ├── config.py                       # All configuration
│   ├── shared_services.py              # Azure OpenAI client singleton
│   ├── multi_agent_workflow.py         # Sequential pipeline orchestrator
│   ├── langgraph_workflow.py           # LangGraph state machine
│   ├── agents/                         # 8 specialized AI agents
│   │   ├── component_extraction_agent.py
│   │   ├── azure_architecture_reference_agent.py
│   │   ├── security_agent.py
│   │   ├── performance_agent.py
│   │   ├── architecture_agent.py       # ★ Core design agent
│   │   ├── connection_expert_agent.py
│   │   ├── requirements_validation_agent.py
│   │   └── azure_architecture_review_agent.py
│   ├── diagram_modification_agent.py   # Post-gen modifications
│   ├── drawio_parser.py                # XML diagram generation
│   ├── ai_validator.py                 # AI validation scoring
│   ├── reverse_engineer.py             # Multi-source reverse engineering
│   ├── diff_analyzer.py                # Architecture diff analysis
│   ├── azure_docs_scanner.py           # Azure docs indexer
│   ├── accuracy_enhancements.py        # Few-shot + learned patterns
│   └── knowledge_base/                 # Persistent KB with RL
│
└── visiofiles/                         # Sample Visio/DrawIO diagrams
```

---

## Running the Application

```bash
# 1. Start backend
cd architecture-Backend
pip install -r requirements.txt
python app.py                    # Starts Flask on port 5000

# 2. Start frontend
cd architecture-diagram-generator
npm install                      # or pnpm install
npm run dev                      # Starts Next.js on port 3000
```
## License
MIT
