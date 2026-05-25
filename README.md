# 🔔 Bill Reminder

Automated monthly bill reminder via **GitHub Actions** + **Gmail**.
Tracks your payment status and stops reminding once a bill is marked paid.

---

## 帳單清單 Bill Schedule

| 帳單 | 繳費月份 | 遲交附加費 |
|------|---------|:---------:|
| 電費 Electricity | 2, 4, 6, 8, 10, 12 月 | ⚡ |
| 煤氣費 Gas | 2, 4, 6, 8, 10, 12 月 | ⚡ |
| 水費 Water | 1, 5, 9 月 | ⚡ |
| 管理費 Management Fee | 每月 | — |
| 電話費 Phone Bill | 每月 | — |
| 差餉及地租 Rates & Ground Rent | 1, 4, 7, 10 月 | ⚡ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (bill-reminder.yml)                             │
│  Cron: 1st of month + every 2 days                              │
│                                                                 │
│  1. Read bills.json  ──►  determine this month's bills          │
│  2. Read bills_state.json  ──►  check which are unpaid          │
│  3. If unpaid bills exist  ──►  send Gmail reminder             │
└───────────────┬─────────────────────────────────────────────────┘
                │ email with "✓ 標記已繳" buttons
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  User's Gmail Inbox                                             │
│  Clicks "✓ 標記已繳" button                                     │
└───────────────┬─────────────────────────────────────────────────┘
                │ link to GitHub Pages
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  docs/mark_paid.html  (GitHub Pages)                            │
│  Shows confirmation UI                                          │
│  Calls GitHub REST API → triggers mark-paid.yml                 │
└───────────────┬─────────────────────────────────────────────────┘
                │ workflow_dispatch
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (mark-paid.yml)                                 │
│  Verifies HMAC token  ──►  updates bills_state.json  ──►  commit│
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup Guide

### Step 1 — Fork / Clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/billreminder.git
cd billreminder
```

### Step 2 — Configure GitHub Secrets

Go to **Repository → Settings → Secrets and Variables → Actions** and add:

| Secret Name | Description |
|-------------|-------------|
| `GMAIL_USER` | Your Gmail address, e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail **App Password** (not your regular password) |
| `RECIPIENT_EMAIL` | Email to receive reminders (can be same as GMAIL_USER) |
| `MARK_PAID_TOKEN` | A random secret string (min 32 chars). Generate with: `openssl rand -hex 32` |
| `GH_PAT` | GitHub Personal Access Token with **`contents:write`** and **`actions:write`** permissions |

#### How to get a Gmail App Password
1. Enable 2-Step Verification on your Google Account
2. Go to **Google Account → Security → 2-Step Verification → App passwords**
3. Create a new App Password for "Mail" / "Other (custom name)"
4. Copy the 16-character password

#### How to create a GitHub PAT (Fine-grained)
1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**
3. Set Repository access: this repository only
4. Permissions needed:
   - **Actions** → Read and write
   - **Contents** → Read and write
5. Copy the token — save it as the `GH_PAT` secret AND note it for Step 5

### Step 3 — Enable GitHub Pages

1. Go to **Repository → Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `docs` folder
4. Save — your pages URL will be: `https://YOUR_USERNAME.github.io/billreminder/`

### Step 4 — Enable Actions

Make sure Actions are enabled for your repository:
**Repository → Settings → Actions → General → Allow all actions**

### Step 5 — First-time mark_paid.html setup

When you first click a "✓ 標記已繳" button in an email:
1. The page will ask for your **GitHub PAT** (same token from Step 2 `GH_PAT`)
2. Enter it and click **儲存並繼續**
3. The token is saved in your browser's `localStorage` — you won't need to enter it again

---

## File Structure

```
billreminder/
├── .github/
│   └── workflows/
│       ├── bill-reminder.yml    # Cron job: sends reminder emails
│       └── mark-paid.yml        # Triggered by email button: updates state
├── docs/
│   └── mark_paid.html           # GitHub Pages: confirms & triggers mark-paid
├── bills.json                   # Bill definitions (edit to add/remove bills)
├── bills_state.json             # Auto-updated payment state (do not edit manually)
├── generate_email.py            # HTML email generator
├── send_reminder.py             # Main reminder script
├── mark_paid.py                 # Marks a bill as paid in state file
├── requirements.txt             # Python deps (stdlib only)
└── prototype.html               # Email design prototype
```

---

## Adding or Modifying Bills

Edit `bills.json` to add, remove, or change bills:

```json
{
  "bills": [
    {
      "id": "my_new_bill",
      "name_zh": "新帳單",
      "name_en": "New Bill",
      "icon": "🧾",
      "months": [3, 6, 9, 12],
      "late_fee": false
    }
  ]
}
```

- `id` — unique snake_case identifier
- `months` — array of months when this bill is due (1–12)
- `late_fee` — `true` shows the ⚡ warning badge in the email

---

## Manual Trigger

You can manually trigger a reminder from the Actions tab:
**Actions → Bill Reminder → Run workflow**

---

## Reminder Schedule

| Day | Action |
|-----|--------|
| 1st of month | First reminder for all due bills |
| 3rd, 5th, 7th … | Follow-up reminders (every 2 days) for unpaid bills |
| After all paid | Reminders stop automatically until next month |
