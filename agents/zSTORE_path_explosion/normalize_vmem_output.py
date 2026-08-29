#!/usr/bin/env python3
"""Normalize Isla RISC-V VMEM JSON outputs for semantic review.

The instruction generator can choose different concrete instructions between
runs, so whole-file diffs are noisy. This tool focuses on the observable pieces
that matter for the VMEM builtin review: return values and memory events.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EVENT_FIELDS = (
    "kind",
    "region",
    "bytes",
    "address_model",
    "value",
    "data",
    "is_ifetch",
    "is_exclusive",
)


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    items = data.get("gen")
    if not isinstance(items, list):
        raise ValueError(f"{path}: expected top-level object with list field 'gen'")
    return items


def normalize_event(event: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple((field, event.get(field)) for field in EVENT_FIELDS if field in event)


def normalize_item(item: dict[str, Any]) -> tuple[Any, tuple[tuple[tuple[str, Any], ...], ...]]:
    events = item.get("memory-events", [])
    if not isinstance(events, list):
        raise ValueError("expected memory-events to be a list")
    return item.get("ret_val"), tuple(normalize_event(event) for event in events)


def counter_to_json(counter: Counter[Any]) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in sorted(counter.items(), key=lambda kv: repr(kv[0]))]


def summarize(path: Path) -> dict[str, Any]:
    items = load_items(path)
    normalized_items = [normalize_item(item) for item in items]
    event_counter: Counter[Any] = Counter()
    for _, events in normalized_items:
        event_counter.update(events)

    return {
        "path": str(path),
        "item_count": len(items),
        "ret_val_counts": counter_to_json(Counter(item.get("ret_val") for item in items)),
        "memory_event_count_counts": counter_to_json(Counter(len(item.get("memory-events", [])) for item in items)),
        "path_shape_counts": counter_to_json(Counter(normalized_items)),
        "event_counts": counter_to_json(event_counter),
    }


def compare(left: Path, right: Path) -> dict[str, Any]:
    left_summary = summarize(left)
    right_summary = summarize(right)
    left_shapes = Counter(normalize_item(item) for item in load_items(left))
    right_shapes = Counter(normalize_item(item) for item in load_items(right))
    left_events: Counter[Any] = Counter()
    right_events: Counter[Any] = Counter()
    for (_, events), count in left_shapes.items():
        for event in events:
            left_events[event] += count
    for (_, events), count in right_shapes.items():
        for event in events:
            right_events[event] += count

    return {
        "left": left_summary,
        "right": right_summary,
        "path_shape_only_left": counter_to_json(left_shapes - right_shapes),
        "path_shape_only_right": counter_to_json(right_shapes - left_shapes),
        "event_only_left": counter_to_json(left_events - right_events),
        "event_only_right": counter_to_json(right_events - left_events),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", nargs="?", type=Path)
    args = parser.parse_args()

    if args.right is None:
        result = summarize(args.left)
    else:
        result = compare(args.left, args.right)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
