"""Durable, opt-in receiver rotation bookkeeping. No chat, Slack or scheduler API.

Native tools create/verify the successor, retarget the existing worker/job, and
archive the predecessor. This helper never interprets a queue hint as approval.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import uuid

from answers import write_json
from relay import read_json


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result.astimezone(timezone.utc)


def thread_id(value):
    if str(uuid.UUID(value)) != value:
        raise ValueError("invalid_thread_id")
    return value


def validate(state):
    if state.get("schema_version") != 1 or state.get("enabled") is not True:
        raise ValueError("rotation_not_enabled")
    thread_id(state["current_thread_id"])
    thread_id(state["generation_id"])
    hours = state["max_age_hours"]
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours) or hours <= 0:
        raise ValueError("invalid_max_age")
    if timestamp(state["expires_at"]) != timestamp(state["started_at"]) + timedelta(hours=hours):
        raise ValueError("expiry_mismatch")
    if not isinstance(state["automation_id"], str) or not state["automation_id"]:
        raise ValueError("missing_automation_id")
    pending = state.get("pending")
    if pending:
        thread_id(pending["rotation_id"])
        thread_id(pending["from_thread_id"])
        if pending["phase"] not in ("creating", "bound", "activated"):
            raise ValueError("invalid_rotation_phase")
        if pending["phase"] != "creating":
            thread_id(pending["to_thread_id"])
            timestamp(pending["successor_started_at"])
            if pending["to_thread_id"] == pending["from_thread_id"]:
                raise ValueError("same_successor")
        expected = pending["to_thread_id"] if pending["phase"] == "activated" else pending["from_thread_id"]
        if state["current_thread_id"] != expected:
            raise ValueError("rotation_target_mismatch")
    return state


def status(state, at=None):
    validate(state)
    at = at or datetime.now(timezone.utc)
    return {"status": "in_progress" if state.get("pending") else "due" if at >= timestamp(state["expires_at"]) else "not_due",
            "current_thread_id": state["current_thread_id"], "expires_at": state["expires_at"],
            "pending": state.get("pending")}


def due_event(config, at=None):
    """One stable native hint per generation, deduplicated by the worker ledger."""
    if not config.get("rotation_state_file"):
        return None
    state = validate(read_json(Path(config["rotation_state_file"])))
    if state["current_thread_id"] != config["thread_id"]:
        raise ValueError("rotation_worker_target_mismatch")
    if status(state, at)["status"] != "due":
        return None
    return ("rotation-" + state["generation_id"],
            {"kind": "receiver_rotation_due", "generation_id": state["generation_id"],
             "thread_id": state["current_thread_id"], "expires_at": state["expires_at"]})


@contextmanager
def locked(path):
    lock = path.with_suffix(path.suffix + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    # A crash leaves an explicit recovery requirement, never a stolen live lock.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(uuid.uuid4()))
    try:
        yield
    finally:
        lock.unlink()


def change(path, action, *, current=None, successor=None, rotation_id=None,
           automation_id=None, max_age_hours=24, force=False, evidence=None, at=None):
    at = at or datetime.now(timezone.utc)
    with locked(path):
        if action == "init":
            if path.exists():
                raise ValueError("rotation_already_initialized")
            state = {"schema_version": 1, "enabled": True, "max_age_hours": max_age_hours,
                     "current_thread_id": thread_id(current), "generation_id": str(uuid.uuid4()),
                     "automation_id": automation_id, "started_at": at.isoformat(),
                     "expires_at": (at + timedelta(hours=max_age_hours)).isoformat(), "pending": None, "history": []}
        else:
            state = validate(read_json(path))
            if current != state["current_thread_id"]:
                raise ValueError("stale_receiver")
            pending = state.get("pending")
            if action == "begin":
                if pending:
                    # Creation may already have succeeded. Never create another.
                    return status(state, at)
                if not force and status(state, at)["status"] != "due":
                    return status(state, at)
                state["pending"] = {"rotation_id": str(uuid.uuid4()), "from_thread_id": current,
                                    "phase": "creating", "began_at": at.isoformat()}
            else:
                if not pending or pending["rotation_id"] != rotation_id:
                    raise ValueError("rotation_claim_mismatch")
                if action == "bind":
                    if pending["phase"] != "creating":
                        raise ValueError("successor_already_bound")
                    thread_id(successor)
                    retired = {x["from_thread_id"] for x in state["history"]}
                    if successor == current or successor in retired:
                        raise ValueError("successor_not_fresh")
                    pending.update(phase="bound", to_thread_id=successor, successor_started_at=at.isoformat())
                elif action == "activate":
                    if pending["phase"] != "bound":
                        raise ValueError("successor_not_bound")
                    # Attestations of actual native checks, not publication approval.
                    expected = pending["to_thread_id"]
                    if not isinstance(evidence, dict) or any(evidence.get(k) != expected for k in
                            ("ready_thread_id", "worker_thread_id", "automation_thread_id")):
                        raise ValueError("unverified_successor_targets")
                    if evidence.get("automation_id") != state["automation_id"] or evidence.get("automation_status") != "ACTIVE":
                        raise ValueError("automation_not_active")
                    state.update(current_thread_id=expected, generation_id=str(uuid.uuid4()),
                                 started_at=pending["successor_started_at"],
                                 expires_at=(timestamp(pending["successor_started_at"]) + timedelta(hours=state["max_age_hours"])).isoformat())
                    pending.update(phase="activated", activation_evidence=evidence, activated_at=at.isoformat())
                elif action == "complete":
                    if pending["phase"] != "activated" or not isinstance(evidence, dict):
                        raise ValueError("rotation_not_activated")
                    if evidence.get("archived_thread_id") != pending["from_thread_id"] or evidence.get("archived") is not True:
                        raise ValueError("predecessor_not_archived")
                    state["history"].append({**pending, "archive_evidence": evidence, "completed_at": at.isoformat()})
                    state["pending"] = None
                else:
                    raise ValueError("unknown_action")
        validate(state)
        write_json(path, state)
        return status(state, at)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "init", "begin", "bind", "activate", "complete"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--current")
    parser.add_argument("--successor")
    parser.add_argument("--rotation-id")
    parser.add_argument("--automation-id")
    parser.add_argument("--max-age-hours", type=float, default=24)
    parser.add_argument("--force", action="store_true", help="Only on the owner's immediate rollover instruction")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    result = status(read_json(args.state)) if args.action == "status" else change(
        args.state, args.action, current=args.current, successor=args.successor, rotation_id=args.rotation_id,
        automation_id=args.automation_id, max_age_hours=args.max_age_hours, force=args.force,
        evidence=read_json(args.evidence) if args.evidence else None)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
