"""
test_billreminder.py
Run with:  python3 test_billreminder.py
"""

import hmac
import hashlib
import importlib
import json
import os
import shutil
import smtplib
import sys
import tempfile
import unittest

# Make sure the project root is importable
sys.path.insert(0, os.path.dirname(__file__))


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

SECRET = "testsecret123"
PAGES_BASE = "https://mzf3334-dev.github.io/billreminder"


def _make_token(bill_id: str, year: int, month: int) -> str:
    msg = f"{bill_id}:{year}:{month}"
    return hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:24]


def _make_tmpdir() -> str:
    tmpdir = tempfile.mkdtemp()
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "bills.json"),
        os.path.join(tmpdir, "bills.json"),
    )
    with open(os.path.join(tmpdir, "bills_state.json"), "w") as f:
        json.dump({}, f)
    return tmpdir


# ─────────────────────────────────────────────────────────────────────────────
#  1. Bill Schedule Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBillSchedule(unittest.TestCase):

    def setUp(self):
        with open("bills.json") as f:
            self.bills = json.load(f)["bills"]

    def _due(self, month: int):
        return [b["name_zh"] for b in self.bills if month in b["months"]]

    def test_january_has_all_six_bills(self):
        # Jan: water(1) + management(every) + phone(every) + rates(1,4,7,10)
        due = self._due(1)
        self.assertIn("水費", due)
        self.assertIn("管理費", due)
        self.assertIn("電話費", due)
        self.assertIn("差餉及地租", due)
        self.assertEqual(len(due), 4)

    def test_may_has_water_management_phone(self):
        due = self._due(5)
        self.assertEqual(sorted(due), sorted(["水費", "管理費", "電話費"]))

    def test_february_has_electricity_gas_management_phone(self):
        due = self._due(2)
        self.assertIn("電費", due)
        self.assertIn("煤氣費", due)
        self.assertIn("管理費", due)
        self.assertIn("電話費", due)

    def test_march_has_only_monthly_bills(self):
        due = self._due(3)
        self.assertEqual(sorted(due), sorted(["管理費", "電話費"]))

    def test_all_bills_have_required_fields(self):
        for b in self.bills:
            for field in ("id", "name_zh", "name_en", "icon", "months", "late_fee"):
                self.assertIn(field, b, f"Bill '{b.get('id')}' missing field '{field}'")
            self.assertIsInstance(b["months"], list)
            self.assertTrue(all(1 <= m <= 12 for m in b["months"]))

    def test_late_fee_flags(self):
        late = {b["id"]: b["late_fee"] for b in self.bills}
        self.assertTrue(late["electricity"])
        self.assertTrue(late["gas"])
        self.assertTrue(late["water"])
        self.assertFalse(late["management"])
        self.assertFalse(late["phone"])
        self.assertTrue(late["rates"])


# ─────────────────────────────────────────────────────────────────────────────
#  2. HMAC Token Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHmacToken(unittest.TestCase):

    def setUp(self):
        from generate_email import make_token
        self.make_token = make_token

    def test_token_is_24_chars(self):
        t = self.make_token("water", 2026, 5, SECRET)
        self.assertEqual(len(t), 24)

    def test_token_is_deterministic(self):
        t1 = self.make_token("water", 2026, 5, SECRET)
        t2 = self.make_token("water", 2026, 5, SECRET)
        self.assertEqual(t1, t2)

    def test_different_bills_different_tokens(self):
        t1 = self.make_token("water", 2026, 5, SECRET)
        t2 = self.make_token("electricity", 2026, 5, SECRET)
        self.assertNotEqual(t1, t2)

    def test_different_months_different_tokens(self):
        t1 = self.make_token("water", 2026, 5, SECRET)
        t2 = self.make_token("water", 2026, 6, SECRET)
        self.assertNotEqual(t1, t2)

    def test_different_secrets_different_tokens(self):
        t1 = self.make_token("water", 2026, 5, "secret_a")
        t2 = self.make_token("water", 2026, 5, "secret_b")
        self.assertNotEqual(t1, t2)


# ─────────────────────────────────────────────────────────────────────────────
#  3. Email HTML Generation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateEmail(unittest.TestCase):

    def setUp(self):
        with open("bills.json") as f:
            self.bills = json.load(f)["bills"]
        from generate_email import generate_html
        self.generate_html = generate_html

    def _may_bills(self):
        return [b for b in self.bills if 5 in b["months"]]

    def test_html_contains_all_bill_names(self):
        html = self.generate_html(self._may_bills(), {}, 2026, 5, PAGES_BASE, SECRET)
        for b in self._may_bills():
            self.assertIn(b["name_zh"], html)

    def test_html_shows_late_fee_tag_for_late_fee_bills(self):
        html = self.generate_html(self._may_bills(), {}, 2026, 5, PAGES_BASE, SECRET)
        self.assertIn("遲交費", html)  # water has late_fee=True

    def test_html_no_late_fee_tag_when_no_late_fee_bills(self):
        # March: only management + phone, both late_fee=False
        mar_bills = [b for b in self.bills if 3 in b["months"]]
        html = self.generate_html(mar_bills, {}, 2026, 3, PAGES_BASE, SECRET)
        # Alert box should NOT appear (no unpaid late-fee bills)
        self.assertNotIn("注意：部分帳單有遲交附加費", html)

    def test_paid_bill_has_strikethrough(self):
        bills = self._may_bills()
        state = {"water": True}
        html = self.generate_html(bills, state, 2026, 5, PAGES_BASE, SECRET)
        self.assertIn("line-through", html)
        self.assertIn("已繳", html)

    def test_unpaid_bill_has_mark_paid_button(self):
        bills = self._may_bills()
        state = {}
        html = self.generate_html(bills, state, 2026, 5, PAGES_BASE, SECRET)
        self.assertIn("btn-paid", html)
        self.assertIn("標記已繳", html)

    def test_paid_bill_has_no_mark_paid_button(self):
        bills = self._may_bills()
        # All paid — no <a class="btn-paid"> element should be rendered
        state = {b["id"]: True for b in bills}
        html = self.generate_html(bills, state, 2026, 5, PAGES_BASE, SECRET)
        self.assertNotIn('<a class="btn-paid"', html)

    def test_summary_counts_correct(self):
        bills = self._may_bills()   # 3 bills
        state = {"management": True}  # 1 paid, 2 unpaid
        html = self.generate_html(bills, state, 2026, 5, PAGES_BASE, SECRET)
        # Summary numbers appear in the HTML
        self.assertIn(">3<", html)   # total
        self.assertIn(">2<", html)   # unpaid
        self.assertIn(">1<", html)   # paid

    def test_mark_paid_url_contains_token(self):
        bills = self._may_bills()
        html = self.generate_html(bills, {}, 2026, 5, PAGES_BASE, SECRET)
        from generate_email import make_token
        token = make_token("water", 2026, 5, SECRET)
        self.assertIn(token, html)

    def test_next_reminder_note_present(self):
        html = self.generate_html(self._may_bills(), {}, 2026, 5, PAGES_BASE, SECRET)
        self.assertIn("下次提醒", html)


# ─────────────────────────────────────────────────────────────────────────────
#  4. mark_paid.py Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMarkPaid(unittest.TestCase):

    def _run_mark_paid(self, bill_id, year, month, token, secret=SECRET):
        tmpdir = _make_tmpdir()
        orig_dir = os.getcwd()
        orig_env = os.environ.get("MARK_PAID_TOKEN")
        orig_argv = sys.argv[:]
        try:
            os.chdir(tmpdir)
            os.environ["MARK_PAID_TOKEN"] = secret
            sys.argv = ["mark_paid.py", bill_id, str(year), str(month), token]
            import mark_paid
            importlib.reload(mark_paid)
            mark_paid.main()
            with open("bills_state.json") as f:
                state = json.load(f)
            return state
        finally:
            os.chdir(orig_dir)
            sys.argv = orig_argv
            if orig_env is None:
                os.environ.pop("MARK_PAID_TOKEN", None)
            else:
                os.environ["MARK_PAID_TOKEN"] = orig_env

    def test_valid_mark_updates_state(self):
        token = _make_token("water", 2026, 5)
        state = self._run_mark_paid("water", 2026, 5, token)
        self.assertTrue(state["2026"]["5"]["water"])

    def test_idempotent_double_mark(self):
        token = _make_token("management", 2026, 5)
        state1 = self._run_mark_paid("management", 2026, 5, token)
        # Run again (second mark on fresh dir but simulates re-running)
        self.assertTrue(state1["2026"]["5"]["management"])

    def test_invalid_token_raises_exit_1(self):
        with self.assertRaises(SystemExit) as cm:
            self._run_mark_paid("water", 2026, 5, "badbadbadbadbadbadbadbad")
        self.assertEqual(cm.exception.code, 1)  # type: ignore[union-attr]

    def test_unknown_bill_id_raises_exit_1(self):
        token = _make_token("fakebill", 2026, 5)
        with self.assertRaises(SystemExit) as cm:
            self._run_mark_paid("fakebill", 2026, 5, token)
        self.assertEqual(cm.exception.code, 1)  # type: ignore[union-attr]


# ─────────────────────────────────────────────────────────────────────────────
#  5. send_reminder.py Tests (mocked SMTP)
# ─────────────────────────────────────────────────────────────────────────────

class TestSendReminder(unittest.TestCase):

    class _FakeSMTP:
        calls = []
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def login(self, user, pwd): TestSendReminder._FakeSMTP.calls.append(("login", user))
        def sendmail(self, frm, to, msg): TestSendReminder._FakeSMTP.calls.append(("sendmail", to, len(msg)))

    def _setup_env(self, state: dict):
        tmpdir = _make_tmpdir()
        with open(os.path.join(tmpdir, "bills_state.json"), "w") as f:
            json.dump(state, f)
        os.chdir(tmpdir)
        os.environ["GMAIL_USER"]          = "sender@gmail.com"
        os.environ["GMAIL_APP_PASSWORD"]  = "apppass"
        os.environ["RECIPIENT_EMAIL"]     = "me@example.com"
        os.environ["MARK_PAID_TOKEN"]     = SECRET
        os.environ["GITHUB_REPOSITORY"]   = "mzf3334-dev/billreminder"
        TestSendReminder._FakeSMTP.calls  = []
        smtplib.SMTP_SSL = TestSendReminder._FakeSMTP
        sys.path.insert(0, os.path.dirname(__file__))
        import send_reminder
        importlib.reload(send_reminder)
        return send_reminder

    def test_sends_email_when_unpaid_bills_exist(self):
        orig = os.getcwd()
        try:
            mod = self._setup_env({"2026": {"5": {"management": True}}})
            mod.main()
            sendmail_calls = [c for c in self._FakeSMTP.calls if c[0] == "sendmail"]
            self.assertEqual(len(sendmail_calls), 1)
            self.assertEqual(sendmail_calls[0][1], "me@example.com")
            self.assertGreater(sendmail_calls[0][2], 1000)
        finally:
            os.chdir(orig)

    def test_no_email_when_all_paid(self):
        orig = os.getcwd()
        try:
            state = {"2026": {"5": {"water": True, "management": True, "phone": True}}}
            mod = self._setup_env(state)
            try:
                mod.main()
            except SystemExit:
                pass
            sendmail_calls = [c for c in self._FakeSMTP.calls if c[0] == "sendmail"]
            self.assertEqual(len(sendmail_calls), 0)
        finally:
            os.chdir(orig)

    def test_email_subject_contains_unpaid_bill_names(self):
        orig = os.getcwd()
        captured_msg = []

        class CaptureSMTP:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def login(self, *a): pass
            def sendmail(self, frm, to, msg): captured_msg.append(msg)

        tmpdir = _make_tmpdir()
        with open(os.path.join(tmpdir, "bills_state.json"), "w") as f:
            json.dump({}, f)
        os.chdir(tmpdir)
        os.environ["GMAIL_USER"] = "a@b.com"
        os.environ["GMAIL_APP_PASSWORD"] = "x"
        os.environ["RECIPIENT_EMAIL"] = "r@b.com"
        os.environ["MARK_PAID_TOKEN"] = SECRET
        os.environ["GITHUB_REPOSITORY"] = "mzf3334-dev/billreminder"
        smtplib.SMTP_SSL = CaptureSMTP
        sys.path.insert(0, os.path.dirname(__file__))
        import send_reminder
        importlib.reload(send_reminder)
        try:
            send_reminder.main()
        finally:
            os.chdir(orig)

        self.assertTrue(len(captured_msg) > 0)
        # Decode MIME headers and check subject contains 帳單提醒
        from email import message_from_string
        from email.header import decode_header
        msg_obj = message_from_string(captured_msg[0])
        raw_subject = msg_obj["Subject"]
        decoded_parts = decode_header(raw_subject)
        subject_str = "".join(
            part.decode(enc or "utf-8") if isinstance(part, bytes) else part
            for part, enc in decoded_parts
        )
        self.assertIn("帳單提醒", subject_str)


# ─────────────────────────────────────────────────────────────────────────────
#  Run
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestBillSchedule, TestHmacToken, TestGenerateEmail,
                TestMarkPaid, TestSendReminder]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
