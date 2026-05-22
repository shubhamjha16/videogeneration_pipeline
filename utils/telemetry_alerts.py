import os
import json
import requests
from datetime import datetime, timezone

# Slack webhook URL configuration (from environment)
SLACK_WEBHOOK_URL = os.environ.get("OPERATIONS_SLACK_WEBHOOK")

# Standard Monthly Budget Limit (in USD)
MONTHLY_BUDGET_USD = float(os.environ.get("MONTHLY_BUDGET_LIMIT_USD", 250.00))

def calculate_cumulative_spend() -> float:
    """Reads cost records ledger to calculate current month's cumulative spend."""
    ledger_path = os.environ.get("COST_LEDGER_PATH", "output/cost_records.jsonl")
    if not os.path.exists(ledger_path):
        return 0.0
    
    total_spend = 0.0
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                total_spend += entry.get("cost_usd", 0.0)
    except Exception as e:
        print(f"⚠️ Telemetry Alert: Failed to parse cost ledger: {e}")
    return round(total_spend, 4)

def send_slack_notification(title: str, blocks: list, fallback_text: str):
    """Sends a rich block-formatted message to the Operations Slack channel."""
    if not SLACK_WEBHOOK_URL:
        print(f"ℹ️ [TELEMETRY LOG] (Slack Hook not set): {fallback_text}")
        return False
        
    payload = {
        "text": fallback_text,
        "blocks": blocks
    }
    
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠️ Telemetry Alert: Slack webhook delivery failed: {e}")
        return False

def alert_pipeline_failure(job_id: str, topic: str, error_msg: str, sunk_cost: float):
    """Triggers an alert on active rendering failure with operational metadata."""
    print(f"🚨 [TELEMETRY ALARM] Job {job_id} failed permanently! Sunk cost: ${sunk_cost:.4f}")
    
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fallback = f"🚨 Render Job Failed: {job_id} | Topic: {topic} | Error: {error_msg}"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Render Pipeline Failure Alert",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Job ID:*\n`{job_id}`"},
                {"type": "mrkdwn", "text": f"*Topic:*\n{topic}"},
                {"type": "mrkdwn", "text": f"*Sunk Cost (USD):*\n${sunk_cost:.4f}"},
                {"type": "mrkdwn", "text": f"*Timestamp:*\n{timestamp}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error Details:*\n```{error_msg}```"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🔧 *Operations Team Action:* Inspect the ECS Fargate CloudWatch logs for troubleshooting."
                }
            ]
        }
    ]
    
    send_slack_notification("Pipeline Failure", blocks, fallback)

def check_monthly_budget():
    """Validates current cumulative spend against monthly threshold budget limit."""
    current_spend = calculate_cumulative_spend()
    print(f"📊 [BUDGET MONITOR] Cumulative spend: ${current_spend:.4f} / ${MONTHLY_BUDGET_USD:.2f}")
    
    if current_spend >= MONTHLY_BUDGET_USD:
        # Critical budget exceeded alert
        fallback = f"⚠️ BUDGET ALERT: Monthly budget limit exceeded! Spend: ${current_spend:.2f} >= Budget: ${MONTHLY_BUDGET_USD:.2f}"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *CRITICAL BUDGET LIMIT EXCEEDED* ⚠️\n*Spend:* `${current_spend:.2f}` / Budget: `${MONTHLY_BUDGET_USD:.2f}`\nAPI generation requests may be throttled to prevent excess costs."
                }
            }
        ]
        send_slack_notification("Budget Limit Exceeded", blocks, fallback)
    elif current_spend >= (MONTHLY_BUDGET_USD * 0.8):
        # 80% Warning milestone alert
        fallback = f"⚠️ BUDGET WARNING: Spend has hit 80% of budget limit. Spend: ${current_spend:.2f}"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Budget Warning Milestone* ⚠️\n*Cumulative Spend:* `${current_spend:.2f}` has exceeded *80%* of your monthly budget limit (`${MONTHLY_BUDGET_USD:.2f}`)."
                }
            }
        ]
        send_slack_notification("Budget Milestone Warning", blocks, fallback)

def alert_low_thirdparty_credits(provider: str, current_balance: int, threshold: int = 5000):
    """Triggers an alert when an external provider API key balance runs below threshold."""
    print(f"⚠️ [CREDIT ALERT] Provider '{provider}' balance is low: {current_balance} remaining.")
    
    fallback = f"⚠️ LOW CREDITS WARNING: {provider} balance is low ({current_balance} units remaining)."
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *LOW API KEY CREDITS WARNING* ⚠️\n*Provider:* `{provider}`\n*Remaining Balance:* `{current_balance}` (Threshold: `{threshold}`)\nPlease top up your accounts to prevent render generation blockages."
            }
        }
    ]
    send_slack_notification("Low API Credits", blocks, fallback)
