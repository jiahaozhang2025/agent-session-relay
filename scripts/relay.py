"""Transport-neutral identity filter and private file queue. No Slack/API access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

RECEIPTS = ("CODEX_BRIDGE_ACK", "CODEX_UPDATE_ACK", "SESSION_UPDATE_ACK", "CLAUDE_UPDATE_ACK")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_config(config):
    for key in ("owner_slack_user_id", "workspace_id", "inbox_root"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip() or "REPLACE_WITH" in value:
            raise ValueError("Set a verified private value for " + key)
    channels = config.get("channel_ids")
    if not isinstance(channels, list) or not channels or any(
        not isinstance(c, str) or not c or "REPLACE_WITH" in c for c in channels
    ):
        raise ValueError("Set verified channel_ids")


def classify(message, config):
    validate_config(config)
    if message.get("workspace_id") != config["workspace_id"] or message.get("channel_id") not in config["channel_ids"]:
        return False, "wrong_scope"
    author = message.get("sender_user_id")
    if not isinstance(author, str) or not author:
        return False, "missing_author"
    if author == config["owner_slack_user_id"]:
        return False, "self_authored"
    if message.get("sender_is_bot") is not False:
        return False, "bot_or_unknown_sender_type"
    if message.get("event_type") != "message":
        return False, "non_message_event"
    body = message.get("text")
    if not isinstance(body, str) or not body.strip():
        return False, "empty"
    if message.get("message_kind") == "receipt" or body.lstrip().startswith(RECEIPTS):
        return False, "receipt"
    if message.get("message_kind") != "update":
        return False, "not_classified_as_update"
    ts = message.get("message_ts")
    if not isinstance(ts, str) or not re.fullmatch(r"\d+\.\d+", ts):
        return False, "invalid_timestamp"
    hops = message.get("visited", [])
    if not isinstance(hops, list) or any(not isinstance(h, str) for h in hops):
        return False, "invalid_hops"
    if "codex-router" in hops or "claude-coordinator" in hops:
        return False, "bridge_echo"
    return True, "external_update"


def source_id(message):
    return ":".join(message[k] for k in ("workspace_id", "channel_id", "message_ts"))


def enqueue(message, config):
    accepted, reason = classify(message, config)
    if not accepted:
        return {"status": "skipped", "reason": reason}
    identity = source_id(message)
    root = Path(config["inbox_root"]).expanduser()
    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(identity.encode("utf-8")).hexdigest() + ".json"
    target = inbox / name
    if target.exists():
        if read_json(target).get("source_id") != identity:
            raise ValueError("Existing queue item has unexpected provenance")
        return {"status": "already_queued", "source_id": identity, "path": str(target)}
    item = dict(message, schema_version=1, source_id=identity, origin="external_slack",
                intended_consumer="claude-coordinator", visited=["codex-router"],
                codex_deliveries=message.get("codex_deliveries", []))
    # One coordinator writes each owner/channel queue. Publish only complete JSON.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=inbox, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(item, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "queued", "source_id": identity, "path": str(target)}


def pending(config):
    validate_config(config)
    root = Path(config["inbox_root"]).expanduser()
    for path in sorted((root / "inbox").glob("*.json")):
        try:
            item = read_json(path)
        except (OSError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        # Recheck identity but not the existing codex-router hop of a queued item.
        candidate = dict(item, visited=[])
        if not classify(candidate, config)[0]:
            continue
        if item.get("source_id") != source_id(item) or item.get("intended_consumer") != "claude-coordinator":
            continue
        hops = item.get("visited")
        if not isinstance(hops, list) or "claude-coordinator" in hops:
            continue
        try:
            receipt = read_json(root / "receipts" / path.name)
        except (OSError, ValueError):
            receipt = None
        if isinstance(receipt, dict) and receipt.get("source_id") == item["source_id"] and receipt.get("status") in ("delivered", "no_match"):
            continue
        yield path, item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("filter", "enqueue", "watch"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--message", type=Path)
    parser.add_argument("--once", action="store_true", help="One filesystem check instead of watching")
    args = parser.parse_args()
    config = read_json(args.config)
    validate_config(config)
    if args.action == "watch":
        seen = set()
        while True:
            for path, item in pending(config):
                if item["source_id"] not in seen:
                    print(json.dumps({"event": "incoming_update", "source_id": item["source_id"], "path": str(path)}), flush=True)
                    seen.add(item["source_id"])
            if args.once:
                return
            time.sleep(30)
    else:
        if args.message is None:
            parser.error("--message is required for filter/enqueue")
        message = read_json(args.message)
        if args.action == "filter":
            accepted, reason = classify(message, config)
            result = {"accepted": accepted, "reason": reason}
        else:
            result = enqueue(message, config)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
