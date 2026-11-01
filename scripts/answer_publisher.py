"""Validate owner-approved answers and persist send claims. Never calls Slack.

One publisher owns a bridge. An existing claim always requires reconciliation;
neither timeouts nor process restarts authorize another network send.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import answers
import relay


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def filename(answer_id):
    return digest(answer_id) + ".json"


def validate(entry, config, root):
    block = answers.policy(config)
    if block.get("mode") != "approval":
        raise ValueError("This publisher requires individual owner approval")
    if not isinstance(entry, dict) or entry.get("origin") != "owner_answer" or entry.get("kind") != "question_answer":
        raise ValueError("wrong_answer_type")
    answer_id = entry.get("answer_id")
    if not isinstance(answer_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", answer_id):
        raise ValueError("invalid_answer_id")
    if entry.get("reviewed_by_owner") is not True or entry.get("workspace_id") != config.get("workspace_id"):
        raise ValueError("unreviewed_or_wrong_workspace")
    decision = relay.read_json(root / "answers" / "decided" / (answer_id + ".json"))
    answers.validate(decision, config)
    session = block.get("approval_session_id")
    if decision.get("status") != "approved" or not isinstance(session, str) or not session.strip() or decision.get("approval_session_id") != session:
        raise ValueError("missing_matching_approval")
    for key in ("owner_words", "owner_message_ref", "decided_at"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError("missing_approval_evidence_" + key)
    for key in ("answer_id", "source_id", "channel_id", "thread_ts", "source_link"):
        if entry.get(key) != decision.get(key):
            raise ValueError("approval_mismatch_" + key)
    text = answers.render(decision, True)
    if entry.get("text") != text or decision.get("approved_text_sha256") != digest(text):
        raise ValueError("approved_text_changed")
    # Match the transport-supplied source, not a question quoted inside its text.
    source_name = digest(entry["source_id"]) + ".json"
    source = relay.read_json(relay.queue_directory(config, "inbox_directory", "inbox") / source_name)
    if not relay.classify(dict(source, visited=[]), config)[0] or source.get("origin") != "external_slack":
        raise ValueError("invalid_source")
    if source.get("message_kind") != "question":
        raise ValueError("source_is_not_a_question")
    if relay.source_id(source) != entry["source_id"] or source.get("source_id") != entry["source_id"]:
        raise ValueError("source_id_mismatch")
    expected = {"channel_id": source["channel_id"], "thread_ts": source.get("thread_ts", source["message_ts"]),
                "source_link": source.get("source_link"), "asker_user_id": source["sender_user_id"], "question": source["text"]}
    if any(decision.get(key) != value for key, value in expected.items()):
        raise ValueError("source_provenance_changed")
    return entry


def binding(entry):
    return {key: entry[key] for key in ("answer_id", "workspace_id", "channel_id", "thread_ts") } | {"text_sha256": digest(entry["text"])}


def receipt_valid(receipt, entry):
    return (isinstance(receipt, dict) and receipt.get("status") == "sent"
            and all(receipt.get(k) == v for k, v in binding(entry).items())
            and isinstance(receipt.get("message_ts"), str) and re.fullmatch(r"\d+\.\d+", receipt["message_ts"])
            and isinstance(receipt.get("message_link"), str) and receipt["message_link"].startswith("https://"))


def prepare(entry, config, root):
    validate(entry, config, root)
    name = filename(entry["answer_id"])
    receipt = root / "answer-sent" / name
    if receipt.exists():
        if not receipt_valid(relay.read_json(receipt), entry):
            raise ValueError("invalid_sent_receipt")
        return {"status": "already_sent", "answer_id": entry["answer_id"]}
    claim_path = root / "answer-state" / name
    if claim_path.exists():
        claim = relay.read_json(claim_path)
        if any(claim.get(k) != v for k, v in binding(entry).items()):
            raise ValueError("claim_changed")
        return {"status": "reconciliation_required", "marker": "Relay answer: " + entry["answer_id"],
                "channel_id": entry["channel_id"], "thread_ts": entry["thread_ts"]}
    return {"status": "ready_to_claim", "answer_id": entry["answer_id"]}


def claim(entry, config, root):
    result = prepare(entry, config, root)
    if result["status"] != "ready_to_claim":
        return result
    # Approval limits also apply at send time, including ambiguous sends. A
    # single publisher is required for cross-item quotas and Slack I/O.
    block = answers.policy(config)
    today = datetime.now(timezone.utc).date().isoformat()
    states = [relay.read_json(p) for p in (root / "answer-state").glob("*.json")]
    if sum(s.get("claimed_at", "")[:10] == today for s in states) >= block.get("max_per_day", 10):
        raise ValueError("daily_send_limit_reached")
    if sum(s.get("channel_id") == entry["channel_id"] and s.get("thread_ts") == entry["thread_ts"] for s in states) >= block.get("max_per_thread", 3):
        raise ValueError("thread_send_limit_reached")
    path = root / "answer-state" / filename(entry["answer_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({**binding(entry), "status": "in_flight", "claimed_at": datetime.now(timezone.utc).isoformat()}, stream, indent=2)
            stream.flush()
            import os
            os.fsync(stream.fileno())
    except FileExistsError:
        return prepare(entry, config, root)
    return {"status": "send_claimed", "channel_id": entry["channel_id"], "thread_ts": entry["thread_ts"], "text": entry["text"]}


def confirm(entry, config, root, evidence):
    validate(entry, config, root)
    path = root / "answer-state" / filename(entry["answer_id"])
    state = relay.read_json(path)
    if any(state.get(k) != v for k, v in binding(entry).items()):
        raise ValueError("claim_changed")
    # Evidence must be supplied from a successful transport result or an exact
    # read-back match by the configured owner in the original Slack thread.
    if any(evidence.get(k) != entry.get(k) for k in ("workspace_id", "channel_id", "thread_ts", "text")) or evidence.get("sender_user_id") != config["owner_slack_user_id"]:
        raise ValueError("transport_evidence_mismatch")
    receipt = {**binding(entry), "status": "sent", "message_ts": evidence.get("message_ts"), "message_link": evidence.get("message_link")}
    if not receipt_valid(receipt, entry):
        raise ValueError("invalid_transport_receipt")
    target = root / "answer-sent" / filename(entry["answer_id"])
    if target.exists() and relay.read_json(target) != receipt:
        raise ValueError("conflicting_sent_receipt")
    answers.write_json(target, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "claim", "confirm"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    try:
        config, entry = relay.read_json(args.config), relay.read_json(args.file)
        if args.file.name != filename(entry["answer_id"]):
            raise ValueError("outbox_filename_mismatch")
        if args.action == "confirm":
            if not args.evidence:
                raise ValueError("evidence_required")
            result = confirm(entry, config, args.root, relay.read_json(args.evidence))
        else:
            result = globals()[args.action](entry, config, args.root)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
