"""
Unit tests for the Islamic Prayer Tracker.
Run with:  python -m unittest test_app -v
No Gemini API key or internet is needed: the AI is replaced by a fake client.
"""

import py_compile
import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

import app


class FakeResponse:
    def __init__(self, text):
        self.text = text


def fake_client(text="Salah is the second pillar of Islam.", error=None):
    client = MagicMock()
    if error:
        client.models.generate_content.side_effect = error
    else:
        client.models.generate_content.return_value = FakeResponse(text)
    return client


class BaseDB(unittest.TestCase):
    def setUp(self):
        self.conn = app.get_connection(":memory:")
        app.init_db(self.conn)
        self.uid = app.create_user(self.conn, "Ahmad_1", "1234")
        self.today = date.today()

    def tearDown(self):
        self.conn.close()


class TestSyntax(unittest.TestCase):
    def test_app_compiles(self):
        py_compile.compile("app.py", doraise=True)


class TestValidation(unittest.TestCase):
    def test_username(self):
        self.assertEqual(app.validate_username("  Ali_99 "), "ali_99")
        for bad in ["", "ab", "has space", "x" * 21, "bad;drop", None]:
            with self.assertRaises(ValueError):
                app.validate_username(bad)

    def test_pin(self):
        self.assertEqual(app.validate_pin("1234"), "1234")
        for bad in ["", "123", "123456789", "12ab", None]:
            with self.assertRaises(ValueError):
                app.validate_pin(bad)

    def test_prayer_status_date_note(self):
        self.assertEqual(app.validate_prayer("Fajr"), "Fajr")
        with self.assertRaises(ValueError):
            app.validate_prayer("Witr")
        with self.assertRaises(ValueError):
            app.validate_status("maybe")
        with self.assertRaises(ValueError):
            app.validate_date(date.today() + timedelta(days=10))
        with self.assertRaises(ValueError):
            app.validate_date("2026-01-01")
        with self.assertRaises(ValueError):
            app.validate_note("x" * 201)
        self.assertEqual(app.validate_note("  ok  "), "ok")

    def test_question(self):
        self.assertEqual(app.validate_question("  Why Fajr? "), "Why Fajr?")
        with self.assertRaises(ValueError):
            app.validate_question("hi")
        with self.assertRaises(ValueError):
            app.validate_question("x" * 501)


class TestUsers(BaseDB):
    def test_duplicate_username(self):
        with self.assertRaises(ValueError):
            app.create_user(self.conn, "ahmad_1", "9999")

    def test_pin_is_hashed(self):
        row = self.conn.execute("SELECT pin_hash FROM users WHERE id = ?", (self.uid,)).fetchone()
        self.assertNotIn(b"1234", row["pin_hash"])

    def test_authenticate(self):
        self.assertEqual(app.authenticate(self.conn, "AHMAD_1", "1234"), self.uid)
        self.assertIsNone(app.authenticate(self.conn, "ahmad_1", "0000"))
        self.assertIsNone(app.authenticate(self.conn, "nobody", "1234"))
        self.assertIsNone(app.authenticate(self.conn, "bad name", "1234"))

    def test_users_cannot_see_each_others_records(self):
        other = app.create_user(self.conn, "sara_2", "5678")
        app.set_status(self.conn, self.uid, self.today, "Fajr", app.STATUS_PRAYED)
        self.assertEqual(app.get_day_statuses(self.conn, other, self.today), {})

    def test_sql_injection_is_harmless(self):
        self.assertIsNone(app.authenticate(self.conn, "x' OR '1'='1", "1234"))
        with self.assertRaises(ValueError):
            app.set_status(self.conn, self.uid, self.today, "Fajr'; DROP TABLE users;--", "prayed")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)


class TestTracking(BaseDB):
    def test_set_update_and_clear(self):
        app.set_status(self.conn, self.uid, self.today, "Fajr", app.STATUS_PRAYED)
        self.assertEqual(app.get_day_statuses(self.conn, self.uid, self.today), {"Fajr": "prayed"})
        app.set_status(self.conn, self.uid, self.today, "Fajr", app.STATUS_MISSED, "overslept")
        self.assertEqual(app.get_day_statuses(self.conn, self.uid, self.today), {"Fajr": "missed"})
        count = self.conn.execute("SELECT COUNT(*) FROM prayer_log").fetchone()[0]
        self.assertEqual(count, 1)  # updated, not duplicated
        app.clear_status(self.conn, self.uid, self.today, "Fajr")
        self.assertEqual(app.get_day_statuses(self.conn, self.uid, self.today), {})

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            app.set_status(self.conn, self.uid, self.today, "Fajr", "bad")
        with self.assertRaises(ValueError):
            app.set_status(self.conn, self.uid, self.today + timedelta(days=30), "Fajr", "prayed")

    def test_missed_list_and_make_up(self):
        yesterday = self.today - timedelta(days=1)
        app.set_status(self.conn, self.uid, yesterday, "Asr", app.STATUS_MISSED, "busy")
        missed = app.get_missed(self.conn, self.uid)
        self.assertEqual(len(missed), 1)
        self.assertEqual(missed[0]["note"], "busy")
        app.set_status(self.conn, self.uid, yesterday, "Asr", app.STATUS_MADE_UP, "busy")
        self.assertEqual(app.get_missed(self.conn, self.uid), [])

    def test_delete_all_user_data(self):
        app.set_status(self.conn, self.uid, self.today, "Isha", app.STATUS_PRAYED)
        app.delete_all_user_data(self.conn, self.uid)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM prayer_log").fetchone()[0], 0)


class TestProgress(BaseDB):
    def test_daily_progress(self):
        self.assertEqual(app.daily_progress({}), (0, 5, 0.0))
        self.assertEqual(app.daily_progress({"Fajr": "prayed", "Asr": "made_up"}), (2, 5, 40.0))
        self.assertEqual(app.daily_progress({"Fajr": "missed", "Dhuhr": "prayed"}), (1, 5, 20.0))
        all_five = {p: "prayed" for p in app.PRAYERS}
        self.assertEqual(app.daily_progress(all_five), (5, 5, 100.0))

    def test_every_count_has_a_message(self):
        for n in range(6):
            self.assertIn(n, app.POSITIVE_MESSAGES)

    def test_history_report(self):
        for p in app.PRAYERS:
            app.set_status(self.conn, self.uid, self.today, p, app.STATUS_PRAYED)
        app.set_status(self.conn, self.uid, self.today - timedelta(days=1), "Fajr", app.STATUS_MISSED)
        report = app.history_report(self.conn, self.uid, self.today - timedelta(days=6), self.today)
        self.assertEqual(len(report), 7)
        last = report.iloc[-1]
        self.assertEqual((last["completed"], last["percent"]), (5, 100.0))
        prev = report.iloc[-2]
        self.assertEqual((prev["completed"], prev["missed"]), (0, 1))
        self.assertEqual(report["completed"].sum(), 5)

    def test_history_report_empty_and_bad_range(self):
        report = app.history_report(self.conn, self.uid, self.today - timedelta(days=29), self.today)
        self.assertEqual(len(report), 30)
        self.assertEqual(report["completed"].sum(), 0)
        with self.assertRaises(ValueError):
            app.history_report(self.conn, self.uid, self.today, self.today - timedelta(days=1))

    def test_per_prayer_report(self):
        for i in range(3):
            app.set_status(self.conn, self.uid, self.today - timedelta(days=i), "Fajr", app.STATUS_PRAYED)
        result = app.per_prayer_report(self.conn, self.uid, self.today - timedelta(days=5), self.today)
        fajr = result[result["prayer"] == "Fajr"].iloc[0]
        self.assertEqual((fajr["completed"], fajr["rate"]), (3, 50.0))
        self.assertEqual(len(result), 5)

    def test_streak(self):
        self.assertEqual(app.current_streak(self.conn, self.uid, self.today), 0)
        for d in range(3):
            for p in app.PRAYERS:
                app.set_status(self.conn, self.uid, self.today - timedelta(days=d), p, app.STATUS_PRAYED)
        self.assertEqual(app.current_streak(self.conn, self.uid, self.today), 3)
        # An incomplete today must not erase the streak that ended yesterday
        app.clear_status(self.conn, self.uid, self.today, "Isha")
        self.assertEqual(app.current_streak(self.conn, self.uid, self.today), 2)
        # A gap breaks the streak
        app.clear_status(self.conn, self.uid, self.today - timedelta(days=1), "Asr")
        self.assertEqual(app.current_streak(self.conn, self.uid, self.today), 0)


class TestContent(unittest.TestCase):
    def test_reminders_have_references(self):
        self.assertGreater(len(app.REMINDERS), 5)
        for item in app.REMINDERS:
            self.assertIn(item["type"], ("Quran", "Hadith"))
            self.assertTrue(item["reference"].strip())
            self.assertTrue(item["meaning"].strip())
            if item["type"] == "Quran":
                self.assertTrue(item["arabic"])

    def test_daily_reminder_is_stable(self):
        d = date(2026, 10, 20)
        self.assertEqual(app.daily_reminder(d), app.daily_reminder(d))

    def test_no_invented_reward_numbers(self):
        self.assertIn("known to Allah", app.REWARDS_INTRO)
        for item in app.REWARDS_SOURCES:
            self.assertNotRegex(item["meaning"], r"\d+\s*(times|fold|rewards|good deeds)")


class TestGemini(unittest.TestCase):
    def test_success(self):
        client = fake_client("Fajr is a prayer at dawn.")
        answer = app.ask_gemini("Why is Fajr important?", client=client)
        self.assertEqual(answer, "Fajr is a prayer at dawn.")
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["contents"], "Why is Fajr important?")

    def test_api_error_is_friendly(self):
        client = fake_client(error=RuntimeError("secret internal detail 429"))
        with self.assertRaises(app.AIServiceError) as ctx:
            app.ask_gemini("Why is Fajr important?", client=client)
        self.assertNotIn("secret internal detail", str(ctx.exception))

    def test_empty_answer(self):
        with self.assertRaises(app.AIServiceError):
            app.ask_gemini("Why is Fajr important?", client=fake_client(text="   "))

    def test_missing_key(self):
        with self.assertRaises(app.AIServiceError):
            app.ask_gemini("Why is Fajr important?", api_key=None)

    def test_invalid_question_never_calls_api(self):
        client = fake_client()
        with self.assertRaises(ValueError):
            app.ask_gemini("  ", client=client)
        client.models.generate_content.assert_not_called()

    def test_get_api_key(self):
        self.assertEqual(app.get_api_key({"GEMINI_API_KEY": "abc"}), "abc")

    def test_no_hardcoded_key_in_source(self):
        with open("app.py", encoding="utf-8") as f:
            source = f.read()
        self.assertNotRegex(source, r"AIza[0-9A-Za-z_\-]{20,}")


if __name__ == "__main__":
    unittest.main()
