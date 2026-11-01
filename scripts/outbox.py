"""Private outbound drafts and policy checks; Slack is sent by an authorized agent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_update(update):
    if not isinstance(update, dict):
        raise ValueError("An update must be a JSON object")
    for key in ("update_id", "source_session_id", "workspace_id", "channel_id", "summary"):
        if not isinstance(update.get(key), str) or not update[key].strip():
            raise ValueError("Missing " + key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", update["update_id"]):
        raise ValueError("update_id must be a short stable identifier without whitespace or paths")
    if update.get("origin") != "local_analysis" or update.get("kind") != "analysis_update":
        raise ValueError("Only local analysis updates belong in the outbox")
    if update.get("incoming_source_id") or update.get("visited"):
        raise ValueError("Do not republish incoming relay traffic")
    for key in ("output_locations", "limitations"):
        if not isinstance(update.get(key, []), list) or any(not isinstance(x, str) for x in update.get(key, [])):
            raise ValueError(key + " must contain strings")
    if not isinstance(update.get("next_step", ""), str):
        raise ValueError("next_step must be a string")


def decision(update, config):
    validate_update(update)
    policy = config.get("outbound", {})
    if policy.get("enabled") is not True:
        return False, "outbound_disabled"
    if update["workspace_id"] != config.get("workspace_id"):
        return False, "wrong_workspace"
    sources = policy.get("source_session_ids", [])
    channels = policy.get("channel_ids", [])
    if not isinstance(sources, list) or not isinstance(channels, list):
        return False, "invalid_allowlists"
    if update["source_session_id"] not in sources:
        return False, "source_not_authorized"
    if update["channel_id"] not in channels:
        return False, "destination_not_authorized"
    fields = policy.get("shareable_fields", ["summary", "output_locations", "limitations", "next_step"])
    if not isinstance(fields, list) or "summary" not in fields or any(f not in ("summary", "output_locations", "limitations", "next_step") for f in fields):
        return False, "invalid_shareable_fields"
    return True, "within_owner_policy"


def filename(update):
    return hashlib.sha256(update["update_id"].encode("utf-8")).hexdigest() + ".json"


def queue(update, root):
    validate_update(update)
    directory = Path(root) / "outbox"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename(update)
    if target.exists():
        if read_json(target) != update:
            raise ValueError("update_id already exists with different content; do not mutate a queued update")
        return {"status": "already_queued", "path": str(target)}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(update, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "queued", "path": str(target), "posted": False}


def prepare(update, config, root):
    allowed, reason = decision(update, config)
    if not allowed:
        return {"status": "blocked", "reason": reason}
    try:
        receipt = read_json(Path(root) / "sent" / filename(update))
    except (OSError, ValueError):
        receipt = {}
    if isinstance(receipt, dict) and all(receipt.get(k) == update[k] for k in ("update_id", "workspace_id", "channel_id")):
        if receipt.get("status") == "sent" and receipt.get("message_ts") and receipt.get("message_link"):
            return {"status": "already_sent", "message_link": receipt["message_link"]}
    text = update["summary"].strip()
    fields = config["outbound"].get("shareable_fields", ["summary", "output_locations", "limitations", "next_step"])
    if "output_locations" in fields and update.get("output_locations"):
        text += "\nOutputs: " + "; ".join(update["output_locations"])
    if "limitations" in fields and update.get("limitations"):
        text += "\nLimits: " + "; ".join(update["limitations"])
    if "next_step" in fields and update.get("next_step"):
        text += "\nNext: " + update["next_step"]
    text += "\nRelay update: " + update["update_id"]
    if len(text) > 3500:
        return {"status": "blocked", "reason": "summary_too_long"}
    return {"status": "prepared_not_sent", "channel_id": update["channel_id"], "message": text,
            "requires_ledger_and_ambiguity_check": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("queue", "prepare"))
    parser.add_argument("--update", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    update = read_json(args.update)
    if args.action == "queue":
        result = queue(update, args.root)
    else:
        if args.config is None:
            parser.error("prepare requires --config")
        result = prepare(update, read_json(args.config), args.root)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
