import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mailbox_worker as worker
import relay
from answers import write_json


class FolderWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "slack-inbox").mkdir()
        (self.root / "answer-outbox").mkdir()
        self.config = dict(enabled=True, mailbox_enabled=False, owner_slack_user_id="UOWNER", workspace_id="TFIXTURE", channel_ids=["CFIXTURE"],
                           thread_id="00000000-0000-0000-0000-000000000001", state_root=str(self.root / "state"), runtime_file=str(self.root / "RUNBOOK.md"),
                           file_inbox=str(self.root / "slack-inbox"), answer_root=str(self.root), queue_command=["codex"], poll_seconds=10)
        self.export_config = dict(self.config, inbox_root=str(self.root))
        self.message = dict(workspace_id="TFIXTURE", channel_id="CFIXTURE", sender_user_id="UPEER", sender_is_bot=False, event_type="message", message_kind="question",
                            message_ts="1700000000.000001", thread_ts="1699999999.000001", text="Where are the outputs?", source_link="https://example.invalid/source")
        self.sent = []

    def no_network(self, *args):
        raise AssertionError("A file-only worker must never call GitHub")

    def submit(self, command):
        self.sent.append(command)
        return "queued fixture"

    def tick(self):
        return worker.tick(self.config, self.no_network, self.submit)

    def test_empty_folder_needs_no_network_or_model(self):
        result = self.tick()
        self.assertFalse(result["queued"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(self.sent, [])

    def test_export_then_native_notification_once(self):
        first = relay.export_message(self.message, self.export_config)
        saved = relay.read_json(first["path"])
        self.assertEqual(saved["intended_consumer"], "codex-router")
        self.assertEqual(saved["thread_ts"], self.message["thread_ts"])
        self.assertTrue(self.tick()["queued"])
        self.assertFalse(self.tick()["queued"])
        self.assertEqual(len(self.sent), 1)
        self.assertNotIn(self.message["text"], self.sent[0][-1])
        self.assertEqual(relay.export_message(self.message, self.export_config)["status"], "already_exported")

    def test_owner_bot_and_loop_never_export(self):
        for change in ({"sender_user_id": "UOWNER"}, {"sender_is_bot": True}, {"text": "Relay answer: example"}):
            self.assertEqual(relay.export_message({**self.message, **change}, self.export_config)["status"], "skipped")
        self.assertFalse(self.tick()["queued"])

    def test_handwritten_owner_file_cannot_wake(self):
        result = relay.export_message(self.message, self.export_config)
        item = relay.read_json(result["path"])
        write_json(Path(result["path"]), {**item, "sender_user_id": "UOWNER"})
        self.assertFalse(self.tick()["queued"])

    def test_partial_temp_ignored_bad_json_does_not_block_valid_file(self):
        (self.root / "slack-inbox" / "partial.tmp").write_text("{")
        (self.root / "slack-inbox" / ("0" * 64 + ".json")).write_text("{")
        relay.export_message(self.message, self.export_config)
        result = self.tick()
        self.assertTrue(result["queued"])
        self.assertTrue(result["errors"])

    def test_receipts_and_other_folder_changes_do_not_wake(self):
        (self.root / "unwatched").mkdir()
        (self.root / "unwatched" / "receipt.json").write_text("{}")
        self.assertFalse(self.tick()["queued"])

    def test_answer_file_wakes_without_incoming_slack(self):
        (self.root / "answer-outbox" / ("b" * 64 + ".json")).write_text("{}")
        self.assertTrue(self.tick()["queued"])
        self.assertFalse(self.tick()["queued"])

    def test_only_matching_processed_receipts_suppress_export(self):
        exported = relay.export_message(self.message, self.export_config)
        receipts = self.root / "slack-receipts"
        receipts.mkdir()
        self.config["file_receipts"] = str(receipts)
        path = receipts / Path(exported["path"]).name
        write_json(path, dict(source_id=exported["source_id"], status="processed"))
        self.assertFalse(self.tick()["queued"])
        write_json(path, dict(source_id="OTHER", status="processed"))
        self.assertTrue(self.tick()["queued"])

    def test_known_probe_is_distinct_from_slack(self):
        directory = self.root / "probes"
        directory.mkdir()
        self.config["probe_directory"] = str(directory)
        probe_id = "00000000-0000-0000-0000-000000000002"
        write_json(directory / (probe_id + ".json"), dict(kind="worker_probe", probe_id=probe_id, created_at=worker.now()))
        result = self.tick()
        batch = relay.read_json(self.root / "state" / "batches" / (result["batch_id"] + ".json"))
        self.assertEqual(batch["events"][0]["kind"], "worker_probe")
        self.assertEqual(batch["events"][0]["probe_id"], probe_id)
        self.assertFalse(self.tick()["queued"])


if __name__ == "__main__":
    unittest.main()
