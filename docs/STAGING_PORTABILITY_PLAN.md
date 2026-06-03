# EaseToLearn Video Factory — Mac Mini Staging & AWS Portability Plan

### **Purpose of this document**
One source of truth for standing the factory up on the office Mac Mini, designed so that the eventual move to AWS production is a configuration flip, not a rebuild. Written to remove ambiguity for the team now and to serve as the cutover playbook when upper management gives the green light.

> [!IMPORTANT]
> **Database Scheme Status**: PostgreSQL is confirmed as the database scheme of choice. The factory's [db/engine.py](file:///Users/apple/Desktop/easetolearn.videogeneration/db/engine.py) is already configured to expect `postgresql+psycopg2://` connections for staging and production environments, and AWS RDS will host a PostgreSQL instance.

---

## 1. Scope — What This Phase Is, and What It Is Not
The Mac Mini is an internal staging box, reached only over WireGuard. It has two jobs:
* **Editor QA**: Real video editors inside the company review actual output quality through the Factory Portal.
* **Architecture-flow validation**: Prove the full Director → Vision → Architect → Supervisor → Healer → Critic chain, the Tony AI webhook round-trip, and self-healing all hold together on a real, always-on machine.

It is **not** student-facing. Students enter only at the AWS production phase. A clean run here earns the confidence to make the AWS bet; it does not, by itself, mean "done."

---

## 2. Design Principle — Portability by Config, Not Rebuild
The dependency containers (Redis, RabbitMQ, Qdrant, SearXNG) are already built. The job now is to wire the factory so that nothing about the code or the image changes between the Mac Mini and AWS — only where each dependency lives and which env values are injected.

Three rules enforce this:
1. **Byte-Identical Images**: The factory container is byte-identical across environments. The only difference between the Mac Mini compose file and the AWS task definition is the environment block and the location of the sidecars — never the image, never the code.
2. **Env-Var Bindings**: Every dependency is reached through an env-var endpoint. No localhost or hardcoded hostnames in code.
3. **1:1 Variable Naming**: Env-var names match the AWS target 1:1. The Mac Mini `.env` uses the exact names that the AWS Secrets Manager secret and task definition expect, so migrating values is copy-paste, not translation.

### **Mac Mini ↔ AWS Dependency Swap**

| Dependency | Mac Mini (Staging) | AWS (Production) | Configuration Target |
| :--- | :--- | :--- | :--- |
| **Cache** | `redis` container | Amazon ElastiCache | `REDIS_URL` |
| **Job Bus** | `rabbitmq` container | Amazon MQ / ECS | `RABBITMQ_HOST` / `USER` / `PASS` |
| **Vector DB** | `qdrant` container | Qdrant on ECS | `QDRANT_HOST` / `QDRANT_PORT` |
| **Search** | `searxng` sidecar | `searxng` sidecar | `SEARXNG_URL` |
| **Relational DB** | Staging Postgres container | Amazon RDS | `DATABASE_URL` |
| **Storage** | Local SSD `/stream` | Amazon S3 | `S3_BUCKET` |
| **Secrets** | Local `.env` | AWS Secrets Manager | `ENV` flag |

### **The One Structural Difference: Storage**
Fargate disk is ephemeral, which is why the production path makes S3 mandatory (the code refuses to start without `S3_BUCKET` in production). On the Mac Mini, local SSD storage persists fine, so the factory uses the `/stream/` endpoint with `S3_BUCKET` unset. Flipping `S3_BUCKET` on is the single storage change for AWS, and it is already coded in `_upload_to_s3`. This is a known, one-line configuration move.

---

## 3. Mac Mini Configuration (Locked Decisions)
* **`ENV=dev`**: Local `/stream/` storage, secrets from `.env`, no Secrets Manager.
* **`S3_BUCKET` Unset**: Videos stay on the Mini's SSD (no S3 storage/transfer cost while internal).
* **`LOCAL_CDN_URL`**: Set to the Mini's WireGuard IP address. This is critical so that Portal playback and the callback URLs handed to Tony AI resolve over the WireGuard tunnel. (The default `localhost:8000` silently breaks playback for anyone off the box).
* **`DATABASE_URL`**: Set to the staging PostgreSQL container (not SQLite) to ensure the persistence path being validated matches the production layout.
* **Isolation**: Only the factory + sidecars run on the Mini. The Spring Boot service stays on the app side and talks to the factory over WireGuard.
* **`RENDER_SEMAPHORE`**: Capped at **2** concurrent renders.
* **Disk Hygiene**: Run `test_disk_hygiene.py` via cron to keep the output folders clean.
* **Runtime**: Colima (not Docker Desktop), started via a `launchd` daemon that runs `colima start && docker compose -f docker-compose.macmini.yaml up -d` on boot. Combined with `restart: always`, the stack self-heals after a reboot.
* **Arch**: Images built on the Mini (arm64 / Apple Silicon — the manim base ships a native arm64 variant).

---

## 4. Execution Phases (≈13–22 Engineering Hours)
Ordered to fail fast and cheap: clear blockers first, prove the box is set up before stressing pipelines, validate known-good paths before risky external ones.

### **Phase 0 — Unblock (~1h)**
* Settle the `DATABASE_URL` string targeting the staging PostgreSQL container.
* Execute a test `curl` from inside the box to Tony AI's `/health` over the WireGuard tunnel to confirm callback routing works (verifying that the factory can initiate webhooks back, not just receive triggers).

### **Phase 1 — Author Deployment Artifacts (~3–4h)**
* Author `docker-compose.macmini.yaml` as a mirror of the AWS task definition structure.
* Derive the staging `.env` from the environment contract (Appendix A).
* Set up the Colima `launchd` plist and boot scripts.

### **Phase 2 — Stand It Up (~2–3h)**
* Pull and build the sidecars and API stack on the Mini.
* Verify `/health` returns and `/portal` loads over the WireGuard tunnel from a remote machine.
* Verify `RENDER_SEMAPHORE` limits and local disk hygiene cron.

### **Phase 3 — Happy-Path Validation (~4–6h)**
* Run the first real test job using actual exam HTML in Presentation mode (proven path) to isolate environment issues from pipeline issues.
* Verify successful video streaming over the tunnel via the Portal Vault (validating `LOCAL_CDN_URL`).
* Run the remaining pipelines by ascending risk: Manim → Explainer → Notes → HeyGen (which uses external APIs). Record performance details in the operations logs.

### **Phase 4 — Integration & Resilience (~3–5h)**
* Trigger a real Spring Boot render request and verify the webhook callback returns over the tunnel.
* Perform failure injection tests: pull API credentials or force a Manim timeout to verify the Healer Agent triggers and the Portal displays the correct alert.
* Reboot the Mac Mini and confirm that Colima and the containers self-heal on startup.

### **Phase 5 — Editor QA Loop**
* Onboard video editors to the Portal over WireGuard.
* Collect structured feedback on rendering quality, script accuracy, and animation pacing.

---

## 5. Staging Exit Gate (Go / No-Go for AWS)
Before requesting the management green light for the AWS budget, all of the following conditions must be met:
1. Video editors approve output quality.
2. All six pipelines validated end-to-end.
3. Spring Boot round-trip webhook callback completes cleanly over the tunnel.
4. Self-healing and error recovery confirmed via failure injection.
5. Mac Mini survives a reboot test and several days of continuous uptime.

Meeting this gate is the signal that the AWS bet is safe.

---

## 6. AWS Cutover — The Green-Light Path
When approved, going live reduces to mechanical infrastructure steps. No factory code is touched:
1. Push the container images to **AWS ECR** (build multi-arch or target arm64 Graviton Fargate).
2. Point your environment variables to your managed cloud endpoints (Amazon RDS, Amazon ElastiCache, Amazon MQ, Qdrant).
3. Move the `.env` values directly into **AWS Secrets Manager** (variable names match 1:1).
4. Flip the environment flag to `ENV=production` and set the `S3_BUCKET` name.
5. Run the Jenkins deploy script (`deploy.sh`).
6. Enable the frontend UI integrations (Watch Video buttons, dubbing selectors).
7. Validate scaling performance using Fargate autoscaling metrics and RabbitMQ queue depths.

---

## Appendix A — Single Env Contract (Source of Truth)
The Mac Mini `.env`, the AWS Secrets Manager secret, and the ECS task definition all derive from this list:

```ini
# --- Environment ---
ENV                     # dev (Mac Mini) | production (AWS)
AWS_REGION              # ap-south-1
AWS_SECRETS_NAME        # AWS only

# --- Storage ---
S3_BUCKET               # unset on Mac Mini | set on AWS
LOCAL_CDN_URL           # Mac Mini WireGuard address | unused on AWS

# --- Data plane ---
DATABASE_URL            # postgresql+psycopg2://...
REDIS_URL
SEARXNG_URL
RABBITMQ_HOST
RABBITMQ_USER
RABBITMQ_PASS
RABBITMQ_VHOST
QDRANT_HOST
QDRANT_PORT
QDRANT_API_KEY

# --- Integration security ---
FACTORY_API_KEY
FACTORY_WEBHOOK_SECRET

# --- Provider keys ---
ANTHROPIC_API_KEY
GROQ_API_KEY
GEMINI_API_KEY
ELEVENLABS_API_KEY
HEYGEN_API_KEY
HIGGSFIELD_API_KEY
OPENAI_API_KEY
```
