"""
generate_email.py
Generates the HTML reminder email body, matching the confirmed prototype style.
"""

import hmac
import hashlib
from datetime import datetime, timedelta

MONTH_NAMES_ZH = {
    1: "1月", 2: "2月", 3: "3月", 4: "4月",
    5: "5月", 6: "6月", 7: "7月", 8: "8月",
    9: "9月", 10: "10月", 11: "11月", 12: "12月",
}


def make_token(bill_id: str, year: int, month: int, secret: str) -> str:
    """Create a short HMAC token to authenticate a mark-paid request."""
    msg = f"{bill_id}:{year}:{month}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()[:24]


def bill_frequency_zh(bill: dict) -> str:
    months = bill["months"]
    if len(months) == 12:
        return "每月繳費"
    return "繳費月份：" + "、".join(f"{m}月" for m in months)


def build_bill_row(bill: dict, is_paid: bool, mark_url: str) -> str:
    late_tag = (
        '<span class="late-fee-tag">⚡ 遲交費</span>' if bill["late_fee"] else ""
    )
    freq = bill_frequency_zh(bill)

    if is_paid:
        return f"""
      <div class="bill-row paid">
        <div class="bill-icon">{bill['icon']}</div>
        <div class="bill-info">
          <div class="bill-name" style="text-decoration:line-through;color:#718096;">
            {bill['name_zh']} {late_tag}
          </div>
          <div class="bill-meta">{bill['name_en']} &nbsp;·&nbsp; {freq}</div>
        </div>
        <div class="status-badge paid">✅ 已繳</div>
      </div>"""
    else:
        return f"""
      <div class="bill-row unpaid">
        <div class="bill-icon">{bill['icon']}</div>
        <div class="bill-info">
          <div class="bill-name">{bill['name_zh']} {late_tag}</div>
          <div class="bill-meta">{bill['name_en']} &nbsp;·&nbsp; {freq}</div>
        </div>
        <div class="status-badge unpaid">⏳ 未繳</div>
        <a class="btn-paid" href="{mark_url}">✓ 標記已繳</a>
      </div>"""


def generate_html(
    month_bills: list,
    month_state: dict,
    year: int,
    month: int,
    pages_base_url: str,
    secret: str,
) -> str:
    """
    Generate the full HTML email body.

    :param month_bills:    Bills due this month (filtered from bills.json)
    :param month_state:    {bill_id: True/False} for current month from state file
    :param year:           Current year
    :param month:          Current month (int)
    :param pages_base_url: GitHub Pages base URL, e.g. https://user.github.io/billreminder
    :param secret:         MARK_PAID_TOKEN secret
    :return:               Complete HTML string
    """
    paid_count = sum(1 for b in month_bills if month_state.get(b["id"], False))
    unpaid_count = len(month_bills) - paid_count
    total_count = len(month_bills)

    today = datetime.now()
    next_day = today + timedelta(days=2)
    next_reminder_str = f"{next_day.month}月{next_day.day}日"
    date_str = f"{year}年 {month}月 {today.day}日"

    # Build bill rows
    rows_html = ""
    for bill in month_bills:
        bid = bill["id"]
        is_paid = month_state.get(bid, False)
        token = make_token(bid, year, month, secret)
        import urllib.parse
        name_encoded = urllib.parse.quote(bill["name_zh"])
        mark_url = (
            f"{pages_base_url}/mark_paid.html"
            f"?bill_id={bid}&year={year}&month={month}"
            f"&token={token}&name={name_encoded}"
        )
        rows_html += build_bill_row(bill, is_paid, mark_url)

    # Late-fee alert (only if unpaid late-fee bills exist)
    has_unpaid_late = any(
        b["late_fee"] and not month_state.get(b["id"], False) for b in month_bills
    )
    alert_html = ""
    if has_unpaid_late:
        alert_html = """
    <div class="alert">
      <span class="alert-icon">⚠️</span>
      <div>
        <strong>注意：部分帳單有遲交附加費。</strong><br>
        請盡快繳清帶有
        <span style="background:#fff3cd;color:#856404;border:1px solid #ffc107;
                     border-radius:4px;padding:0 5px;font-size:11px;font-weight:700;">
          遲交費
        </span>
        標籤的帳單，以免產生額外費用。
      </div>
    </div>"""

    # Summary colours
    unpaid_style = "color:#e53e3e;" if unpaid_count > 0 else "color:#38a169;"

    return f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>帳單提醒 {year}年{MONTH_NAMES_ZH[month]}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang HK",
          "Noto Sans HK",Arial,sans-serif;background:#f0f4f8;color:#1a202c;padding:32px 16px;}}
    .email-card{{max-width:620px;margin:0 auto;background:#ffffff;border-radius:16px;
                overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);}}
    .header{{background:linear-gradient(135deg,#1a56db 0%,#0e3fa3 100%);
             padding:32px 36px 28px;color:#fff;}}
    .header .icon{{font-size:36px;margin-bottom:10px;}}
    .header h1{{font-size:22px;font-weight:700;letter-spacing:.5px;margin-bottom:6px;}}
    .header .subtitle{{font-size:14px;opacity:.85;}}
    .header .date-badge{{display:inline-block;margin-top:14px;
      background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);
      border-radius:20px;padding:4px 14px;font-size:13px;font-weight:600;}}
    .summary{{display:flex;border-bottom:1px solid #e2e8f0;}}
    .summary-item{{flex:1;padding:18px 12px;text-align:center;
                   border-right:1px solid #e2e8f0;}}
    .summary-item:last-child{{border-right:none;}}
    .summary-item .num{{font-size:28px;font-weight:800;line-height:1;}}
    .summary-item .label{{font-size:12px;color:#718096;margin-top:4px;}}
    .body{{padding:28px 36px;}}
    .section-title{{font-size:13px;font-weight:700;text-transform:uppercase;
                    letter-spacing:1px;color:#a0aec0;margin-bottom:14px;}}
    .bill-list{{display:flex;flex-direction:column;gap:10px;margin-bottom:28px;}}
    .bill-row{{display:flex;align-items:center;gap:14px;padding:14px 18px;
               border-radius:10px;border:1.5px solid #e2e8f0;background:#f7fafc;}}
    .bill-row.unpaid{{border-color:#fed7d7;background:#fff5f5;}}
    .bill-row.paid{{border-color:#c6f6d5;background:#f0fff4;opacity:.82;}}
    .bill-icon{{font-size:22px;flex-shrink:0;}}
    .bill-info{{flex:1 1 auto;min-width:0;}}
    .bill-name{{font-size:15px;font-weight:700;}}
    .bill-meta{{font-size:12px;color:#718096;margin-top:2px;}}
    .late-fee-tag{{display:inline-block;background:#fff3cd;color:#856404;
      border:1px solid #ffc107;border-radius:6px;font-size:11px;font-weight:600;
      padding:1px 7px;margin-left:6px;vertical-align:middle;}}
    .status-badge{{flex-shrink:0;border-radius:20px;font-size:12px;
                   font-weight:700;padding:4px 12px;}}
    .status-badge.unpaid{{background:#fff5f5;color:#c53030;border:1.5px solid #fc8181;}}
    .status-badge.paid{{background:#f0fff4;color:#276749;border:1.5px solid #68d391;}}
    .btn-paid{{flex-shrink:0;display:inline-block;
      background:linear-gradient(135deg,#38a169,#276749);color:#fff;
      border:none;border-radius:8px;font-size:12px;font-weight:700;
      padding:7px 14px;text-decoration:none;white-space:nowrap;
      box-shadow:0 2px 6px rgba(56,161,105,.35);}}
    @media only screen and (max-width:480px){{
      body{{padding:12px 8px;}}
      .header{{padding:20px 18px 16px;}}
      .header h1{{font-size:18px;}}
      .body{{padding:18px 14px;}}
      .summary-item .num{{font-size:22px;}}
      .bill-row{{flex-wrap:wrap;gap:8px;padding:10px 12px;}}
      .bill-icon{{font-size:20px;}}
      .bill-name{{font-size:14px;}}
      .status-badge{{font-size:11px;padding:3px 9px;}}
      .btn-paid{{display:block;width:100%;text-align:center;
        padding:9px 0;font-size:13px;margin-top:4px;}}
      .footer{{padding:16px 14px;}}
    }}
    .alert{{display:flex;gap:12px;align-items:flex-start;background:#fffbeb;
            border:1.5px solid #f6c84b;border-radius:10px;padding:14px 18px;
            margin-bottom:28px;font-size:13px;color:#744210;}}
    .alert .alert-icon{{font-size:20px;flex-shrink:0;}}
    .footer{{background:#f7fafc;border-top:1px solid #e2e8f0;padding:22px 36px;
             text-align:center;font-size:12px;color:#a0aec0;line-height:1.7;}}
    .footer a{{color:#4299e1;text-decoration:none;}}
  </style>
</head>
<body>
<div class="email-card">

  <div class="header">
    <div class="icon">🔔</div>
    <h1>每月帳單提醒</h1>
    <div class="subtitle">Monthly Bill Reminder</div>
    <div class="date-badge">📅 {date_str}</div>
  </div>

  <div class="summary">
    <div class="summary-item">
      <div class="num" style="color:#2b6cb0;">{total_count}</div>
      <div class="label">本月帳單</div>
    </div>
    <div class="summary-item">
      <div class="num" style="{unpaid_style}">{unpaid_count}</div>
      <div class="label">待繳費</div>
    </div>
    <div class="summary-item">
      <div class="num" style="color:#38a169;">{paid_count}</div>
      <div class="label">已繳費</div>
    </div>
  </div>

  <div class="body">
    {alert_html}
    <div class="section-title">本月帳單清單</div>
    <div class="bill-list">
      {rows_html}
    </div>

    <div style="background:#ebf8ff;border:1.5px solid #bee3f8;border-radius:10px;
                padding:14px 18px;font-size:13px;color:#2c5282;">
      📬 <strong>下次提醒：</strong>
      如有未繳帳單，系統將於 <strong>{next_reminder_str}</strong>
      再次發送提醒，直至所有帳單繳清為止。
    </div>
  </div>

  <div class="footer">
    此電郵由 <strong>Bill Reminder Bot</strong> 自動發出，請勿直接回覆。<br>
    如需更改設定，請前往
    <a href="https://github.com/{pages_base_url.split('github.io/')[1] if 'github.io' in pages_base_url else ''}">
      GitHub Repository
    </a> 修改帳單清單。<br>
    <span style="color:#cbd5e0;">© {year} Bill Reminder · Powered by GitHub Actions</span>
  </div>

</div>
</body>
</html>"""
