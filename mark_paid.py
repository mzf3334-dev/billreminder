"""
mark_paid.py
Called by the mark-paid GitHub Actions workflow.
Updates bills_state.json to mark a specific bill as paid for the given month,
then the workflow commits the change back to the repo.

Usage:
    python mark_paid.py <bill_id> <year> <month> <token>

The token is verified against MARK_PAID_TOKEN env var before any write is performed.
"""

import hmac
import hashlib
import json
import os
import sys


def verify_token(bill_id: str, year: int, month: int, token: str, secret: str) -> bool:
    msg = f"{bill_id}:{year}:{month}"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()[:24]
    # Constant-time comparison
    return hmac.compare_digest(expected, token)


def load_state() -> dict:
    try:
        with open("bills_state.json", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_bills() -> list:
    with open("bills.json", encoding="utf-8") as f:
        return json.load(f)["bills"]


def main() -> None:
    if len(sys.argv) < 5:
        print("Usage: python mark_paid.py <bill_id> <year> <month> <token>", file=sys.stderr)
        sys.exit(1)

    bill_id = sys.argv[1]
    year    = int(sys.argv[2])
    month   = int(sys.argv[3])
    token   = sys.argv[4]

    secret = os.environ.get("MARK_PAID_TOKEN", "").strip()
    if not secret:
        print("ERROR: MARK_PAID_TOKEN env var not set.", file=sys.stderr)
        sys.exit(1)

    # Verify token
    if not verify_token(bill_id, year, month, token, secret):
        print(f"ERROR: Invalid token for bill '{bill_id}' {year}/{month:02d}.", file=sys.stderr)
        sys.exit(1)

    # Validate bill_id exists in bills.json
    bills = load_bills()
    valid_ids = {b["id"] for b in bills}
    if bill_id not in valid_ids:
        print(f"ERROR: Unknown bill_id '{bill_id}'. Valid: {sorted(valid_ids)}", file=sys.stderr)
        sys.exit(1)

    # Load and update state
    state = load_state()
    state.setdefault(str(year), {}).setdefault(str(month), {})[bill_id] = True

    with open("bills_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✅ Marked '{bill_id}' as paid for {year}/{month:02d}.")

    # Check if all bills for this month are now paid
    month_bills = [b for b in bills if month in b["months"]]
    month_state = state[str(year)][str(month)]
    all_paid = all(month_state.get(b["id"], False) for b in month_bills)
    if all_paid:
        print(f"🎉 All bills for {year}/{month:02d} are now paid!")


if __name__ == "__main__":
    main()
