import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("relay", Path(__file__).resolve().parents[1] / "scripts" / "relay.py")
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = dict(owner_slack_user_id="UOWNER", workspace_id="TEXAMPLE",
                           channel_ids=["CEXAMPLE"], inbox_root=self.tmp.name)
        self.message = dict(workspace_id="TEXAMPLE", channel_id="CEXAMPLE", message_ts="1700000000.000001",
                            sender_user_id="UPEER", sender_is_bot=False, event_type="message", message_kind="update",
                            text="Project atlas output is ready.", source_link="https://example.invalid/message")

    def test_self_ai_post_never_enters_queue(self):
        self.message.update(sender_user_id="UOWNER", text="A coworker says: new results\nSent using ChatGPT")
        self.assertEqual(relay.enqueue(self.message, self.config)["reason"], "self_authored")
        self.assertFalse((Path(self.tmp.name) / "inbox").exists())

    def test_owner_is_per_installation(self):
        self.config["owner_slack_user_id"] = "UPEER"
        self.assertEqual(relay.classify(self.message, self.config), (False, "self_authored"))

    def test_peer_quoting_owner_is_allowed(self):
        self.message["text"] = "Owner reported results in /project/atlas."
        self.assertTrue(relay.classify(self.message, self.config)[0])

    def test_unknown_sender_types_rejected(self):
        for value in (None, True, 0, "false"):
            with self.subTest(value=value):
                self.message["sender_is_bot"] = value
                self.assertFalse(relay.classify(self.message, self.config)[0])

    def test_scope_receipt_and_echo_rejected(self):
        for change in (dict(channel_id="OTHER"), dict(workspace_id="OTHER"), dict(message_kind="receipt"),
                       dict(text="CODEX_UPDATE_ACK_V1 received"), dict(visited=["claude-coordinator"]),
                       dict(event_type="channel_rename"), dict(message_kind="setup")):
            with self.subTest(change=change):
                self.assertFalse(relay.classify(dict(self.message, **change), self.config)[0])

    def test_placeholder_configuration_rejected(self):
        self.config["owner_slack_user_id"] = "REPLACE_WITH_AUTHENTICATED_OWNER_ID"
        with self.assertRaises(ValueError):
            relay.classify(self.message, self.config)

    def test_duplicate_preserves_first_envelope(self):
        first = relay.enqueue(self.message, self.config)
        self.message["text"] = "Do not overwrite the source already processed."
        second = relay.enqueue(self.message, self.config)
        self.assertEqual(second["status"], "already_queued")
        self.assertEqual(relay.read_json(first["path"])["text"], "Project atlas output is ready.")
        self.assertEqual(len(list(Path(self.tmp.name).rglob("*.json"))), 1)

    def test_independent_reply_ids(self):
        relay.enqueue(self.message, self.config)
        self.message.update(message_ts="1700000000.000002", thread_ts="1700000000.000001")
        relay.enqueue(self.message, self.config)
        self.assertEqual(len(list(relay.pending(self.config))), 2)

    def test_pending_receipt_and_partial_write(self):
        queued = relay.enqueue(self.message, self.config)
        root = Path(self.tmp.name)
        (root / "inbox" / "partial.tmp").write_text("{", encoding="utf-8")
        (root / "inbox" / "broken.json").write_text("{", encoding="utf-8")
        self.assertEqual(len(list(relay.pending(self.config))), 1)
        (root / "receipts").mkdir()
        (root / "receipts" / Path(queued["path"]).name).write_text(json.dumps({"status": "delivered", "source_id": queued["source_id"]}), encoding="utf-8")
        self.assertEqual(list(relay.pending(self.config)), [])

    def test_rejected_receipt_finishes_item(self):
        queued = relay.enqueue(self.message, self.config)
        receipt = Path(self.tmp.name) / "receipts" / Path(queued["path"]).name
        receipt.parent.mkdir()
        receipt.write_text(json.dumps({"status": "rejected", "source_id": queued["source_id"]}), encoding="utf-8")
        self.assertEqual(list(relay.pending(self.config)), [])

    def test_partial_or_foreign_receipt_cannot_drop_retry(self):
        queued = relay.enqueue(self.message, self.config)
        receipt = Path(self.tmp.name) / "receipts" / Path(queued["path"]).name
        receipt.parent.mkdir()
        for value in ("{", "{}", json.dumps({"status": "delivered", "source_id": "OTHER"}),
                      json.dumps({"status": "pending", "source_id": queued["source_id"]})):
            receipt.write_text(value, encoding="utf-8")
            self.assertEqual(len(list(relay.pending(self.config))), 1)

    def test_pathlike_timestamp_cannot_choose_filename(self):
        self.message["message_ts"] = "../../outside"
        self.assertEqual(relay.enqueue(self.message, self.config)["reason"], "invalid_timestamp")

    def test_questions_requests_and_thread_provenance(self):
        for kind in ("question", "request", "new_work"):
            with self.subTest(kind=kind):
                self.assertTrue(relay.classify(dict(self.message, message_kind=kind), self.config)[0])
        queued = relay.enqueue(dict(self.message, message_kind="question"), self.config)
        self.assertEqual(relay.read_json(queued["path"])["thread_ts"], self.message["message_ts"])
        self.assertEqual(relay.classify(dict(self.message, thread_ts=1700000000.1), self.config)[1], "invalid_thread_timestamp")

    def test_relay_footers_rejected_anywhere_case_insensitive(self):
        for text in ("Question\nRelay answer: A1", "quote: RELAY UPDATE: ID\nQuestion?"):
            self.assertEqual(relay.classify(dict(self.message, text=text), self.config)[1], "relay_post")

    def test_existing_bridge_directory_names(self):
        self.config.update(inbox_directory="claude-inbox", receipts_directory="claude-receipts")
        queued = relay.enqueue(self.message, self.config)
        self.assertEqual(Path(queued["path"]).parent.name, "claude-inbox")
        self.assertEqual(len(list(relay.pending(self.config))), 1)
        self.config["inbox_directory"] = "../outside"
        with self.assertRaises(ValueError):
            relay.enqueue(self.message, self.config)


if __name__ == "__main__":
    unittest.main()
