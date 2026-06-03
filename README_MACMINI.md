# Mac Mini Staging — Setup Runbook

Stand up the EaseToLearn Video Factory on the office Mac Mini (Apple Silicon, reached over WireGuard). Internal staging only — not student-facing.

All files in this bundle go at the **factory repo root**, alongside the `Dockerfile` and `searxng_standalone/`.

## 1. Prerequisites (one-time)
1. Install the runtime (lighter than Docker Desktop, headless-friendly):
   ```bash
   brew install colima docker docker-compose
   ```
2. Enable **auto-login** for the box's user (System Settings → Users & Groups → Login Options). The LaunchAgent needs a user session for colima.
3. Make the start script executable: `chmod +x start-factory.sh`
4. If the repo isn't at `/Users/easetolearn/factory`, update the path in **both** `start-factory.sh` and `com.easetolearn.factory.plist`.

## 2. Configure
1. `cp .env.macmini.template .env`
2. Set `LOCAL_CDN_URL` to the Mini's **WireGuard IP** (e.g. `http://10.8.0.3:8000`) — not localhost. This is the single setting that makes Portal playback and Tony AI callbacks work over the tunnel.
3. Fill in the provider keys, plus `FACTORY_API_KEY` and `FACTORY_WEBHOOK_SECRET` (these two must match Tony AI's Spring Boot config).

## 3. Phase 0 — verify the callback direction
WireGuard transport is up; confirm the factory can *initiate* back to Tony AI:
```bash
curl http://<tony-ai-wg-host>:<port>/health
```
If that returns, the trigger→callback round-trip is clear.

## 4. First start (manual)
```bash
colima start --cpu 6 --memory 12 --disk 60   # tune to the Mini's specs
docker compose -f docker-compose.macmini.yaml up -d --build
```
Confirm:
- `curl http://localhost:8000/health` → ok
- Open `http://<mini-wg-ip>:8000/portal` from another machine on the tunnel — the Curriculum Vault is where editors review renders.
- RabbitMQ management UI (optional): `http://<mini-wg-ip>:15672`

## 5. Auto-start on reboot
```bash
mkdir -p ~/factory/logs
cp com.easetolearn.factory.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.easetolearn.factory.plist
```
Then **reboot the Mini and confirm the stack comes back unattended** — this is the resilience test the launchd setup exists for.

## 6. Validate (Phases 3–4)
- First real job in **Presentation mode** (proven path); play it back from the Portal to confirm `LOCAL_CDN_URL` resolves.
- Then Manim → Explainer → Notes → HeyGen (last; external API).
- Spring Boot trigger→callback round-trip over the tunnel.
- Failure-injection pass (pull a provider key, force a Manim timeout) → confirm the Healer fires and the red alert shows in the Portal.

## AWS migration (when greenlit)
This stack is a mirror of the AWS task definition. Cutover = push the same `factory-api` image to ECR, repoint env vars at managed endpoints (RDS / ElastiCache / Amazon MQ / Qdrant), move `.env` values into Secrets Manager, set `ENV=production` + `S3_BUCKET`. No code change. See the portability plan for the full step list and the go/no-go gate.
