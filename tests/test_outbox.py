import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("outbox", Path(__file__).resolve().parents[1] / "scripts" / "outbox.py")
outbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outbox)


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.update = dict(update_id="atlas-result-1", source_session_id="SESSION_A", workspace_id="TEXAMPLE",
                           channel_id="CEXAMPLE", origin="local_analysis", kind="analysis_update",
                           summary="Recomputation finished.", output_locations=["/project/atlas/run2"],
                           limitations=["Pilot only"], next_step="Review outputs.")
        self.config = dict(workspace_id="TEXAMPLE", outbound=dict(enabled=True, source_session_ids=["SESSION_A"], channel_ids=["CEXAMPLE"]))

    def test_draft_does_not_enable_publication(self):
        outbox.queue(self.update, self.tmp.name)
        self.assertEqual(outbox.prepare(self.update, {}, self.tmp.name)["reason"], "outbound_disabled")

    def test_payload_cannot_grant_permission(self):
        self.update["approved"] = True
        self.assertFalse(outbox.decision(self.update, {})[0])

    def test_source_and_destination_restricted(self):
        for change in (dict(source_session_id="OTHER"), dict(channel_id="OTHER"), dict(workspace_id="OTHER")):
            self.assertFalse(outbox.decision(dict(self.update, **change), self.config)[0])

    def test_incoming_traffic_cannot_echo(self):
        for change in (dict(origin="external_slack"), dict(incoming_source_id="T:C:1.2"), dict(visited=["codex-router"])):
            with self.assertRaises(ValueError):
                outbox.queue(dict(self.update, **change), self.tmp.name)

    def test_retry_is_same_item_content_cannot_change(self):
        outbox.queue(self.update, self.tmp.name)
        self.assertEqual(outbox.queue(self.update, self.tmp.name)["status"], "already_queued")
        with self.assertRaises(ValueError):
            outbox.queue(dict(self.update, summary="Changed"), self.tmp.name)

    def test_confirmed_receipt_suppresses_duplicate(self):
        receipt = Path(self.tmp.name) / "sent" / outbox.filename(self.update)
        receipt.parent.mkdir()
        receipt.write_text(json.dumps(dict(update_id=self.update["update_id"], workspace_id="TEXAMPLE", channel_id="CEXAMPLE",
                                          status="sent", message_ts="1.2", message_link="https://example.invalid/message")), encoding="utf-8")
        self.assertEqual(outbox.prepare(self.update, self.config, self.tmp.name)["status"], "already_sent")

    def test_draft_or_foreign_receipt_is_not_delivery(self):
        receipt = Path(self.tmp.name) / "sent" / outbox.filename(self.update)
        receipt.parent.mkdir()
        receipt.write_text(json.dumps(dict(update_id=self.update["update_id"], status="sent")), encoding="utf-8")
        self.assertEqual(outbox.prepare(self.update, self.config, self.tmp.name)["status"], "prepared_not_sent")

    def test_prepared_message_has_stable_marker_and_locations(self):
        result = outbox.prepare(self.update, self.config, self.tmp.name)
        self.assertIn("Relay update: atlas-result-1", result["message"])
        self.assertIn("/project/atlas/run2", result["message"])
        self.assertEqual(result["status"], "prepared_not_sent")

    def test_field_scope_is_enforced(self):
        self.config["outbound"]["shareable_fields"] = ["summary", "limitations"]
        result = outbox.prepare(self.update, self.config, self.tmp.name)
        self.assertNotIn("/project/atlas/run2", result["message"])
        self.assertNotIn("Next:", result["message"])
        self.assertIn("Pilot only", result["message"])

    def test_malformed_allowlist_does_not_match_substrings(self):
        self.config["outbound"]["source_session_ids"] = "SESSION_A_AND_OTHER"
        self.assertFalse(outbox.decision(self.update, self.config)[0])

    def test_update_marker_cannot_contain_newlines(self):
        with self.assertRaises(ValueError):
            outbox.queue(dict(self.update, update_id="one\nsecond"), self.tmp.name)


if __name__ == "__main__":
    unittest.main()
