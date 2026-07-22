# Capsule - Manual Setup Guidelines

This document provides in-depth, step-by-step instructions for manually setting up the Capsule project on a completely new system.

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
