# 🔔 Bill Reminder

Automated monthly bill reminder via **GitHub Actions** + **Gmail**.
Tracks your payment status and stops reminding once a bill is marked paid.

---

## 帳單清單 Bill Schedule

| 帳單 | 繳費月份 | 遲交附加費 |
| --- | --- | :---: |
| 電費 Electricity | 2, 4, 6, 8, 10, 12 月 | ⚡ |
| 煤氣費 Gas | 2, 4, 6, 8, 10, 12 月 | ⚡ |
| 水費 Water | 1, 5, 9 月 | ⚡ |
| 管理費 Management Fee | 每月 | — |
| 電話費 Phone Bill | 每月 | — |
| 差餉及地租 Rates & Ground Rent | 1, 4, 7, 10 月 | ⚡ |

---

## Architecture

```text
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

> **Total time:** ~15 minutes. Follow every step in order.

---

### Step 1 — Get this repository onto your GitHub account

1. Open [github.com/mzf3334-dev/billreminder](https://github.com/mzf3334-dev/billreminder) in your browser
2. Click the **Fork** button (top-right corner)
3. Leave all defaults and click **Create fork**
4. You now have your own copy at `https://github.com/YOUR_USERNAME/billreminder`

> All following steps are done inside **your forked repository**, not the original.

---

### Step 2 — Create a Gmail App Password

> Gmail blocks direct password login from scripts. You need an **App Password** — a special 16-character code just for this app.

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** in the left sidebar
3. Make sure **2-Step Verification** is turned ON
   - If it says "OFF", click it → follow the prompts to enable it → come back here
4. In the **Security** page, scroll down and click **2-Step Verification**
5. Scroll to the very bottom and click **App passwords**
   - If you don't see "App passwords", search for it in the Google Account search bar
6. Under **Select app**, choose **Mail**
7. Under **Select device**, choose **Other (Custom name)** → type `Bill Reminder`
8. Click **Generate**
9. A yellow box shows a **16-character password** like `abcd efgh ijkl mnop`
10. **Copy it immediately** (you cannot see it again) — paste it somewhere temporary like Notepad

> ⚠️ Remove the spaces when you paste it into GitHub. It should be 16 characters with no spaces: `abcdefghijklmnop`

---

### Step 3 — Create a GitHub Personal Access Token (GH_PAT)

> This token lets the confirmation page in your browser call GitHub to trigger the "mark as paid" workflow.

1. Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new)
   - Or navigate: GitHub top-right avatar → **Settings** → scroll down left sidebar to **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
2. Fill in the form:
   - **Token name:** `billreminder-mark-paid`
   - **Expiration:** Choose `No expiration` (or 1 year — you'll need to renew it)
   - **Resource owner:** your username
   - **Repository access:** Select **Only select repositories** → choose `billreminder`
3. Under **Permissions**, expand **Repository permissions** and set:
   - Find **Actions** → change dropdown to **Read and write**
   - Find **Contents** → change dropdown to **Read and write**
   - Leave everything else as **No access**
4. Scroll to the bottom and click **Generate token**
5. The page shows a token starting with `github_pat_...`
6. **Copy it immediately** (you cannot see it again) — paste it somewhere temporary like Notepad

---

### Step 4 — Generate the MARK_PAID_TOKEN secret

> This is a random password used to verify that "mark as paid" requests are genuine and not forged.

Open your **Terminal** (Mac/Linux) or **Command Prompt** (Windows) and run:

```bash
# Mac / Linux
openssl rand -hex 32
```

```powershell
# Windows PowerShell
[System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace("-","").ToLower()
```

You'll get a 64-character string like:

```text
a3f8c2d19e4b7a0f6c3d82e1f0a94b5c7e2d8f1a0b3c4e5d6f7a8b9c0d1e2f3
```

Copy this — you'll use it in the next step.

---

### Step 5 — Add all Secrets to your GitHub Repository

> Secrets are encrypted variables stored by GitHub. Your scripts read them at runtime — they are **never** written into any file or visible in logs.

1. Go to your forked repository: `https://github.com/YOUR_USERNAME/billreminder`
2. Click the **Settings** tab (top menu bar of the repo)
3. In the left sidebar, click **Secrets and variables** → click **Actions**
4. You are now on the **Actions secrets and variables** page
5. Click the green **New repository secret** button
6. Add each secret one at a time by filling in **Name** and **Secret**, then clicking **Add secret**:

| \# | Name | Secret value |
| --- | --- | --- |
| 1 | `GMAIL_USER` | Your Gmail address e.g. `yourname@gmail.com` |
| 2 | `GMAIL_APP_PASSWORD` | The 16-char App Password from Step 2 (no spaces) |
| 3 | `RECIPIENT_EMAIL` | The email where you want to receive bill reminders (can be same as Gmail) |
| 4 | `MARK_PAID_TOKEN` | The 64-char random string you generated in Step 4 |
| 5 | `GH_PAT` | The `github_pat_...` token you copied in Step 3 |

After adding all 5, the page should list:

```text
GMAIL_USER             Updated just now
GMAIL_APP_PASSWORD     Updated just now
RECIPIENT_EMAIL        Updated just now
MARK_PAID_TOKEN        Updated just now
GH_PAT                 Updated just now
```

---

### Step 6 — Enable GitHub Pages

> GitHub Pages hosts the "Mark as Paid" confirmation page that your email buttons link to.

1. In your repository, click **Settings** tab
2. In the left sidebar, click **Pages**
3. Under **Build and deployment**:
   - **Source:** Select `Deploy from a branch`
   - **Branch:** Select `main`  |  Folder: select `/docs`
4. Click **Save**
5. Wait ~1 minute, then refresh the page
6. You should see a green banner:
   > **Your site is live at** `https://YOUR_USERNAME.github.io/billreminder/`
7. Click that link and verify the page loads (it may be blank — that's fine, the important file is `mark_paid.html`)
8. Test the full URL: `https://YOUR_USERNAME.github.io/billreminder/mark_paid.html`
   - You should see the Bill Reminder confirmation page

---

### Step 7 — Enable GitHub Actions

1. In your repository, click the **Actions** tab
2. If you see a yellow banner saying workflows are disabled, click **I understand my workflows, go ahead and enable them**
3. In the left sidebar you should see:
   - `Bill Reminder`
   - `Mark Bill as Paid`

---

### Step 8 — Test it manually

Instead of waiting until the 1st of next month, trigger the reminder now:

1. Click the **Actions** tab in your repository
2. In the left sidebar, click **Bill Reminder**
3. Click the **Run workflow** button (right side)
4. Leave branch as `main` → click the green **Run workflow** button
5. A new run appears — click it to watch the progress
6. After ~30 seconds it should show ✅ green
7. Check your `RECIPIENT_EMAIL` inbox — you should receive the reminder email!

> If it shows ❌ red, click the failed job → read the error log. Common issues: wrong App Password (spaces included), Gmail 2FA not enabled, wrong secret names.

---

### Step 9 — First-time "Mark as Paid" setup in browser

The first time you click a **✓ 標記已繳** button in a reminder email:

1. Your browser opens `https://YOUR_USERNAME.github.io/billreminder/mark_paid.html`
2. The page asks for your **GitHub Personal Access Token**
3. Paste the `github_pat_...` token you saved in Step 3
4. Click **儲存並繼續**
5. The token is saved in your **browser's localStorage** — you will NOT need to enter it again on this device/browser
6. A confirmation card shows the bill name → click **✓ 確認已繳**
7. The page shows ✅ **已成功標記為已繳！**
8. GitHub Actions runs in the background (~30 sec) to update `bills_state.json`

> ⚠️ If you use a different browser or device, you'll need to enter the PAT once on that browser too.

---

## File Structure

```text
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
| --- | --- |
| 1st of month | First reminder for all due bills |
| 3rd, 5th, 7th … | Follow-up reminders (every 2 days) for unpaid bills |
| After all paid | Reminders stop automatically until next month |
