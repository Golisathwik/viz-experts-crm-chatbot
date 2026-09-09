# 🤖 viz Experts — AI-Powered Zoho CRM Conversational Assistant

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-LLM-orange?logo=groq)](https://groq.com)
[![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![n8n](https://img.shields.io/badge/n8n-Automation-ea4b71?logo=n8n&logoColor=white)](https://n8n.io)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **A fully conversational AI assistant that connects to your Zoho CRM** — ask questions in plain English, get rich visual responses, filter records, update data, and analyze your pipeline — with direct backend integration to Zoho CRM and an optional n8n workflow export available for automation use cases.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Key Features](#-key-features)
- [Everything I Built](#-everything-i-built)
- [Data Flow Architecture](#-data-flow-architecture)
- [Feature Workflows](#-feature-workflows)
- [Directory Structure](#-directory-structure)
- [Installation Guide](#-installation-guide)
- [Environment Setup](#-environment-setup)
- [Usage Instructions](#-usage-instructions)
- [API Endpoints](#-api-endpoints)
- [Configuration Options](#-configuration-options)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Project Overview

**viz Experts CRM Chatbot** is a production-grade AI assistant built during an internship at viz Experts. It wraps Zoho CRM in a natural-language chat interface powered by multiple LLMs (Groq & Google Gemini), with direct Zoho CRM access handled in the backend through OAuth-based connection management. The optional **n8n** workflow export is included for users who want to reuse the automation flow separately, but it is not required for the app to function.

Users authenticate, configure their API keys once, then simply chat:

| Example Query | What Happens |
|---|---|
| `"Show me all deals"` | Fetches + paginates deals in a sortable table |
| `"Show deals greater than 50,000"` | Runs deterministic filter, no LLM needed |
| `"Update Goli's phone to 9999999999"` | 3-step confirm-before-execute workflow |
| `"Show pipeline as a bar chart"` | Renders interactive Chart.js visualization |
| `"What's the total revenue of closed won deals?"` | AI analytics with computed stats |
| `"Show lead #3"` | Single-record deep-dive view |

---

## ✨ Key Features

- 🔐 **User Authentication** — JWT-based login/signup with bcrypt password hashing
- 🧠 **Multi-Provider AI Router** — Automatic failover between Groq and Google Gemini with health tracking
- 🔎 **Smart Intent Classification** — Regex-first to LLM-fallback pipeline for fast routing
- 📊 **Rich Visualizations** — Tables, bar, pie, line, funnel, KPI cards rendered via Chart.js
- 🔄 **Deterministic Filter Engine** — Numeric, string, and date filters run without LLM calls
- ✏️ **Safe Update Workflow** — 3-step search → validate → confirm → execute before any CRM write
- 📄 **Paginated Browsing** — Navigate records with "next", "previous", "page 2", "record #5"
- 🎙️ **Voice Input** — Audio transcription via Groq Whisper Large V3
- 📎 **File Upload** — Attach PDF, DOCX, XLSX, CSV, or image files for AI context
- 💾 **Persistent Sessions** — SQLite stores chat history, API configs, and pending actions
- 🔁 **SSE Streaming** — Real-time token streaming with 5-second liveness pings
- 🕵️ **Full Trace Logging** — Per-request trace IDs, LLM/Zoho/DB timing, observability built in

---

## 🏗️ Everything I Built

### Components Built

| Component | Description |
|---|---|
| **FastAPI Backend** | Full REST API with auth, chat, config, and file upload endpoints |
| **AI Router** (`ai/router.py`) | Multi-provider failover engine with model health scoring and cooldowns |
| **Query Understanding** (`ai/query_understanding.py`) | Regex + LLM hybrid intent classification across 15+ CRM intents |
| **Filter Engine** (`filter_engine.py`) | Zero-LLM deterministic filter for numeric, string, date operations |
| **Action Engine** (`action_engine.py`) | Safe CRM update workflow with validation, disambiguation, and audit log |
| **Groq Client** (`groq_client.py`) | Core response orchestrator — cache, fetch, filter, render, stream |
| **Zoho Client** (`zoho_client.py`) | Direct Zoho CRM client with OAuth token refresh and CRM operations |
| **Visualization Engine** (`ai/visualization_engine.py`) | Chart config builder for 10+ chart types |
| **Analytics Engine** (`ai/analytics_engine.py`) | CRM stats: status distributions, totals, conversion rates, revenue |
| **Pagination Handler** (`ai/pagination_handler.py`) | Page-based navigation with Indian currency formatting |
| **Navigation Handler** (`ai/navigation_handler.py`) | "next/prev/page N/record #N" without LLM involvement |
| **Conversation Context** (`ai/conversation_context.py`) | Active record tracking, history cleanup, follow-up detection |
| **CRM Context Service** (`ai/crm_context_service.py`) | Record fetching, cleaning, and single-record activation |
| **Database Layer** (`database.py`) | SQLite schema: users, sessions, messages, pending actions, audit logs |
| **Auth Module** (`auth.py`) | bcrypt hashing, JWT creation and verification |
| **Trace Logger** (`utils.py`) | Per-request observability with step timing and external call logs |
| **Frontend** (`static/`) | Vanilla HTML + Tailwind CSS + Chart.js SPA with SSE streaming |
| **Optional n8n Workflow** (`n8n_workflow.json`) | Exported workflow for users who want to reuse the automation logic in n8n |

### Technologies & Tools Used

| Category | Technologies |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **AI / LLM** | Groq (Llama 3.1, Llama 3.3, Llama 4, Groq Compound), Google Gemini (2.5 Flash, Flash-Lite, Gemma) |
| **Automation** | Optional n8n export + direct backend OAuth integration |
| **Frontend** | Vanilla HTML, Tailwind CSS (CDN), Chart.js, SSE (EventSource) |
| **Database** | SQLite3 (via Python's built-in `sqlite3`) |
| **Auth** | JWT (PyJWT), bcrypt |
| **File Parsing** | pypdf, python-docx, openpyxl (PDF, DOCX, XLSX, CSV) |
| **HTTP Client** | httpx (async) |
| **Speech** | Groq Whisper Large V3 (audio transcription) |
| **Config** | python-dotenv, pydantic-settings |
| **Cryptography** | cryptography (Fernet encryption for stored API keys) |

### Notable Achievements

- **Zero-LLM filter path** — Most filter queries (numeric, date, string) never call an LLM, making responses 10x faster
- **Multi-provider health system** — Tracks per-model success/failure rates; auto-skips unhealthy providers on cooldown
- **Indian currency formatting** — Custom formatter with lakh/crore grouping for financial data
- **Active record context** — DB-persisted "currently viewing" record so follow-up questions like "what is their email?" work across requests
- **3-step safe update** — No CRM record is ever modified without explicit user confirmation, with audit trail in DB

---

## 🔀 Data Flow Architecture

### High-Level Architecture

```
+------------------------------------------------------------------------+
|                          Browser (SPA)                                  |
|   index.html + app.js + app.css (Tailwind CSS + Chart.js)               |
+----------------------------+-------------------------------------------+
                             |  HTTP / SSE (EventSource)
                             v
+------------------------------------------------------------------------+
|                     FastAPI Backend  (main.py)                          |
|  Auth . Config . Chat . Sessions . File Upload . Audio Transcription    |
+------+----------+---------------+----------------+----------------------+
       |          |               |                |
       v          v               v                v
  SQLite DB   AI Router      Action Engine    Groq Whisper
  (database.py) (ai/router.py) (action_engine.py) (audio)
       |          |               |
       |          +-- Groq API    |
       |          +-- Gemini API  |
       |                         |
       |          v               v
       |   +----------------------------+
       |   |    groq_client.py          |
       |   |  (Response Orchestrator)   |
       |   |  . Cache Manager           |
       |   |  . Filter Engine           |
       |   |  . Analytics Engine        |
       |   |  . Visualization Engine    |
       |   |  . Pagination Handler      |
       |   |  . Navigation Handler      |
       |   +------------+--------------+
       |                |
       |                v
       |   +----------------------------+
       |   |   ZohoCRMClient            |
       |   |   (zoho_client.py)         |
       |   +------------+--------------+
       |                |  HTTPS / REST API
       |                v
       |   +----------------------------+
       |   |    Zoho CRM                |
       |   |  Leads . Contacts          |
       |   |  Deals . Accounts          |
       |   +----------------------------+
       |
       +-- zoho_assistant.db
           . users
           . configurations (encrypted API keys)
           . chat_sessions
           . chat_messages
           . pending_actions (update workflows)
           . update_audit_log
           . provider_health_metrics
```

### Request Execution Flow

#### Read Query (e.g. "Show deals greater than 50,000")

```
1. Browser sends POST /chat (form-data: session_id, prompt)
2. main.py: Validates JWT token -> fetches user config from DB
3. main.py: Checks for active pending_action (update workflow in progress?)
4. main.py: extract_update_details_deterministic() -> regex check (not an update)
5. main.py: detect_intent_by_regex() -> matches "show_deals"
6. main.py: No LLM classification needed (regex matched)
7. main.py: Opens SSE StreamingResponse -> calls stream_groq_response()
8. groq_client.py: Checks SESSION_BROWSING_CACHE for existing records
9. groq_client.py: Cache miss -> calls ZohoCRMClient.fetch_module("Deals")
10. zoho_client.py: Uses OAuth-backed Zoho API calls to fetch CRM records directly
11. groq_client.py: Stores raw records in SESSION_BROWSING_CACHE
12. groq_client.py: apply_deterministic_filters() -> Amount > 50000
13. groq_client.py: render_page_response_from_state() -> builds table JSON
14. SSE: Streams JSON chunks to browser
15. Browser: Parses JSON -> renders interactive table + Chart.js visualizations
16. main.py (finally): save_chat_message() to SQLite
```

#### Update Query (e.g. "Update Goli's phone to 9999999999")

```
1. Browser sends POST /chat
2. main.py: extract_update_details_deterministic() -> matches update pattern
3. main.py: extract_update_details() via LLM -> {target: "Goli", field: "phone", value: "9999999999"}
4. ActionEngine.start_update_workflow():
   a. Search Zoho for "Goli" across Leads, Contacts, Accounts, Deals
   b. If 1 match: create_pending_action(status=AWAITING_CONFIRMATION)
   c. If multiple matches: create_pending_action(status=AWAITING_SELECTION)
   d. Returns confirmation message to user
5. User replies "yes" (or selects record)
6. main.py: get_active_pending_action() -> finds AWAITING_CONFIRMATION action
7. ActionEngine.handle_workflow_step():
   a. Validates field (email format, phone digits, status options, etc.)
   b. Updates pending_action status -> EXECUTING
   c. Calls ZohoCRMClient.update_record() -> direct Zoho CRM API PUT
   d. Verifies update by re-fetching record
   e. Updates pending_action status -> COMPLETED
   f. Logs to update_audit_log
8. SSE: Streams success message
```

---

## 🔧 Feature Workflows

### 1. 🔐 Authentication

**User Journey:**
1. Open the app at `http://localhost:8000`
2. Click "Sign Up" — enter name, email, password
3. Auto-redirected to chat after account creation
4. On future visits, click "Login"

**Behind the scenes:**
- Passwords are hashed with `bcrypt` (salt rounds auto-managed)
- JWT token (HS256, 24-hour expiry) stored in `localStorage`
- All subsequent requests send `Authorization: Bearer <token>`
- Token verification done in `get_current_user_id()` dependency

**Input/Output:**
```json
POST /signup
{ "full_name": "John Doe", "email": "john@example.com", "password": "mypassword" }

Response:
{ "message": "Account created successfully", "token": "eyJ...", "full_name": "John Doe" }
```

---

### 2. ⚙️ API Key Configuration

**User Journey:**
1. After login, click the Settings icon
2. Connect Zoho CRM through the app’s direct backend OAuth flow
3. Enter at least one LLM key: Groq API Key or Google Gemini API Key
4. Click "Test Connection" to verify each key
5. Click "Save Configuration"

**Behind the scenes:**
- Keys are encrypted with Fernet before storage in SQLite
- Zoho CRM access is managed through the backend OAuth connection and token refresh flow
- The optional n8n export is not required for normal app operation
- Keys are resolved per-request via Python `ContextVar` — no global state
- Masked keys shown in UI (first 6 + last 4 chars)

---

### 3. 💬 Conversational CRM Query

**User Journey:**
1. Type any natural language CRM question
2. Hit Enter or click Send
3. Response streams in real-time with a table, chart, or text answer

**Intent Classification Pipeline:**
```
User Query
    |
    +-> Step 1: Regex patterns (instant, no API cost)
    |   e.g. "show leads" -> show_leads
    |
    +-> Step 2: extract_search_request() (e.g. "find John Smith")
    |
    +-> Step 3: extract_update_details_deterministic() (regex update detection)
    |
    +-> Step 4: LLM classify_intent() fallback (Gemini -> Groq chain)
```

**Supported Intents:**

| Intent | Example Query |
|---|---|
| `show_leads` | "Show all leads", "List leads" |
| `show_deals` | "Show open deals", "Get deals" |
| `show_contacts` | "Show contacts", "List contacts" |
| `show_accounts` | "Show accounts", "List companies" |
| `show_activities` | "Today's activities", "Show tasks" |
| `crm_search` | "Find John Smith in Leads" |
| `global_search` | "Search for Acme Corp" |
| `crm_update` | "Update Goli's phone to 9999..." |
| `pipeline_summary` | "Show pipeline summary" |
| `crm_stats` | "CRM statistics", "Analytics overview" |
| `general_chat` | "What's a good follow-up strategy?" |

---

### 4. 🔍 Smart Filtering

**User Journey:**
1. Ask a filtered query: `"Show deals greater than 50000"`
2. Results show filtered table instantly (no LLM call for simple filters)

**Behind the scenes:**
- `parse_filter_query()` extracts: field, operator, value
- Operators: `gt`, `lt`, `gte`, `lte`, `between`, `equals`, `contains`, `starts_with`, `ends_with`
- Date filters: `today`, `this week`, `last month`, `before 2025-01-01`, etc.
- Multi-condition: `"Show leads from Mumbai with revenue > 100000"`
- Fallback: If deterministic filter fails, `ai_post_process_filter()` via LLM

**Field Mappings (Deals):**

| User says | CRM field |
|---|---|
| "amount", "value", "deal value" | `Amount` |
| "stage", "deal stage", "status" | `Stage` |
| "closing date", "date" | `Closing_Date` |

---

### 5. ✏️ Record Update Workflow

**User Journey:**
1. Ask: `"Update Goli's annual revenue to 500000"`
2. Bot searches for "Goli" across all modules
3. Bot shows: `"Found: Goli Srinivas (Lead). Current Annual Revenue: 2,00,000. Update to 5,00,000? Type 'yes' to confirm."`
4. User types: `"yes"`
5. Bot executes update, verifies, shows success message

**Behind the scenes:**
- `pending_actions` DB table tracks workflow state machine:
  `SEARCHING -> AWAITING_SELECTION -> AWAITING_CONFIRMATION -> EXECUTING -> COMPLETED`
- Field validation before execution:
  - Email: regex pattern check
  - Phone: digit-only, minimum 7 digits
  - Website: protocol and format check
  - Lead Status: must be from allowed list
  - Deal Stage: must be from allowed list
- Audit log written to `update_audit_log` table after completion

**Valid Lead Status Values:**
```
Attempted to Contact | Contact in Future | Contacted | Junk Lead
Lost Lead | Not Contacted | Pre Qualified
```

**Valid Deal Stage Values:**
```
Qualification | Needs Analysis | Value Proposition | Identify Decision Makers
Proposal/Price Quote | Negotiation/Review | Closed Won | Closed Lost | Closed Lost to Competition
```

---

### 6. 📊 Data Visualization

**User Journey:**
1. Ask: `"Show pipeline as a bar chart"` or `"Change to pie chart"`
2. Chart renders inline in the chat

**Supported chart types:**

| Type | Best For |
|---|---|
| `table` | Default — all record lists |
| `bar` | Comparisons (deal amounts by stage) |
| `pie` | Distributions (lead status breakdown) |
| `line` | Trends over time |
| `funnel` | Pipeline stages |
| `kpi_cards` | Summary metrics |

**Behind the scenes:**
- `VisualizationEngine` builds a JSON config per chart type
- Frontend reads `visualizations[]` array from SSE response JSON
- Chart.js renders each visualization dynamically
- Switching chart type (e.g. "show as bar") uses cached records — no new Zoho API call

---

### 7. 📄 Pagination & Navigation

**User Journey:**
1. Ask: `"Show all contacts"` — sees first 10 records
2. Type `"next"` — sees records 11–20
3. Type `"show contact #3"` — full detail view of the 3rd record
4. Type `"previous"` — back to previous page

**Supported navigation commands:**

| Command | Action |
|---|---|
| `"next"` / `"next 5"` | Next page / next N records |
| `"previous"` / `"prev"` | Previous page |
| `"page 3"` | Jump to page 3 |
| `"record #5"` / `"lead #2"` | View single record in detail |
| `"first 20"` | Show first 20 records |

---

### 8. 🎙️ Voice Input

**User Journey:**
1. Click the microphone button
2. Speak your query
3. Transcript auto-fills in the chat input
4. Press Enter to send

**Behind the scenes:**
- Browser `MediaRecorder` API captures audio
- Audio blob uploaded to `POST /transcribe`
- Groq Whisper Large V3 model transcribes the audio
- Requires: Groq API key configured

---

### 9. 📎 File Upload

**User Journey:**
1. Click the attachment button
2. Select a file (PDF, DOCX, XLSX, CSV, image)
3. The file content is extracted and added as context to your next message

**Supported formats:**

| Format | How it's parsed |
|---|---|
| `.pdf` | pypdf page extraction |
| `.docx` | python-docx paragraph extraction |
| `.xlsx` / `.xls` | openpyxl sheet/row extraction |
| `.csv` | Python csv module |
| `.txt` | UTF-8 decode |
| `.png`, `.jpg`, `.gif` | File metadata (size, name) |

> **PDF question support:** Users can upload a PDF and ask questions about its content. For testing with Wispr exports, the exported question set can be used as sample prompts to validate the document Q&A flow and confirm the expected answers.

---

## 📁 Directory Structure

```
viz experts/
|
+-- README.md                          <- This file
+-- api_keys.txt                       # Local API key storage (NOT committed)
+-- n8n_workflow.json                  # Optional n8n export for workflow reuse
|
+-- website/
|   +-- zoho_chatbot/                  # Main production application
|   |   +-- requirements.txt           # Python dependencies
|   |   +-- zoho_assistant.db          # SQLite database (auto-created)
|   |   |
|   |   +-- app/                       # FastAPI application package
|   |   |   +-- main.py                # Application entry point & API router
|   |   |   +-- auth.py                # JWT + bcrypt authentication
|   |   |   +-- database.py            # SQLite schema + all DB operations
|   |   |   +-- models.py              # Shared dataclasses (Request/Context/Response)
|   |   |   +-- utils.py               # TraceLogger, file extraction, ContextVars
|   |   |   +-- zoho_client.py         # Direct Zoho CRM client with OAuth support
|   |   |   +-- groq_client.py         # Core response orchestrator
|   |   |   +-- action_engine.py       # CRM update workflow engine
|   |   |   +-- filter_engine.py       # Deterministic filter/sort/search
|   |   |   |
|   |   |   +-- ai/                    # AI Intelligence Layer
|   |   |       +-- __init__.py        # AIRouter singleton initialization
|   |   |       +-- router.py          # Multi-provider AI Router (failover logic)
|   |   |       +-- query_understanding.py   # Intent classification (regex + LLM)
|   |   |       +-- prompt_builder.py  # System prompt templates
|   |   |       +-- conversation_context.py  # Active record + history management
|   |   |       +-- crm_context_service.py   # CRM data fetching + cleaning
|   |   |       +-- analytics_engine.py      # Stats aggregation
|   |   |       +-- visualization_engine.py  # Chart config builder
|   |   |       +-- pagination_handler.py    # Page rendering + navigation
|   |   |       +-- navigation_handler.py    # "next/prev/page N" handling
|   |   |       +-- cache_manager.py         # Session browsing cache
|   |   |       +-- active_record_handler.py # Single record context
|   |   |       +-- response_builder.py      # AI post-process filter
|   |   |       +-- db_metrics.py            # Provider health tracking
|   |   |       +-- ai_config.json           # Model chains + provider config
|   |   |       +-- analytics_rules.json     # Analytics computation rules
|   |   |       +-- adapters/
|   |   |           +-- groq.py              # Groq API adapter
|   |   |           +-- gemini.py            # Google Gemini API adapter
|   |   |
|   |   +-- static/                    # Frontend (served by FastAPI)
|   |       +-- index.html             # Single-page application
|   |       +-- app.js                 # All frontend logic (SSE, Charts, Auth)
|   |       +-- app.css                # Custom styles
|   |       +-- images/                # Static image assets
|   |
|   +-- vizexperts_crm/               # Alternative/backup backend version
|       +-- requirements.txt
|       +-- .gitignore
|       +-- new_backend/              # Refactored backend (modular architecture)
|
+-- docs/                             # Project documentation & presentations
|   +-- AI-Powered CRM Automation Dashboard.pptx
|   +-- Zoho_CRM_RAG_Report_with_Diagrams.docx
|
+-- implementation plans/             # Technical design documents
|   +-- full project architecture_review.md
|   +-- implementation_plan.md
|   +-- walkthrough.md
|
+-- reports/                          # Final project reports
|   +-- internship final report vizexperts.pdf
|
+-- videos/                           # Demo recordings
```

---

## 🚀 Installation Guide

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Download from [python.org](https://python.org) |
| pip | latest | Comes with Python |
| Zoho CRM account | any | With API/OAuth access |
| n8n (optional) | any | [n8n.io](https://n8n.io) — only if you want to use the exported workflow separately |
| Groq API Key | — | Free at [console.groq.com](https://console.groq.com) |
| Google Gemini API Key | — | Optional, free tier at [aistudio.google.com](https://aistudio.google.com) |

> **Important:** You need at least **one LLM API key** (Groq or Gemini). Groq is recommended as the primary provider due to free tier generosity and speed.

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/Golisathwik/viz-experts-crm-chatbot.git
cd viz-experts-crm-chatbot
```

> This project repository: https://github.com/Golisathwik/viz-experts-crm-chatbot.git

### Step 2: Create & Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

From the project root, install the required Python packages:

```bash
pip install -r requirements.txt
```

This repository uses the project root as the app root, not a nested `website/zoho_chatbot` folder.

**What gets installed:**

| Package | Purpose |
|---|---|
| `fastapi>=0.100.0` | Web framework |
| `uvicorn>=0.22.0` | ASGI server |
| `groq==1.4.0` | Groq LLM client + Whisper |
| `httpx>=0.24.1` | Async HTTP client (Gemini calls) |
| `python-dotenv>=1.0.0` | `.env` file loading |
| `pyjwt>=2.8.0` | JWT authentication |
| `bcrypt>=4.0.1` | Password hashing |
| `cryptography>=42.0.0` | API key encryption |
| `pypdf>=3.9.0` | PDF text extraction |
| `python-docx>=0.8.11` | DOCX file parsing |
| `openpyxl>=3.1.2` | Excel file parsing |
| `python-multipart>=0.0.6` | File upload support |
| `pydantic-settings>=2.0.0` | Settings management |
| `python-dateutil` | Date parsing for filters |
| `email-validator>=2.0.0` | Email validation |

### Step 4: Optional n8n Workflow Import

This project is designed to connect to Zoho CRM directly from the backend using the app’s OAuth flow. The n8n workflow is optional and is included only for users who want to import and reuse the same automation logic in n8n.

1. Open your n8n instance
2. Import `n8n_workflow.json` from the project root
3. Configure the Zoho CRM credentials inside n8n if you want to use that flow
4. Activate the workflow only if you plan to use it outside the app
5. If you are not using n8n, skip this step entirely

> **Note:** The core application does not depend on n8n. Zoho connection and token refresh are handled directly inside the backend through the Zoho OAuth service and repository, while the n8n file remains an optional export for automation experiments or external workflow reuse.

### Step 5: Configure Environment Variables

Create a `.env` file in the project root folder (same directory as `requirements.txt` and `new_backend/`):

```env
# Required for authentication
JWT_SECRET_KEY=your-secret-key-here-change-this

# Optional: if you are using the exported n8n workflow separately
N8N_ZOHO_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id

# Optional: override database path
DATABASE_PATH=/path/to/your/zoho_assistant.db

# Optional: set API keys here if you want them as defaults for local testing
GROQ_API_KEY=
GEMINI_API_KEY=
ZOHO_API_KEY=
```

> **Note:** In this project, API keys (Zoho/Groq/Gemini) are primarily configured through the app Settings screen after login. The `.env` file is used for local configuration only and should not replace the user-level settings workflow.

### Step 6: Verify Installation

```bash
python -c "import fastapi, groq, httpx, pydantic_settings; print('All dependencies OK')"
```

---

## ▶️ Usage Instructions

### Start the Development Server

Run the app from the project root with the virtual environment activated:

```bash
uvicorn new_backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Access the Application

Open your browser and navigate to:

```
http://127.0.0.1:8000
```

This project serves its frontend from the root `static/` folder and loads the app through `new_backend/main.py`.

### First-Time Setup

1. **Sign up** — Create your account
2. Click the **Settings / Configuration** button
3. Connect Zoho CRM through the app’s direct OAuth flow
4. Enter your **Groq API Key** and/or **Gemini API Key**
5. Click **"Test Connection"** for each key to verify
6. Click **"Save Configuration"**
7. Start chatting with the CRM assistant

> **Important:** This project is designed to be used from the repository root. The app connects to Zoho CRM directly in the backend; n8n is optional and not required for normal usage. The working app entrypoint is `new_backend/main.py`.

### Sample Queries to Try

```
# Read operations
Show all leads
List deals
Show contacts
Get accounts
Today's activities

# Filtered queries
Show deals greater than 50000
Show leads from Mumbai
Show deals closing this month
Show contacts whose email contains gmail

# Search
Find John Smith
Search for Acme Corp

# Analytics & Charts
Show pipeline summary
Show deals as a bar chart
Change to pie chart
What is total revenue of closed won deals?

# Navigation
next
previous
page 2
record #3
show lead #5

# Updates
Update John's phone to 9876543210
Change Acme deal stage to Closed Won
Set John's lead status to Contacted

# Voice & Files
[Click microphone and speak]
[Click attachment and upload a PDF/DOCX/CSV]
```

### Production Deployment

```bash
# Install Gunicorn
pip install gunicorn

# Start production server
gunicorn new_backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

> **Warning:** For production, ensure:
> - `JWT_SECRET_KEY` is a strong random string (not the default)
> - CORS origins are restricted (update `allow_origins` in `main.py`)
> - The SQLite database file is backed up regularly
> - Run behind a reverse proxy (nginx/Caddy) for HTTPS

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/signup` | Register new user |
| `POST` | `/login` | Login and get JWT |
| `POST` | `/forgot-password` | Reset password (simulated) |

### Configuration

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/config` | Get current config (masked keys) |
| `POST` | `/config/save` | Save API keys |
| `POST` | `/config/test-zoho` | Test Zoho CRM connection |
| `POST` | `/config/test-groq` | Test Groq API key |
| `POST` | `/config/test-gemini` | Test Gemini API key |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/chat-history` | Get all chat sessions |
| `GET` | `/chat-session/{id}` | Get session with messages |
| `POST` | `/chat-session/create` | Create new session |
| `POST` | `/chat-session/{id}/delete` | Delete session |
| `POST` | `/chat` | **Main chat endpoint (SSE streaming)** |
| `POST` | `/transcribe` | Audio to text transcription |

### Settings

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/settings/change-password` | Change user password |
| `POST` | `/settings/clear-history` | Delete all chat history |

### SSE Response Format

The `/chat` endpoint streams Server-Sent Events:

```
data: {"event": "start"}

data: {"chunk": "{\"intent_detected\": \"show_deals\", \"text_response\": \"Here are your deals...\","}

data: {"chunk": "\"visualizations\": [{\"type\": \"table\", \"data\": [...]}]}"}

data: {"event": "complete"}
```

**Chat Request (multipart form-data):**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | int | Yes | Active chat session ID |
| `prompt` | string | Yes | User's message |
| `file` | file | No | Optional file attachment |

**Authorization header required:**
```
Authorization: Bearer <jwt_token>
```

---

## ⚙️ Configuration Options

### AI Model Configuration (`app/ai/ai_config.json`)

The AI router uses a task-based model chain. Customize which models are tried for each task type:

```json
{
  "tasks": {
    "intent_classification": {
      "model_chain": ["gemini-2.5-flash", "groq/compound-mini", "llama-3.1-8b-instant"]
    },
    "crud_extraction": {
      "model_chain": ["gemini-2.5-flash", "groq/compound-mini", "llama-3.1-8b-instant"]
    },
    "general_crm": {
      "model_chain": ["groq/compound", "llama-4-scout-17b-16e-instruct", "gemini-2.5-flash"]
    }
  }
}
```

**Available models:**

| Model ID | Provider | Context | Best For |
|---|---|---|---|
| `gemini-2.5-flash` | Google | 1M tokens | Classification, extraction |
| `gemini-2.5-flash-lite` | Google | 1M tokens | Summaries |
| `groq/compound` | Groq | 128K tokens | General CRM responses |
| `llama-3.3-70b-versatile` | Groq | 32K tokens | Reasoning |
| `llama-4-scout-17b-16e-instruct` | Groq | 64K tokens | Long responses |
| `llama-3.1-8b-instant` | Groq | 8K tokens | Fast classification fallback |

### Session & Cache

- **Session cache** (`SESSION_BROWSING_CACHE`): In-memory per-session, cleared on server restart
- **Active record context**: Persisted in SQLite `chat_sessions` table (survives restarts)
- **Token expiry**: 24 hours (configurable in `auth.py` via `ACCESS_TOKEN_EXPIRE_MINUTES`)

### Database Schema Overview

| Table | Purpose |
|---|---|
| `users` | User accounts (id, name, email, password_hash) |
| `configurations` | Encrypted API keys per user |
| `chat_sessions` | Chat threads with active record context |
| `chat_messages` | All messages (user + assistant) |
| `pending_actions` | Update workflow state machine |
| `update_audit_log` | Full audit trail of CRM updates |
| `provider_health_metrics` | Per-model success/failure/cooldown tracking |

---

## 🧪 Testing

### Project Testing and Validation

This project is validated from the repository root using the live FastAPI app and its API endpoints. The app connects directly to Zoho CRM through the backend OAuth flow; n8n is optional and only needed if you want to import the separate workflow export for external automation.

#### 1. Start the app

```bash
uvicorn new_backend.main:app --reload --host 127.0.0.1 --port 8000
```

#### 2. Open the API docs

Use the FastAPI Swagger UI at:

```
http://127.0.0.1:8000/docs
```

Or use the Redoc alternative at:

```
http://127.0.0.1:8000/redoc
```

#### 3. Test the endpoints manually

```bash
# Sign up
curl -X POST http://127.0.0.1:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Test User", "email": "test@example.com", "password": "pass123"}'

# Login (save the token from the response)
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "pass123"}'

# Chat example (replace YOUR_TOKEN with JWT from login response)
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "session_id=1" \
  -F "prompt=Show all leads"
```

> **Project usage rule:** Run the backend from the repository root, use the live app endpoints, and configure the API keys in the app before testing CRM actions.

---

## 🛠️ Troubleshooting

### Common Issues

#### "Keys missing. Please complete Configuration setup first."
**Cause:** You haven't configured API keys yet.  
**Fix:** Go to Settings, enter Zoho webhook URL + at least one LLM key, then Save.

#### "Failed to connect to Zoho CRM"
**Cause:** Zoho OAuth connection is missing, expired, or invalid.  
**Fix:**
1. Go to the app Settings screen
2. Reconnect Zoho CRM through the backend OAuth flow
3. Verify the client ID, client secret, and redirect settings are valid
4. If you are using the optional n8n workflow separately, ensure that the n8n workflow is running and configured correctly

#### "Groq Whisper transcription failed"
**Cause:** Groq API key not configured, or audio format issue.  
**Fix:** Ensure Groq API key is saved in settings. Audio must be WAV, MP3, M4A, or WebM format.

#### "Response generation timed out after 30 seconds"
**Cause:** n8n or Zoho API is slow, or LLM rate limit hit.  
**Fix:**
1. Check n8n/Zoho connectivity
2. Retry the request
3. The AI router will automatically try backup models if the primary is rate-limited

#### SSE stream shows no data in browser
**Cause:** CORS issue or frontend not pointing to correct backend URL.  
**Fix:** Ensure you're accessing `http://localhost:8000` (not a separate dev server port).

#### "ModuleNotFoundError"
**Cause:** Dependencies not installed or venv not activated.  
**Fix:**
```bash
# Activate venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Reinstall deps
pip install -r requirements.txt
```

#### Database errors on startup
**Cause:** Corrupted SQLite file or permission issue.  
**Fix:** Delete `zoho_assistant.db` — it will be recreated automatically on next start.

> **Caution:** Deleting the database clears all user accounts, chat history, and stored configurations. All users will need to re-register and re-configure API keys.

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch:** `git checkout -b feature/my-new-feature`
3. **Make your changes** following the existing code style
4. **Test your changes** using the existing test suite
5. **Commit:** `git commit -m "feat: add amazing new feature"`
6. **Push:** `git push origin feature/my-new-feature`
7. **Open a Pull Request** with a clear description

### Code Style Guidelines

- Python: Follow PEP 8
- FastAPI: Keep endpoints thin — business logic belongs in service/engine modules
- New CRM modules: Add field mappings to both `filter_engine.py` and `action_engine.py`
- New AI models: Register in `ai/ai_config.json` and add the adapter in `ai/adapters/`

### Architecture Rules

- `conversation_context.py` must NOT call Zoho CRM or any LLM
- `filter_engine.py` must remain deterministic (no LLM calls)
- All CRM writes must go through `ActionEngine` for safety
- API keys must NEVER be logged or exposed in responses

---

## 📄 License

This project was built as an internship project at **viz Experts**. All rights reserved by viz Experts.

For open-source or commercial use, please contact the organization directly.

---

## 🙏 Acknowledgements

- **viz Experts** — for the internship opportunity and project scope
- **Groq** — for blazing-fast LLM inference and the free Whisper API
- **Google DeepMind** — for the Gemini API
- **Optional n8n export** — for users who want to reuse the same automation flow in n8n separately
- **FastAPI / Tiangolo** — for the incredible Python web framework
- **Chart.js** — for beautiful, interactive data visualizations

---

Built with love at **viz Experts** · Powered by **Groq** + **Gemini** + **Zoho CRM** + optional **n8n** export
