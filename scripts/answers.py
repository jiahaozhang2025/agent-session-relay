"""Owner-gated answers to coworker questions; Slack is sent by an authorized agent."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from outbox import read_json

LOOP_MARKER = re.compile(r"Relay (update|answer):", re.IGNORECASE)
NEVER_SHARE = re.compile(
    r"xox[abprs]-|\bsk-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY|\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*\S+"
    r"|[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)
MAX_LENGTH = 3500


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def policy(config):
    block = config.get("answers", {})
    if not isinstance(block, dict):
        raise ValueError("invalid_answer_policy")
    if block.get("enabled") is not True:
        raise ValueError("answers_disabled")
    if block.get("mode") not in ("approval", "automatic"):
        raise ValueError("invalid_answer_mode")
    channels = block.get("channel_ids")
    if not isinstance(channels, list) or any(not isinstance(c, str) or not c for c in channels):
        raise ValueError("invalid_answer_channels")
    for key, default in (("max_per_thread", 3), ("max_per_day", 10)):
        limit = block.get(key, default)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("invalid_" + key)
    return block


def validate(draft, config):
    if not isinstance(draft, dict):
        raise ValueError("A draft must be a JSON object")
    for key in ("answer_id", "source_id", "channel_id", "thread_ts", "asker_user_id", "source_link", "question", "answer"):
        if not isinstance(draft.get(key), str) or not draft[key].strip():
            raise ValueError("Missing " + key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", draft["answer_id"]):
        raise ValueError("answer_id must be a short stable identifier without whitespace or paths")
    if not re.fullmatch(r"\d+\.\d+", draft["thread_ts"]):
        raise ValueError("invalid_thread_timestamp")
    for key in ("sources", "limitations"):
        if not isinstance(draft.get(key), list) or any(not isinstance(x, str) for x in draft[key]):
            raise ValueError(key + " must be a list of strings")
    if not draft["sources"]:
        raise ValueError("An answer must cite where it came from")
    if draft["asker_user_id"] == config.get("owner_slack_user_id"):
        raise ValueError("own_post")
    if draft["channel_id"] not in policy(config).get("channel_ids", []):
        raise ValueError("destination_not_authorized")
    if LOOP_MARKER.search(draft["question"]):
        raise ValueError("relay_post")
    if NEVER_SHARE.search("\n".join([draft["answer"], *draft["sources"], *draft["limitations"]])):
        raise ValueError("never_share_pattern")


def render(draft, reviewed):
    lines = [draft["answer"].strip()]
    lines.append("Sources: " + "; ".join(draft["sources"]))
    if draft["limitations"]:
        lines.append("Limits: " + "; ".join(draft["limitations"]))
    note = "AI-drafted from existing work, reviewed by the owner." if reviewed else "AI-drafted from existing work, not individually reviewed."
    lines.append(note + " Relay answer: " + draft["answer_id"])
    text = "\n".join(lines)
    if len(text) > MAX_LENGTH:
        raise ValueError("answer_too_long")
    return text


def decided(root):
    for path in sorted((root / "answers" / "decided").glob("*.json")):
        yield read_json(path)


def check_limits(draft, config, root):
    block = policy(config)
    approved = [item for item in decided(root) if item.get("status") == "approved"]
    today = now()[:10]
    if sum(item.get("decided_at", "")[:10] == today for item in approved) >= block.get("max_per_day", 10):
        raise ValueError("daily_limit_reached")
    if sum(item.get("channel_id") == draft["channel_id"] and item.get("thread_ts") == draft["thread_ts"] for item in approved) >= block.get("max_per_thread", 3):
        raise ValueError("thread_limit_reached")


def publish(draft, config, root, reviewed, words, approval_session_id=None, owner_message_ref=None):
    validate(draft, config)
    if reviewed:
        expected = policy(config).get("approval_session_id")
        if not expected or approval_session_id != expected or not isinstance(owner_message_ref, str) or not owner_message_ref.strip():
            raise ValueError("Record the actual owner message reference in the configured brief session")
    check_limits(draft, config, root)
    text = render(draft, reviewed)
    entry = {key: draft[key] for key in ("answer_id", "source_id", "channel_id", "thread_ts", "source_link")}
    entry.update(workspace_id=config.get("workspace_id"), origin="owner_answer", kind="question_answer",
                 text=text, reviewed_by_owner=reviewed)
    name = hashlib.sha256(draft["answer_id"].encode("utf-8")).hexdigest() + ".json"
    write_json(root / "answers" / "decided" / (draft["answer_id"] + ".json"),
               {**draft, "status": "approved", "decided_at": now(), "owner_words": words,
                "approval_session_id": approval_session_id, "owner_message_ref": owner_message_ref,
                "approved_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    write_json(root / "answer-outbox" / name, entry)
    (root / "answers" / "drafts" / (draft["answer_id"] + ".json")).unlink(missing_ok=True)
    return {"status": "queued_for_publisher", "answer_id": draft["answer_id"], "posted": False}


def add_draft(draft, config, root):
    validate(draft, config)
    target = root / "answers" / "drafts" / (draft["answer_id"] + ".json")
    if target.exists() or (root / "answers" / "decided" / target.name).exists():
        return {"status": "already_recorded", "answer_id": draft["answer_id"]}
    render(draft, True)
    if policy(config)["mode"] == "automatic":
        return publish(draft, config, root, False, "standing owner policy")
    write_json(target, {**draft, "drafted_at": now()})
    return {"status": "awaiting_owner", "answer_id": draft["answer_id"]}


def decide(answer_id, approve, words, config, root, approval_session_id=None, owner_message_ref=None):
    if not words.strip():
        raise ValueError("Record the owner's own words")
    if not isinstance(answer_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", answer_id):
        raise ValueError("invalid_answer_id")
    path = root / "answers" / "drafts" / (answer_id + ".json")
    if not path.exists():
        raise ValueError("no_pending_draft")
    draft = read_json(path)
    validate(draft, config)
    if draft["answer_id"] != answer_id:
        raise ValueError("draft_id_mismatch")
    if approve:
        return publish(draft, config, root, True, words, approval_session_id, owner_message_ref)
    write_json(root / "answers" / "decided" / path.name, {**draft, "status": "rejected", "decided_at": now(), "owner_words": words})
    path.unlink()
    return {"status": "rejected", "answer_id": answer_id}


def pending(root):
    return [read_json(path) for path in sorted((root / "answers" / "drafts").glob("*.json"))]


def screen(envelope, config):
    if envelope.get("sender_user_id") == config.get("owner_slack_user_id"):
        return {"status": "blocked", "reason": "own_post"}
    if LOOP_MARKER.search(envelope.get("text", "")):
        return {"status": "blocked", "reason": "relay_post"}
    return {"status": "ok"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("screen", "draft", "pending", "approve", "reject"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--file", type=Path, help="envelope for screen, draft JSON for draft")
    parser.add_argument("--id", help="answer_id for approve or reject")
    parser.add_argument("--owner-words", default="", help="the owner's own words for approve or reject")
    parser.add_argument("--approval-session", help="configured brief session ID, for approve")
    parser.add_argument("--owner-message-ref", help="actual owner event/message ID in the brief session")
    args = parser.parse_args()
    config = read_json(args.root / "publisher-config.json")
    try:
        if args.action == "screen":
            result = screen(read_json(args.file), config)
        elif args.action == "draft":
            result = add_draft(read_json(args.file), config, args.root)
        elif args.action == "pending":
            result = pending(args.root)
        else:
            result = decide(args.id, args.action == "approve", args.owner_words, config, args.root,
                            args.approval_session, args.owner_message_ref)
    except ValueError as error:
        result = {"status": "blocked", "reason": str(error)}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
