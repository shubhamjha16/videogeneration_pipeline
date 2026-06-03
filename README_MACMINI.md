# Mac Mini Staging — Setup Runbook (DevOps & Management Coordination)

Stand up the EaseToLearn Video Factory on the office Mac Mini (Apple Silicon, reached over WireGuard). Internal staging only — not student-facing.

All files in this bundle reside at the **factory repo root** (`/Users/apple/Desktop/easetolearn.videogeneration` or the designated installation directory on the Mac Mini), alongside the `Dockerfile` and `searxng_standalone/`.

---

## 👥 Roles & Responsibilities Matrix

To prevent confusion between the **DevOps Engineer** and the **Project Owner/User**, tasks are partitioned as follows:

| Role | Responsibility | Tasks |
| :--- | :--- | :--- |
| **DevOps Engineer** | Infrastructure & Daemons | Install runtimes, configure LaunchAgent path mappings, verify container health, set up local database schemas. |
| **Project Owner / User** | Secrets & Validation | Fill in the LLM / TTS / External API provider keys, verify the portal, run smoke tests. |

---

## 🛠️ Step-by-Step Deployment Guide

### Step 1: Infrastructure Setup (DevOps Engineer)

1. **Install Runtimes**:
   Install Colima and Docker CLI on the Mac Mini (lighter, headless-friendly alternative to Docker Desktop):
   ```bash
   brew install colima docker docker-compose
   ```
2. **Configure Auto-Login**:
   On macOS, go to **System Settings → Users & Groups → Login Options** and set **Automatic Login** to the system user. This is necessary because Colima requires an active GUI user session to spin up on boot.
3. **Repository Directory Structure**:
   Clone or pull this repository on the Mac Mini. 
   > [!IMPORTANT]
   > The default configuration scripts assume the repository is located at `/Users/easetolearn/factory`. If you put it in a different path (e.g. `/Users/apple/Desktop/easetolearn.videogeneration`), you **must** update the directory path in:
   > - `start-factory.sh` (line 13: `FACTORY_DIR="/your/custom/path"`)
   > - `com.easetolearn.factory.plist` (lines 17, 24, 26: update `/Users/easetolearn/factory` to `/your/custom/path`)

---

### Step 2: Environment Configuration (User & DevOps Collaboration)

1. **Initialize `.env`**:
   On the Mac Mini, copy the template to the active `.env` file:
   ```bash
   cp .env.macmini.template .env
   ```
2. **Configure WireGuard IP (DevOps)**:
   Ensure the Mac Mini's WireGuard VPN interface is connected.
   * On this network, the **Mac Mini's WireGuard IP is `10.0.1.1`** (the host running the API).
   * Inside `.env`, set `LOCAL_CDN_URL`:
     ```ini
     LOCAL_CDN_URL=http://10.0.1.1:8000
     ```
3. **Fill in Secrets (User/Project Owner)**:
   Open `.env` and fill in the active API provider credentials:
   ```ini
   # --- Integration Security ---
   FACTORY_API_KEY=your_secure_api_key
   FACTORY_WEBHOOK_SECRET=your_secure_webhook_secret

   # --- Provider Keys ---
   ANTHROPIC_API_KEY=sk-ant-...
   GROQ_API_KEY=gsk_...
   GEMINI_API_KEY=AIzaSy...
   ELEVENLABS_API_KEY=...
   HEYGEN_API_KEY=...
   OPENAI_API_KEY=sk-proj-...
   ```

---

### Step 3: Launch & Unattended Recovery (DevOps Engineer)

1. **Verify Launch Script Executability**:
   ```bash
   chmod +x start-factory.sh
   ```
2. **Load LaunchAgent Daemon**:
   Make the stack persistent across reboots:
   ```bash
   mkdir -p ~/factory/logs
   cp com.easetolearn.factory.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.easetolearn.factory.plist
   ```
3. **Reboot Test**:
   Reboot the Mac Mini. Verify that Colima starts up and the containers recover automatically without logging in manually.

---

### Step 4: Verification (User & DevOps)

1. **Local Health Check (DevOps)**:
   Run on the Mac Mini:
   ```bash
   curl http://localhost:8000/health
   ```
2. **Remote Portal Verification (User)**:
   From your MacBook Air (`10.0.1.10`) or any machine connected to the WireGuard VPN, open:
   `http://10.0.1.1:8000/portal`
   Verify that the curriculum vault loads and mock slides can be rendered/previewed.

