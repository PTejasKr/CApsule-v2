# Capsule 🛡️

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

**Capsule** is an AI-powered CI/CD companion that watches your pull requests, checks them against your Business Requirements, spots risky changes, and auto-publishes versioned changelogs. Think of it as having a senior engineer reviewing every PR, but faster and without the coffee breaks.

---

## Quick Overview

What does Capsule actually do?

1. **Watches GitHub PRs** → Gets notified when you open a PR
2. **Reads your Business Rules** → Loads your BRD document to understand what matters
3. **Analyzes code changes** → Uses AI to understand what changed and why
4. **Checks for violations** → Makes sure nothing breaks your critical workflows
5. **Generates summaries** → Creates a human-readable summary in your PR
6. **Auto-versions releases** → Bumps version numbers automatically (MAJOR, MINOR, PATCH)
7. **Pushes changelogs** → Commits versioned changelog entries to your release repo

**End result**: Your team spends less time writing release notes and more time shipping code.

---

## 📋 Quick Links

- [Setup Instructions](#-setup--step-by-step) - Get it running in 15 minutes
- [How Multi-Repo Works](#how-multi-repo-orchestration-works) - For teams managing multiple codebases
- [Architecture](#architecture) - The boring but important stuff
- [Troubleshooting](#troubleshooting) - When things go wrong

---

## Architecture

```mermaid
graph TD
    subgraph GitHub["📦 GitHub"]
        PR["You open a PR"]
    end
    
    subgraph Jenkins["🔧 Jenkins"]
        Webhook["Webhook Event"]
    end
    
    subgraph Capsule["🛡️ Capsule Backend"]
        BRD["Reads Business Rules<br/>from BRD Document"]
        Analyzer["AI Analyzer<br/>NVIDIA LLM"]
        Cache["Results Cache<br/>Redis"]
    end
    
    subgraph Output["📝 Output"]
        PRComment["PR Comment<br/>with Summary"]
        Changelog["Changelog Entry<br/>in Release Repo"]
    end
    
    PR -->|"GitHub Webhook"| Webhook
    Webhook -->|"POST /webhooks"| Capsule
    BRD -.->|"Ground Truth"| Analyzer
    Analyzer -->|"AI Analysis"| Cache
    Cache --> PRComment
    Cache --> Changelog
```

**Flow in human terms:**
> Your GitHub webhook triggers Jenkins → Jenkins tells Capsule → Capsule loads your business rules → AI analyzes the PR diff → Results are cached → Chrome extension shows summary → On merge, changelog auto-updates

---

## Key Features

### 🤖 AI-Powered Code Analysis
- Reads diffs and explains what changed in plain English
- Uses NVIDIA's Llama 3.1 70B model (enterprise-grade accuracy)
- Detects patterns your BRD cares about

### ✅ Business Rule Checking
- Compares code changes against your BRD
- Warns if a PR modifies critical workflows
- Prevents rule violations from shipping

### 🛡️ Anti-Hallucination Layer
- 8-layer validation system ensures AI doesn't make stuff up
- Physical file validation checks
- Low temperature inference (0.1) for consistency
- Confidence scoring on all findings

### 📦 Smart Versioning
- **MAJOR**: When workflow logic changes
- **MINOR**: When features are added
- **PATCH**: When bugs are fixed
- Automatic SemVer bumping on each merge

### 🎛️ Centralized Web Dashboard
- Independent, hosted dashboard accessible via `/dashboard`
- **GitHub OAuth Login**: Secure login utilizing GitHub OAuth apps
- **Role-Based Access Control**: Different views and capabilities for `super_admin` vs normal `user`
- **Dynamic Theming**: Fluid animated dark/light mode toggle
- **Profile Configurations**: Dynamically manage LLM choices (NVIDIA NIM, Gemini, Groq, Ollama), AI parameters, and override custom Business Rules and API tokens via the UI.

### 🎨 Floating Dashboard
- Chrome extension injects a side panel in GitHub
- No styling conflicts (Shadow DOM isolated)
- Shows summaries without page reload
- **Admin Console**: Edit generated summaries, trigger auto-repairs, compare summaries, and approve/reject directly from the UI
- **Weekly Changes Metadata**: Displays the integration (merge) timestamp and the GitHub account that pushed/created each PR inside the weekly summary feed.

### 📊 Workflow Diagram Generator
- Renders workflow diagrams automatically from text descriptions or PR summaries using Mermaid.js and QuickChart
- Accessible via the `/api/workflow/diagram` backend endpoint
- Fully integrated into the Chrome extension popup tab for visual pipeline inspection

### 🛠️ Capsule Multi-Agent Loop
- Multi-agent orchestration loop (`Architect`, `Coder`, and `Debugger` modes)
- Automatic verification and self-healing loop with up to 2 code repair attempts
- Automatic branch patching and commit pushes on successful verification

### 🚀 Jenkins Integration
- Multibranch pipeline ready
- Analyzes PRs before merge
- Auto-publishes on merge to main

---

## Tech Stack (What's Under the Hood)

| What | Technology | Why |
|-----|-----------|-----|
| **API** | FastAPI | Fast, async, great for webhooks |
| **Database** | SQLite (Stub) / PostgreSQL + AsyncPG | Flexible persistence options |
| **Cache** | Redis | Lightning-fast result caching |
| **Task Queue** | Celery | Handles long-running PR analysis in background |
| **AI Model** | NVIDIA NIM, Gemini, Groq, OpenRouter, Ollama | Multi-provider AI compatibility |
| **Frontend** | Vanilla JS + Shadow DOM | Works everywhere, no dependencies |
| **CI/CD** | Jenkins + Multibranch Pipeline | Standard enterprise setup |
| **Container** | Docker Compose | Everything in one `docker-compose up` |
| **Reverse Proxy** | Nginx | Load balancing, SSL termination |

---

## How Multi-Repo Orchestration Works

Running multiple projects? Capsule can analyze PRs from all of them and consolidate everything into one changelog.

### The Setup

```
Your Organization
├── app-backend (monitored)
├── app-frontend (monitored)
├── app-shared (monitored)
└── releases (central changelog destination)
```

### What Happens

```mermaid
graph LR
    Repo1["📱 Frontend Repo<br/>PR #42 Opened"]
    Repo2["⚙️ Backend Repo<br/>PR #88 Opened"]
    Repo3["📚 Shared Repo<br/>PR #15 Opened"]
    
    Webhook1["Webhook Event"]
    Webhook2["Webhook Event"]
    Webhook3["Webhook Event"]
    
    Jenkins["Jenkins Pipeline<br/>Processes All PRs"]
    Capsule["Capsule Backend<br/>Analyzes Each PR<br/>Against Same BRD"]
    
    Cache["Analysis Cache<br/>Redis"]
    
    Release["Release Repo<br/>Single changelog.txt"]
    
    Repo1 -->|"PR opened/updated"| Webhook1
    Repo2 -->|"PR opened/updated"| Webhook2
    Repo3 -->|"PR opened/updated"| Webhook3
    
    Webhook1 --> Jenkins
    Webhook2 --> Jenkins
    Webhook3 --> Jenkins
    
    Jenkins -->|"Analyze PR #42"| Capsule
    Jenkins -->|"Analyze PR #88"| Capsule
    Jenkins -->|"Analyze PR #15"| Capsule
    
    Capsule -->|"Store results"| Cache
    
    Cache -->|"On merge to main"| Release
    
    style Repo1 fill:#e1f5ff
    style Repo2 fill:#e1f5ff
    style Repo3 fill:#e1f5ff
    style Release fill:#c8e6c9
```

### Real Example: Multi-Repo Changelog

When PRs from multiple repos get merged:

```
# Changelog v1.2.3

## Frontend (PR #42)
- Added dark mode toggle to user dashboard
- Fixed mobile responsive layout on tablet devices
- IMPACT: MINOR (feature addition)

## Backend (PR #88)
- Migrated authentication from JWT to OAuth 2.0
- Updated database schema for user profiles
- IMPACT: MAJOR (workflow change - review required!)

## Shared Library (PR #15)
- Fixed memory leak in cache utility function
- Updated TypeScript definitions
- IMPACT: PATCH (bug fix)
```

All in **one file**, **one version number**, **from three different repos**.

---

## ⚡ Setup & Step-by-Step

### 🔧 Manual Setup (Recommended for Dev)

## Prerequisites

Before you begin, ensure your system has the following software installed:

1. **Python 3.10+**: Download and install from [python.org](https://www.python.org/).
2. **Git**: Download and install from [git-scm.com](https://git-scm.com/).
3. **uv**: An extremely fast Python package and project manager. Install it via terminal:
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. **Google Chrome** (or any Chromium-based browser like Brave or Edge) for loading the Capsule browser extension.

---

## Step 1: Clone the Repository

Open your terminal or command prompt and clone the Capsule repository to your local machine:

```bash
git clone <your-repository-url> capsule
cd capsule
```

---

## Step 2: Set Up the Virtual Environment

Capsule uses `uv` for dependency management. Create and activate a virtual environment in the root of the project:

```bash
# Create the virtual environment
uv venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

---

## Step 3: Install Dependencies

With your virtual environment active, install the required Python packages using the `requirements.txt` file:

```bash
uv pip install -r requirements.txt
```

---

## Step 4: Environment Configuration

Capsule relies on environment variables for security keys, API endpoints, and third-party integrations (like GitHub and NVIDIA NIM).

1. In the root directory of the project, locate the `.env.example` file.
2. Make a copy of this file and name it `.env`.
   - On Windows (Command Prompt): `copy .env.example .env`
   - On macOS/Linux: `cp .env.example .env`
3. Open the `.env` file in a text editor and configure the necessary variables. **Important minimum variables to set:**
   - `API_KEY`: Set this to a secure string. You will need to enter this in the Chrome Extension's options page later.
   - `GITHUB_TOKEN`: Generate a Personal Access Token (Classic) in GitHub with `repo` scope and paste it here.
   - `GITHUB_CLIENT_ID`: Your GitHub OAuth App Client ID (Required for user authentication on the dashboard).
   - `GITHUB_CLIENT_SECRET`: Your GitHub OAuth App Client Secret.
   - **AI Provider Keys**: Fill in either `NVIDIA_NIM_API_KEY`, `GEMINI_API_KEY`, or `GROQ_API_KEY` depending on which LLM you plan to use for analysis.

---

## Step 5: Initialize the Database

Capsule uses an SQLite database (`capsule.db`) stored in the `./data/` folder. Ensure the data directory exists, and the application will automatically create the required database tables on its first run.

```bash
mkdir data
```

---

## Step 6: Start the Backend Server

To start the FastAPI backend server, you need to run Uvicorn from the root directory.

```bash
# Run the FastAPI server in development (reload) mode
uv run uvicorn extension.backend.main:app --reload --port 8000
```

The server will start and output logs indicating it is listening on `http://127.0.0.1:8000`. 
- You can access the API documentation at `http://localhost:8000/docs`.
- You can access the main Dashboard at `http://localhost:8000/dashboard`.

---

## Step 7: Load the Chrome Extension

To use the frontend component of Capsule on GitHub PR pages, you need to load the extension into your browser:

1. Open your Chromium-based browser (Chrome, Brave, Edge).
2. Navigate to your extensions management page:
   - Chrome/Brave: `chrome://extensions/`
   - Edge: `edge://extensions/`
3. Toggle on **"Developer mode"** (usually in the top right corner).
4. Click **"Load unpacked"**.
5. In the file dialog, navigate to your `capsule` project folder, select the `extension/frontend` folder, and click "Select Folder".
6. The Capsule extension should now appear in your list of installed extensions.

---

## Step 8: Configure the Extension

1. Click on the Capsule extension icon in your browser toolbar (you may need to pin it first).
2. Right-click the icon and select **"Options"** (or click the settings gear inside the extension popup).
3. In the options page, ensure the **API URL** points to your local server: `http://localhost:8000`
4. Enter the same **API Key** that you configured in your `.env` file (`API_KEY`).
5. Click **Save Settings**.

---

## Troubleshooting

- **"GitHub Client ID not configured" on Dashboard Login**: Ensure you have successfully created a GitHub OAuth application (Authorization callback URL should be `http://localhost:8000/api/auth/github/callback`) and that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correctly populated in your `.env` file.
- **Server Not Starting / Import Errors**: Ensure you are running Uvicorn from the absolute root directory of the project, not from inside the `extension/backend` folder. If necessary, inject the python path manually: `$env:PYTHONPATH="."; uv run uvicorn extension.backend.main:app --reload --port 8000`
- **Extension cannot connect to backend**: Verify that Uvicorn is running on port `8000` and that you don't have any typos in the extension's options page.


---

## Environment Variables (The Reference)

| Variable | What It Does | Example |
|----------|------------|---------|
| `API_KEY` | Chrome extension auth token | `KX5vJ8qWpZlM2nR9sT6uVwXyZa1bCdEf` |
| `GITHUB_TOKEN` | Authenticate with GitHub API | `ghp_xxxxxxxxxxxx` |
| `GITHUB_WEBHOOK_SECRET` | Verify GitHub webhooks are legit | `ab12cd34ef56gh78ij90kl12mn34op56` |
| `CHANGELOG_REPO` | Where to push changelogs | `your-org/releases` |
| `NVIDIA_NIM_API_KEY` | Access NVIDIA LLM | `nvapi_xxxxxxxxxxxx` |
| `NVIDIA_NIM_BASE_URL` | NVIDIA API endpoint | `https://integrate.api.nvidia.com/v1` |
| `NVIDIA_NIM_MODEL` | Which LLM to use | `meta/llama-3.1-70b-instruct` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://postgres:postgres@postgres:5432/capsule` |
| `REDIS_HOST` | Redis cache server | `redis` (in Docker, use service name) |
| `BRD_FILE_PATH` | Path to your business rules | `./brd/requirements.md` |
| `LOG_LEVEL` | How verbose the logs are | `INFO` (or `DEBUG` for troubleshooting) |

---

## Testing It Out

### Test 1: Create a Test PR

1. Fork the Capsule repo (or create a test repo)
2. Create a new branch: `git checkout -b test-capsule`
3. Make a small change (add a comment, update a line)
4. Push and create a PR
5. Check the PR page - you should see the Capsule badge
6. Click it to see the AI analysis

### Test 2: Check Backend Logs

```bash
docker-compose logs -f capsule-api-server
```

You should see requests coming in when you open the PR.

### Test 3: Merge and Check Changelog

1. Merge the PR to `main`
2. Check your release repo - `changelog.txt` should be updated automatically
3. Version number should be bumped

---

## Common Issues & Fixes

### "Chrome Extension says 'Connection Failed'"

**Problem**: Extension can't reach the backend.

**Fix**:
```bash
# 1. Check if API is running
curl http://localhost:8000/api/health

# 2. Check the backend URL in extension settings
# (Should be http://localhost:8000 for local setup)

# 3. Check firewall - port 8000 might be blocked
sudo lsof -i :8000  # See what's using port 8000

# 4. Restart the API
docker-compose restart capsule-api-server
```

### "No Changelog Generated"

**Problem**: You merged a PR but nothing happened.

**Fix**:
```bash
# 1. Verify CHANGELOG_REPO is set correctly in .env
grep CHANGELOG_REPO .env

# 2. Check GitHub token has repo access
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# 3. Check Celery worker logs
docker-compose logs capsule-celery-worker

# 4. Manually trigger changelog generation
curl -X POST http://localhost:8000/api/pr/1/generate-changelog \
  -H "X-API-Key: $API_KEY"
```

### "NVIDIA API Error"

**Problem**: `"Unable to connect to NVIDIA NIM"`

**Fix**:
```bash
# 1. Verify API key is correct
echo $NVIDIA_NIM_API_KEY

# 2. Test connectivity to NVIDIA
curl -H "Authorization: Bearer $NVIDIA_NIM_API_KEY" \
  https://integrate.api.nvidia.com/v1/models

# 3. Check if you've exceeded rate limits
# (Wait a few minutes if rate-limited)

# 4. Use debug logging
# Set LOG_LEVEL=DEBUG in .env and restart
docker-compose restart capsule-api-server
```

### "Jenkins Webhook Not Triggering"

**Problem**: You created a PR but Jenkins didn't run.

**Fix**:
```bash
# 1. Check webhook delivery logs in GitHub
# Settings → Webhooks → [Your Webhook] → Recent Deliveries

# 2. Test the webhook manually
curl -X POST http://your-jenkins-server/github-webhook/ \
  -H "Content-Type: application/json" \
  -d '{"action":"opened","pull_request":{"number":1}}'

# 3. Check Jenkins plugin is installed
# Manage Jenkins → Plugin Manager → Search "GitHub"
# Make sure "GitHub Integration Plugin" is installed

# 4. Verify Jenkins can be reached from GitHub
# Test: curl -I http://your-jenkins-server/github-webhook/
```

### "Database Connection Error"

**Problem**: `"Cannot connect to postgresql://localhost:5432"`

**Fix**:
```bash
# 1. Check if PostgreSQL container is running
docker-compose ps postgres

# 2. View container logs
docker-compose logs postgres

# 3. Force restart the database
docker-compose down -v  # WARNING: This deletes data!
docker-compose up -d

# 4. Check DATABASE_URL in .env is correct
# Should be: postgresql+asyncpg://postgres:postgres@postgres:5432/capsule
```

---

## For the Curious: How the AI Works

### The 8-Layer Anti-Hallucination Shield

Why we don't trust AI blindly:

1. **Temperature 0.1** - Keeps responses consistent, not creative
2. **Confidence scoring** - AI rates how sure it is (we ignore low-confidence findings)
3. **Fact grounding** - Cross-references findings against actual file changes
4. **BRD validation** - Only reports violations actually mentioned in your BRD
5. **File existence checks** - Verifies modified files actually exist
6. **Pattern matching** - Double-checks findings with regex patterns
7. **Human review prompts** - Flags findings for manual review if unsure
8. **Changelog validation** - Makes sure generated entries match actual changes

**Result**: You get AI analysis you can actually trust, not hallucinations.

### Map-Reduce with a Holistic Reduce Pass

Capsule analyzes large PRs in two stages so nothing gets silently dropped:

1. **Map** – The unified diff is split into file-bounded chunks (`max 300 lines` each) and analyzed concurrently. This keeps any single PR within the LLM's context window.
2. **Reduce (holistic)** – The merged per-chunk results are sent back to the LLM **once** for a global pass. This captures relationships that span chunks (renamed functions, shared helpers, cross-file workflow transitions) that per-chunk analysis alone would miss.
3. **Critic + Cross-validate** – The reduced output is verified against the raw diff and stripped of any fabricated file references (see the 8-Layer Shield above).

The holistic reduce pass is controlled by `GLOBAL_REDUCE_ENABLED` (default `true`). Set it to `false` to skip the extra LLM call and fall back to the raw merged chunks for lower latency/cost.

---

## Multi-Repo Deep Dive

### How It Actually Works

Say you have 3 repos with these webhooks all pointing to the same Jenkins:

```
Frontend: https://github.com/acme/app-ui
  ↓ PR opened
  → Webhook to Jenkins

Backend: https://github.com/acme/app-api
  ↓ PR opened
  → Webhook to Jenkins

Shared: https://github.com/acme/app-shared
  ↓ PR opened
  → Webhook to Jenkins
```

When your team merges PRs to main across all 3 repos, Capsule:

1. **Collects all merged PRs** from PostgreSQL
2. **Retrieves cached analysis** from Redis (fast!)
3. **Aggregates results** - Groups by repo, calculates overall SemVer bump
4. **Generates consolidated changelog** - One entry per PR, organized by repo
5. **Bumps version** - Highest impact determines version bump (MAJOR > MINOR > PATCH)
6. **Pushes to release repo** - Updates `changelog.txt` with new version and all entries

### Data Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant Jenkins as Jenkins
    participant Cache as Redis Cache
    participant DB as PostgreSQL
    participant AI as NVIDIA LLM
    participant Release as Release Repo

    Dev->>GH: Open PR in app-ui
    GH->>Jenkins: Webhook
    Jenkins->>DB: Store PR metadata
    DB->>DB: Query BRD (business rules)
    Jenkins->>AI: Send PR diff + BRD
    AI-->>Jenkins: Analysis result
    Jenkins->>Cache: Store analysis (10 min TTL)
    GH->>GH: Show Capsule badge on PR

    Note over Dev: ... time passes ...
    
    Dev->>GH: Merge PR to main
    GH->>Jenkins: Webhook (PR merged)
    Jenkins->>DB: Query all merged PRs
    DB-->>Jenkins: List of merged PRs
    Jenkins->>Cache: Fetch cached analysis
    Cache-->>Jenkins: Analysis results
    Jenkins->>Jenkins: Aggregate + calculate SemVer
    Jenkins->>Release: Push changelog v1.2.3
    Release->>GH: Create commit + tag
```

---

## What's Next?

- **Self-host**: Run this on your own server instead of localhost
- **Custom AI models**: Swap NVIDIA LLM for your own model
- **Slack notifications**: Get alerts when high-impact PRs are analyzed
- **Policy enforcement**: Automatically block merges that violate rules

---

## Help & Support

### Find an Issue?

1. Check [existing issues](https://github.com/PTejasKr/Capsule/issues)
2. Create a new issue with:
   - What you were trying to do
   - What happened
   - Full error message (screenshot is fine)
   - Your setup (Docker? Jenkins version? etc.)

### Want to Contribute?

- Fork the repo
- Create a feature branch
- Make your changes
- Submit a PR

We read all submissions! 🙏

---

## License

MIT - Do whatever you want with this, just don't blame us if it breaks production. (Just kidding, please test first.)

---

**Made by engineers, for engineers.**

*Questions? Issues? Ideas? Create an issue or start a discussion. We're here to help.*

**Latest version**: 1.1.0 | **Last updated**: 2026-06-30 | **Status**: ✅ Production Ready
