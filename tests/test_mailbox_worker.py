import base64
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mailbox_worker as worker
from answers import write_json
from relay import read_json


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = dict(enabled=True, repository="fixture/mailbox", expected_cli_login="local-fixture", workspace_id="TFIXTURE", channel_ids=["CFIXTURE"],
                           thread_id="00000000-0000-0000-0000-000000000001", state_root=str(self.root / "state"), runtime_file=str(self.root / "RUNBOOK.md"),
                           answer_root=str(self.root), gh_command=["gh"], queue_command=["codex"], poll_seconds=60)
        (self.root / "answer-outbox").mkdir()
        self.event = dict(schema_version=1, workspace_id="TFIXTURE", channel_id="CFIXTURE", message_ts="1700000000.000001", thread_ts="1699999999.000001")
        self.path = "wake/CFIXTURE_1700000000.000001.json"
        self.events = True
        self.private = True
        self.sent = []

    def request(self, config, endpoint):
        if endpoint == "user": return {"login": "local-fixture"}
        if endpoint == "repos/fixture/mailbox": return dict(private=self.private, full_name="fixture/mailbox", default_branch="main")
        if "/git/trees/" in endpoint:
            return dict(truncated=False, tree=[dict(path=self.path, type="blob", size=200, sha="a" * 40)] if self.events else [])
        import json
        return dict(encoding="base64", content=base64.b64encode(json.dumps(self.event).encode()).decode())

    def submit(self, command):
        self.sent.append(command)
        return "queued fixture"

    def tick(self):
        return worker.tick(self.config, self.request, self.submit)

    def test_queue_once_and_restart_does_not_repeat(self):
        result = self.tick()
        self.assertTrue(result["queued"])
        self.assertFalse(self.tick()["queued"])
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][1:4], ["queue", "--thread", self.config["thread_id"]])
        self.assertNotIn(self.event["message_ts"], self.sent[0][-1])

    def test_no_model_call_while_empty(self):
        self.events = False
        self.assertFalse(self.tick()["queued"])
        self.assertEqual(self.sent, [])

    def test_source_metadata_only_and_exact_scope(self):
        for change in ({"text": "Never store Slack content here"}, {"workspace_id": "OTHER"}, {"message_ts": "1; execute"}, {"schema_version": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                worker.event_check({**self.event, **change}, self.path, self.config)
        with self.assertRaises(ValueError):
            worker.event_check(self.event, "wake/OTHER_1700000000.000001.json", self.config)

    def test_public_mailbox_rejected(self):
        self.private = False
        result = self.tick()
        self.assertTrue(result["errors"])
        self.assertFalse(result["queued"])

    def test_account_mismatch_rejected(self):
        self.config["expected_cli_login"] = "different"
        self.assertTrue(self.tick()["errors"])
        self.assertEqual(self.sent, [])

    def test_incomplete_tree_never_claims_complete(self):
        def request(config, endpoint):
            value = self.request(config, endpoint)
            if "/git/trees/" in endpoint: value["truncated"] = True
            return value
        self.assertTrue(worker.tick(self.config, request, self.submit)["errors"])
        self.assertEqual(self.sent, [])

    def test_queue_timeout_stays_uncertain_without_retry(self):
        def timeout(command):
            self.sent.append(command)
            raise subprocess.TimeoutExpired(command, 45)
        result = worker.tick(self.config, self.request, timeout)
        self.assertTrue(result["errors"])
        self.tick()
        self.assertEqual(len(self.sent), 1)
        state = read_json(self.root / "state" / "worker-state.json")
        self.assertEqual(next(iter(state["batches"].values()))["status"], "submission_uncertain")

    def test_native_receipt_separate_from_queue_acceptance(self):
        result = self.tick()
        state = read_json(self.root / "state" / "worker-state.json")
        self.assertEqual(state["batches"][result["batch_id"]]["status"], "queued_unconfirmed")
        worker.acknowledge(self.config, result["batch_id"])
        self.tick()
        state = read_json(self.root / "state" / "worker-state.json")
        self.assertEqual(state["batches"][result["batch_id"]]["status"], "received")

    def test_local_answer_hints_independent_of_mailbox_failure(self):
        self.private = False
        (self.root / "answer-outbox" / ("a" * 64 + ".json")).write_text("{}")
        result = self.tick()
        self.assertTrue(result["queued"])
        self.assertTrue(result["errors"])
        self.assertFalse(self.tick()["queued"])

    def test_missing_answer_mount_is_a_failure(self):
        self.events = False
        self.config["answer_root"] = str(self.root / "missing")
        self.assertTrue(self.tick()["errors"])
        self.assertEqual(self.sent, [])

    def test_changed_source_ids_wake_but_duplicates_do_not(self):
        self.tick()
        self.event.update(message_ts="1700000000.000002")
        self.path = "wake/CFIXTURE_1700000000.000002.json"
        self.assertTrue(self.tick()["queued"])
        self.assertFalse(self.tick()["queued"])
        self.assertEqual(len(self.sent), 2)

    def test_unsafe_config_rejected_before_any_call(self):
        for change in ({"enabled": False}, {"repository": "a/../b"}, {"queue_command": "codex"}, {"poll_seconds": 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                worker.tick({**self.config, **change}, self.request, self.submit)


if __name__ == "__main__":
    unittest.main()
