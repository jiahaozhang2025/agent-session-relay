from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import receiver_rotation as rotation
import mailbox_worker as worker
from relay import read_json

OLD = "00000000-0000-0000-0000-000000000001"
NEW = "00000000-0000-0000-0000-000000000002"
AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


class RotationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "rotation.json"
        self.init()

    def init(self):
        return rotation.change(self.path, "init", current=OLD, automation_id="existing-job", at=AT)

    def begin(self):
        return rotation.change(self.path, "begin", current=OLD, at=AT + timedelta(hours=24))["pending"]["rotation_id"]

    def bind(self):
        rid = self.begin()
        rotation.change(self.path, "bind", current=OLD, successor=NEW, rotation_id=rid, at=AT + timedelta(hours=24))
        return rid

    def test_exact_24_hour_boundary(self):
        state = read_json(self.path)
        self.assertEqual(rotation.status(state, AT + timedelta(hours=24, microseconds=-1))["status"], "not_due")
        self.assertEqual(rotation.status(state, AT + timedelta(hours=24))["status"], "due")
        self.assertEqual(rotation.change(self.path, "begin", current=OLD, at=AT)["status"], "not_due")

    def test_force_supports_owner_requested_immediate_rotation(self):
        self.assertEqual(rotation.change(self.path, "begin", current=OLD, force=True, at=AT)["status"], "in_progress")

    def test_pending_creation_survives_restart_and_never_duplicates(self):
        rid = self.begin()
        self.assertEqual(self.begin(), rid)
        self.assertIsNone(rotation.due_event({"rotation_state_file": str(self.path), "thread_id": OLD}, AT + timedelta(days=3)))

    def test_cannot_replace_state_or_reuse_same_chat(self):
        with self.assertRaises(ValueError):
            self.init()
        rid = self.begin()
        with self.assertRaises(ValueError):
            rotation.change(self.path, "bind", current=OLD, successor=OLD, rotation_id=rid)

    def test_activation_requires_matching_ready_worker_and_automation(self):
        rid = self.bind()
        with self.assertRaises(ValueError):
            rotation.change(self.path, "activate", current=OLD, rotation_id=rid, evidence={})
        self.assertEqual(read_json(self.path)["current_thread_id"], OLD)

    def test_verified_lifecycle_resets_age_and_preserves_retirement(self):
        rid = self.bind()
        evidence = dict(ready_thread_id=NEW, worker_thread_id=NEW, automation_thread_id=NEW,
                        automation_id="existing-job", automation_status="ACTIVE")
        rotation.change(self.path, "activate", current=OLD, rotation_id=rid, evidence=evidence, at=AT + timedelta(hours=24, minutes=2))
        self.assertEqual(read_json(self.path)["expires_at"], (AT + timedelta(hours=48)).isoformat())
        with self.assertRaises(ValueError):
            rotation.change(self.path, "begin", current=OLD)
        with self.assertRaises(ValueError):
            rotation.change(self.path, "complete", current=NEW, rotation_id=rid, evidence={"archived": True})
        rotation.change(self.path, "complete", current=NEW, rotation_id=rid,
                        evidence={"archived_thread_id": OLD, "archived": True}, at=AT + timedelta(hours=24, minutes=3))
        self.assertEqual(len(read_json(self.path)["history"]), 1)
        self.assertIsNone(read_json(self.path)["pending"])

    def test_lock_and_target_mismatch_fail_closed(self):
        self.path.with_suffix(".json.lock").write_text("live owner")
        with self.assertRaises(FileExistsError):
            self.begin()
        with self.assertRaises(ValueError):
            rotation.due_event({"rotation_state_file": str(self.path), "thread_id": NEW})

    def test_invalid_expiry_or_naive_timestamp_rejected(self):
        state = read_json(self.path)
        state["expires_at"] = AT.isoformat()
        with self.assertRaises(ValueError):
            rotation.status(state)
        with self.assertRaises(ValueError):
            rotation.timestamp("2026-01-01T00:00:00")

    def test_due_worker_queues_once_without_network(self):
        root = self.path.parent
        config = dict(enabled=True, mailbox_enabled=False, owner_slack_user_id="UOWNER", workspace_id="TFIXTURE",
                      channel_ids=["CFIXTURE"], thread_id=OLD, state_root=str(root / "worker"),
                      runtime_file=str(root / "RUNBOOK.md"), queue_command=["codex"], poll_seconds=10,
                      rotation_state_file=str(self.path))
        sent = []
        def no_network(*args):
            self.fail("rotation has no network transport")
        first = worker.tick(config, no_network, lambda command: sent.append(command) or "queued")
        self.assertTrue(first["queued"])
        batch = read_json(root / "worker" / "batches" / (first["batch_id"] + ".json"))
        self.assertEqual(batch["events"][0]["kind"], "receiver_rotation_due")
        worker.acknowledge(config, first["batch_id"])
        self.assertFalse(worker.tick(config, no_network, lambda command: sent.append(command))["queued"])
        self.assertEqual(len(sent), 1)
        config["thread_id"] = NEW
        self.assertTrue(worker.tick(config, no_network, lambda command: self.fail("stale target"))["errors"])


if __name__ == "__main__":
    unittest.main()
