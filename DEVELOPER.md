# Developer Guide — Fresh Machine Setup

Everything you need to go from `git clone` to fully running stack.

# Developer Guide — Fresh Machine Setup

Everything you need to go from `git clone` to fully running stack.

---

## Prerequisites

Install these before starting:

| Tool | Min version | Install |
|------|-------------|---------|
| Python | 3.12 | https://python.org |
| Node.js | 20 | https://nodejs.org |
| Docker Desktop | any recent | https://docker.com |
| Ollama | any | https://ollama.com |
| Git | any | https://git-scm.com |

---

## Step 1 — Clone & create `.env`

```bash
git clone <repo-url>
cd ai-copilot-optimizer
```

Create `.env` in the project root:

```dotenv
# Generate JWT_SECRET with:
#   python -c "import secrets; print(secrets.token_hex(20))"
JWT_SECRET=<paste generated value>

DATABASE_URL=postgresql+asyncpg://postgres:changeme@localhost:5432/ai_optimizer
REDIS_URL=redis://localhost:6379/0
POSTGRES_PASSWORD=changeme

# --- LLM: Ollama (local, free) ---
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:latest          # must match an installed ollama model

# --- Auth ---
DEMO_USERNAME=admin
# Generate with: python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt(12)).decode())"
DEMO_PASSWORD_HASH=<paste bcrypt hash>
```

### How to generate each secret value

**JWT_SECRET** (random 40-char hex):
```powershell
python -c "import secrets; print(secrets.token_hex(20))"
```

**DEMO_PASSWORD_HASH** (bcrypt hash of your chosen password):
```powershell
python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt(12)).decode())"
```
> Note: `bcrypt` here is the standalone `bcrypt` package, not `passlib`. Install with `pip install bcrypt` if needed.

---

## Step 2 — Pull Ollama model

```powershell
ollama pull gemma3:latest
```

Confirm it's available:
```powershell
ollama list
```

---

## Step 3 — Start Postgres & Redis

```powershell
docker compose up -d postgres redis
docker compose ps   # both should show (healthy)
```

---

## Step 4 — Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

Run the server **from the project root** (not inside `backend/`):

```powershell
cd ..   # back to project root
backend\.venv\Scripts\uvicorn.exe backend.main:app --reload --port 8000
```

Verify:
```powershell
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content
# → {"status":"ok"}
```

Get a JWT token (save it — needed for the extension):
```powershell
$token = (Invoke-WebRequest -Uri http://localhost:8000/auth/login -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin"}' `
  -UseBasicParsing | ConvertFrom-Json).access_token
Write-Host $token
```

---

## Step 5 — Dashboard

```powershell
cd dashboard
npm install
npm run dev
```

Open http://localhost:5173 → log in with `admin` / `admin`.

---

## Step 6 — VS Code Extension

### Option A: Install the packaged `.vsix` (use in any real project)

```powershell
cd vscode-extension
npm install
npm run compile
npx @vscode/vsce package --no-dependencies
# → produces ai-copilot-optimizer-1.0.0.vsix

code --install-extension ai-copilot-optimizer-1.0.0.vsix
```

Reload VS Code when prompted.

In your Java project:
1. `Ctrl+Shift+P` → **AI Copilot Optimizer: Set Backend JWT Token** → paste the token from Step 4
2. Open any `.java` file → save, or `Ctrl+Shift+P` → **Build Optimized Copilot Prompt**
3. Right-click a Java folder in Explorer → **Build Optimized Copilot Prompt (Folder)**

### Option B: F5 development mode (iterate on extension code)

Open the `vscode-extension/` folder in VS Code and press **F5**.  
A new Extension Development Host window opens with the extension loaded.

---

## Step 7 — IntelliJ Plugin (optional)

```powershell
cd intellij-plugin
.\gradlew.bat runIde   # launches a sandboxed IntelliJ with plugin loaded
```

In the sandboxed IDE: **File → Settings → AI Copilot Optimizer** → set Backend URL + paste JWT.

---

## Common Troubleshooting

| Symptom | Fix |
|---------|-----|
| `RuntimeError: JWT_SECRET env var is not set` | Make sure `.env` is in the project root and you ran uvicorn from the project root |
| `502 LLM unavailable` | Check `ollama list` — model name in `.env` must match exactly |
| `model requires more system memory` | Switch to a smaller model: `LLM_MODEL=gemma3:latest` or `llama3.2:3b` in `.env` |
| Postgres connection refused | `docker compose up -d postgres` |
| Redis connection refused | `docker compose up -d redis` |
| Dashboard login fails | Re-generate `DEMO_PASSWORD_HASH` with the bcrypt command above |
| Extension shows no result | Run **Set Backend JWT Token** first; backend must be running on port 8000 |
| `passlib` bcrypt error | Pin `bcrypt==3.2.2` in `requirements.txt` — passlib is incompatible with bcrypt≥4 |
