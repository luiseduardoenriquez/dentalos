#!/usr/bin/env python3
"""Send alert notifications to Telegram.

Usage:
    python scripts/alert_telegram.py --type service_down --message "PostgreSQL is unreachable"
    python scripts/alert_telegram.py --type error_spike --message "Error rate > 5% for 5 min"
    python scripts/alert_telegram.py --type queue_backlog --message "queue depth: 1200"
    python scripts/alert_telegram.py --type disk_space --message "Disk usage at 92%"
    python scripts/alert_telegram.py --type custom --message "Any custom alert message"

Environment variables:
    TELEGRAM_BOT_TOKEN  — Bot token from @BotFather
    TELEGRAM_CHAT_ID    — Chat/group ID to send alerts to

Can be called from:
    - Grafana alert rules (webhook contact point)
    - Cron jobs for periodic checks
    - Manual invocation for ad-hoc alerts
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime

ALERT_ICONS = {
    "service_down": "\u26a0\ufe0f",  # warning
    "error_spike": "\U0001f534",  # red circle
    "queue_backlog": "\U0001f4e8",  # envelope
    "disk_space": "\U0001f4be",  # floppy disk
    "custom": "\u2139\ufe0f",  # info
}

SEVERITY_MAP = {
    "service_down": "P1 - CRITICAL",
    "error_spike": "P2 - HIGH",
    "queue_backlog": "P2 - HIGH",
    "disk_space": "P3 - MEDIUM",
    "custom": "P3 - MEDIUM",
}


def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    """Send a message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")

    req = urllib.request.Request(  # noqa: S310
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return resp.status == 200
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}", file=sys.stderr)
        return False


def format_alert(alert_type: str, message: str) -> str:
    """Format an alert message with icon, severity, and timestamp."""
    icon = ALERT_ICONS.get(alert_type, ALERT_ICONS["custom"])
    severity = SEVERITY_MAP.get(alert_type, SEVERITY_MAP["custom"])
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"{icon} <b>DentalOS Alert</b>\n\n"
        f"<b>Severity:</b> {severity}\n"
        f"<b>Type:</b> {alert_type}\n"
        f"<b>Message:</b> {message}\n"
        f"<b>Time:</b> {timestamp}\n\n"
        f"<i>Environment: {os.getenv('ENVIRONMENT', 'unknown')}</i>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Send DentalOS alerts to Telegram")
    parser.add_argument(
        "--type",
        choices=list(ALERT_ICONS.keys()),
        required=True,
        help="Alert type",
    )
    parser.add_argument("--message", required=True, help="Alert message")
    args = parser.parse_args()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    text = format_alert(args.type, args.message)
    success = send_telegram(bot_token, chat_id, text)

    if success:
        print("Alert sent successfully")
    else:
        print("Failed to send alert", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
