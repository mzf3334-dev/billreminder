"""
send_reminder.py
Entry point for the GitHub Actions bill-reminder workflow.
Reads bills.json + bills_state.json, generates HTML, and sends via Gmail SMTP.
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from generate_email import generate_html


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_bills() -> list:
    with open("bills.json", encoding="utf-8") as f:
        return json.load(f)["bills"]


def load_state() -> dict:
    try:
        with open("bills_state.json", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_month_bills(bills: list, month: int) -> list:
    return [b for b in bills if month in b["months"]]


def get_month_state(state: dict, year: int, month: int) -> dict:
    return state.get(str(year), {}).get(str(month), {})


def send_email(html: str, subject: str, gmail_user: str, gmail_pass: str, recipient: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Bill Reminder 🔔 <{gmail_user}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipient, msg.as_string())


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    now = datetime.now()
    year, month = now.year, now.month

    # Load data
    bills = load_bills()
    state = load_state()
    month_bills = get_month_bills(bills, month)
    month_state = get_month_state(state, year, month)

    if not month_bills:
        print(f"No bills due in month {month}. Skipping.")
        sys.exit(0)

    # Count unpaid
    unpaid = [b for b in month_bills if not month_state.get(b["id"], False)]
    if not unpaid:
        print(f"✅ All {len(month_bills)} bills paid for {year}/{month:02d}. No reminder needed.")
        sys.exit(0)

    print(f"⏳ {len(unpaid)}/{len(month_bills)} bills unpaid for {year}/{month:02d}. Sending reminder…")

    # Read environment secrets
    def require_env(key: str) -> str:
        val = os.environ.get(key, "").strip()
        if not val:
            print(f"ERROR: environment variable '{key}' is not set.", file=sys.stderr)
            sys.exit(1)
        return val

    gmail_user   = require_env("GMAIL_USER")
    gmail_pass   = require_env("GMAIL_APP_PASSWORD")
    recipient    = require_env("RECIPIENT_EMAIL")
    secret       = require_env("MARK_PAID_TOKEN")
    repo         = require_env("GITHUB_REPOSITORY")          # owner/repo
    owner        = repo.split("/")[0]
    repo_name    = repo.split("/")[1]
    pages_base   = f"https://{owner}.github.io/{repo_name}"

    # Generate HTML
    html = generate_html(
        month_bills=month_bills,
        month_state=month_state,
        year=year,
        month=month,
        pages_base_url=pages_base,
        secret=secret,
    )

    # Build subject
    unpaid_names = "、".join(b["name_zh"] for b in unpaid)
    subject = f"🔔 帳單提醒 {year}年{month}月 — 未繳：{unpaid_names}"

    # Send
    send_email(html, subject, gmail_user, gmail_pass, recipient)
    print(f"📧 Reminder email sent to {recipient}")


if __name__ == "__main__":
    main()
