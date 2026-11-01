"""Resolve configurable agent check intervals; this does not create schedules."""
import argparse
import json
import math
from pathlib import Path


def cadence_hours(config, runtime):
    if runtime not in ("codex", "claude"):
        raise ValueError("runtime must be codex or claude")
    overrides = config.get("cadence_overrides_hours", {})
    if not isinstance(overrides, dict) or any(key not in ("codex", "claude") for key in overrides):
        raise ValueError("cadence_overrides_hours may contain only codex and claude")
    value = overrides.get(runtime, config.get("cadence_hours", 6))
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 1 / 60:
        raise ValueError("cadence must be finite and at least one minute, expressed in hours")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runtime", choices=("codex", "claude"), required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    value = cadence_hours(config, args.runtime)
    print(json.dumps({"runtime": args.runtime, "cadence_hours": value, "interval_seconds": value * 3600}))


if __name__ == "__main__":
    main()
