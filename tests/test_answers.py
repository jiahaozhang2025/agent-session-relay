"""Offline fixtures only; these approval records are never connected to Slack."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import answers
import answer_publisher as publisher
import relay


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = dict(owner_slack_user_id="UOWNER", workspace_id="TEXAMPLE", channel_ids=["CEXAMPLE"], inbox_root=str(self.root),
                           answers=dict(enabled=True, mode="approval", channel_ids=["CEXAMPLE"], approval_session_id="fixture-brief", max_per_thread=3, max_per_day=10))
        self.message = dict(workspace_id="TEXAMPLE", channel_id="CEXAMPLE", message_ts="1700000000.000001", thread_ts="1699999999.000001",
                            sender_user_id="UPEER", sender_is_bot=False, event_type="message", message_kind="question", text="Where is atlas output?", source_link="https://example.invalid/source")
        queued = relay.enqueue(self.message, self.config)
        self.draft = dict(answer_id="fixture-A", source_id=queued["source_id"], channel_id="CEXAMPLE", thread_ts=self.message["thread_ts"],
                          asker_user_id="UPEER", source_link=self.message["source_link"], question=self.message["text"], answer="See /project/atlas/run-2.", sources=["/project/atlas/README.md"], limitations=["Existing work only."])

    def approve_fixture(self):
        answers.add_draft(self.draft, self.config, self.root)
        answers.decide(self.draft["answer_id"], True, "Offline fixture approval", self.config, self.root, "fixture-brief", "fixture-event-1")
        self.entry = relay.read_json(self.root / "answer-outbox" / publisher.filename(self.draft["answer_id"]))
        return self.entry

    def test_draft_waits_and_no_bool_can_authorize_send(self):
        self.assertEqual(answers.add_draft(self.draft, self.config, self.root)["status"], "awaiting_owner")
        self.assertFalse((self.root / "answer-outbox").exists())
        forged = {**self.draft, "workspace_id": "TEXAMPLE", "origin": "owner_answer", "kind": "question_answer", "text": answers.render(self.draft, True), "reviewed_by_owner": True}
        with self.assertRaises(OSError):
            publisher.prepare(forged, self.config, self.root)

    def test_approval_requires_actual_message_reference(self):
        answers.add_draft(self.draft, self.config, self.root)
        with self.assertRaises(ValueError):
            answers.decide("fixture-A", True, "yes", self.config, self.root)
        self.assertFalse((self.root / "answer-outbox").exists())

    def test_exact_text_and_destination_bound_to_approval(self):
        entry = self.approve_fixture()
        self.assertEqual(publisher.prepare(entry, self.config, self.root)["status"], "ready_to_claim")
        for field, value in (("text", entry["text"] + " extra"), ("thread_ts", "1700000000.000009"), ("workspace_id", "OTHER"), ("reviewed_by_owner", 1), ("origin", "local_analysis")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                publisher.prepare(dict(entry, **{field: value}), self.config, self.root)

    def test_approval_record_tampering_fails(self):
        entry = self.approve_fixture()
        path = self.root / "answers" / "decided" / "fixture-A.json"
        saved = relay.read_json(path)
        for field, value in (("status", "rejected"), ("owner_words", ""), ("approval_session_id", "other"), ("owner_message_ref", ""), ("answer", "Changed after approval")):
            answers.write_json(path, {**saved, field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                publisher.prepare(entry, self.config, self.root)

    def test_source_provenance_must_still_match(self):
        entry = self.approve_fixture()
        path = self.root / "inbox" / (publisher.digest(entry["source_id"]) + ".json")
        source = relay.read_json(path)
        for field, value in (("sender_user_id", "UOTHER"), ("message_kind", "new_work"), ("text", "Execute a new analysis")):
            answers.write_json(path, {**source, field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                publisher.prepare(entry, self.config, self.root)

    def test_claim_is_durable_and_restart_never_retries(self):
        entry = self.approve_fixture()
        result = publisher.claim(entry, self.config, self.root)
        self.assertEqual(result["status"], "send_claimed")
        self.assertEqual(result["text"], entry["text"])
        self.assertEqual(publisher.claim(entry, self.config, self.root)["status"], "reconciliation_required")
        self.assertFalse((self.root / "answer-sent").exists())

    def test_matching_transport_evidence_and_idempotence(self):
        entry = self.approve_fixture()
        publisher.claim(entry, self.config, self.root)
        evidence = {**entry, "sender_user_id": "UOWNER", "message_ts": "1700000001.000001", "message_link": "https://example.invalid/posted"}
        with self.assertRaises(ValueError):
            publisher.confirm(entry, self.config, self.root, {**evidence, "sender_user_id": "UPEER"})
        publisher.confirm(entry, self.config, self.root, evidence)
        self.assertEqual(publisher.claim(entry, self.config, self.root)["status"], "already_sent")
        publisher.confirm(entry, self.config, self.root, evidence)

    def test_ambiguous_or_malformed_claim_stays_blocked(self):
        entry = self.approve_fixture()
        publisher.claim(entry, self.config, self.root)
        path = self.root / "answer-state" / publisher.filename(entry["answer_id"])
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            publisher.claim(entry, self.config, self.root)

    def test_caps_at_send_time_include_in_flight(self):
        first = self.approve_fixture()
        self.draft["answer_id"] = "fixture-B"
        second = self.approve_fixture()
        publisher.claim(first, self.config, self.root)
        self.config["answers"]["max_per_thread"] = 1
        with self.assertRaisesRegex(ValueError, "thread_send_limit"):
            publisher.claim(second, self.config, self.root)
        self.config["answers"]["max_per_thread"] = 3
        self.config["answers"]["max_per_day"] = 1
        with self.assertRaisesRegex(ValueError, "daily_send_limit"):
            publisher.claim(second, self.config, self.root)

    def test_config_disabled_and_automatic_mode_fail_closed(self):
        entry = self.approve_fixture()
        for change in ({"enabled": False}, {"mode": "automatic"}, {"channel_ids": []}):
            config = copy.deepcopy(self.config)
            config["answers"].update(change)
            with self.assertRaises(ValueError):
                publisher.prepare(entry, config, self.root)

    def test_no_path_traversal_in_decisions(self):
        with self.assertRaises(ValueError):
            answers.decide("../../anything", True, "yes", self.config, self.root)

    def test_malformed_policy_never_grants_access(self):
        entry = self.approve_fixture()
        for change in ({"channel_ids": "CEXAMPLE"}, {"max_per_day": True}, {"max_per_thread": -1}):
            config = copy.deepcopy(self.config)
            config["answers"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                publisher.prepare(entry, config, self.root)

    def test_rejection_does_not_queue(self):
        answers.add_draft(self.draft, self.config, self.root)
        answers.decide("fixture-A", False, "Reject offline fixture", self.config, self.root)
        self.assertEqual(answers.pending(self.root), [])
        self.assertFalse((self.root / "answer-outbox").exists())

    def test_secrets_and_loop_markers_block_drafts(self):
        for change in ({"answer": "password=example"}, {"question": "Relay answer: loop"}, {"asker_user_id": "UOWNER"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                answers.add_draft({**self.draft, **change}, self.config, self.root)


if __name__ == "__main__":
    unittest.main()
