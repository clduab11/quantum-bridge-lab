"""Private, single-writer, fsynced event journal with no-replay reservations.

The hash chain detects accidental corruption; it is not an authenticity proof
against an actor who can rewrite the entire file. A corrupt tail is preserved
and rejected, never truncated automatically.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path


class JournalCorrupt(ValueError):
    """The on-disk journal is not a complete, valid hash chain."""


class JournalBusy(RuntimeError):
    """Another file description already holds the writer lock."""


class NoReplayError(RuntimeError):
    """A reservation or completion would reuse an existing number."""


def _encoded(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _validate_usage(usage):
    if usage is None:
        return
    if not isinstance(usage, dict):
        raise ValueError("usage must be a category-to-count object or None")
    for category, count in usage.items():
        if not isinstance(category, str) or not category:
            raise ValueError("usage categories must be nonempty strings")
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError("known usage counts must be native nonnegative integers")


class DurableJournal:
    """Append-only JSONL. Use as a context manager; files must remain private.

    Only the owner process or its sequential arm worker may append. Forked
    workers inherit the locked file descriptor; concurrent writers are not an
    accepted execution arrangement.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._fd = None
        self._size = -1
        self._records = []
        created = not self.path.exists()
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise PermissionError("journal must be a regular private 0600 file")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise JournalBusy(str(self.path)) from exc
            self._fd = fd
            self._refresh()
            if created:
                os.fsync(fd)
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except BaseException:
            os.close(fd)
            self._fd = None
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _refresh(self):
        if self._fd is None:
            raise ValueError("journal is closed")
        size = os.fstat(self._fd).st_size
        if size == self._size:
            return
        data = os.pread(self._fd, size, 0)
        if len(data) != size or (data and not data.endswith(b"\n")):
            raise JournalCorrupt("incomplete journal tail")
        records = []
        previous = "0" * 64
        reservations = set()
        completed = set()
        try:
            for number, line in enumerate(data.splitlines(), 1):
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("record is not an object")
                digest = row.pop("hash")
                if row["seq"] != number or row["previous"] != previous:
                    raise ValueError("sequence or previous digest mismatch")
                if hashlib.sha256(_encoded(row)).hexdigest() != digest:
                    raise ValueError("digest mismatch")
                if row["kind"] == "reserved":
                    if row["reservation"] in reservations:
                        raise ValueError("reused reservation")
                    reservations.add(row["reservation"])
                elif row["kind"] == "completed":
                    key = row["reservation"]
                    if key not in reservations or key in completed:
                        raise ValueError("invalid completion")
                    completed.add(key)
                row["hash"] = digest
                records.append(row)
                previous = digest
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise JournalCorrupt("invalid journal record") from exc
        self._records = records
        self._size = size

    def read_events(self):
        self._refresh()
        return copy.deepcopy(self._records)

    def append(self, kind: str, **fields):
        self._refresh()
        if not isinstance(kind, str) or not kind:
            raise ValueError("event kind must be nonempty text")
        if {"seq", "previous", "hash", "kind"} & fields.keys():
            raise ValueError("reserved event fields")
        row = {
            "seq": len(self._records) + 1,
            "previous": self._records[-1]["hash"] if self._records else "0" * 64,
            "kind": kind,
            **copy.deepcopy(fields),
        }
        row["hash"] = hashlib.sha256(_encoded(row)).hexdigest()
        data = _encoded(row) + b"\n"
        offset = 0
        while offset < len(data):
            written = os.write(self._fd, data[offset:])
            if written <= 0:
                raise OSError("short journal write")
            offset += written
        os.fsync(self._fd)
        self._records.append(row)
        self._size += len(data)
        return copy.deepcopy(row)

    def reserve(self, resource: str, key: str, **fields):
        if resource not in {"objective", "transport"}:
            raise ValueError("unknown reserved resource")
        reservation = f"{resource}:{key}"
        if any(e.get("reservation") == reservation for e in self.read_events()):
            raise NoReplayError(reservation)
        self.append("reserved", resource=resource, reservation=reservation, **fields)
        return reservation

    def complete(self, reservation: str, **fields):
        matches = [e for e in self.read_events() if e.get("reservation") == reservation]
        if len(matches) != 1 or matches[0]["kind"] != "reserved":
            raise NoReplayError(reservation)
        original = matches[0]
        if original["resource"] == "transport":
            _validate_usage(fields.get("usage"))
        inherited = {
            key: original[key]
            for key in ("block", "arm", "slot", "batch", "logical", "attempt")
            if key in original
        }
        if {"reservation", "resource"} & fields.keys():
            raise ValueError("completion cannot change its resource")
        return self.append(
            "completed",
            reservation=reservation,
            resource=original["resource"],
            **inherited,
            **fields,
        )

    def resource_counts(self, *, block=None, arm=None, usage_categories=()):
        """Return confirmed work, uncertainty bounds and known usage subtotals.

        usage_categories may list additional billing categories required by a
        future pinned provider. Every observed category is retained. Missing
        categories and explicit None are unknown, including for an empty usage
        object; known subtotals are lower bounds, never substituted totals.
        """
        events = [
            e
            for e in self.read_events()
            if (block is None or e.get("block") == block) and (arm is None or e.get("arm") == arm)
        ]
        completed = {e["reservation"]: e for e in events if e["kind"] == "completed"}
        objectives = [e for e in events if e["kind"] == "reserved" and e["resource"] == "objective"]
        attempts = [e for e in events if e["kind"] == "reserved" and e["resource"] == "transport"]
        confirmed = sum(
            completed.get(e["reservation"], {}).get("invoked") is True for e in objectives
        )
        unresolved = sum(e["reservation"] not in completed for e in objectives)
        dispatches = sum(
            completed.get(e["reservation"], {}).get("dispatched") is True for e in attempts
        )
        unknown_dispatch = sum(
            completed.get(e["reservation"], {}).get("dispatched") is None for e in attempts
        )
        if isinstance(usage_categories, str) or any(
            not isinstance(c, str) or not c for c in usage_categories
        ):
            raise ValueError("usage_categories must contain nonempty category names")
        categories = {"input_tokens", "output_tokens", *usage_categories}
        usages = []
        for event in attempts:
            usage = completed.get(event["reservation"], {}).get("usage")
            _validate_usage(usage)
            usage = usage or {}
            categories.update(usage)
            usages.append(usage)
        lower_bounds = {c: sum(usage.get(c) or 0 for usage in usages) for c in sorted(categories)}
        missing_counts = {
            c: sum(usage.get(c) is None for usage in usages) for c in sorted(categories)
        }
        unknown_usage = sum(any(usage.get(c) is None for c in categories) for usage in usages)
        return {
            "confirmed_objective_calls": confirmed,
            "unresolved_objective_reservations": unresolved,
            "actual_objective_call_bounds": [confirmed, confirmed + unresolved],
            "attempt_allowances_used": len(attempts),
            "confirmed_transport_dispatches": dispatches,
            "unresolved_transport_reservations": sum(
                e["reservation"] not in completed for e in attempts
            ),
            "actual_transport_dispatch_bounds": [dispatches, dispatches + unknown_dispatch],
            "unknown_usage_attempts": unknown_usage,
            "usage_lower_bounds": lower_bounds,
            "usage_missing_counts": missing_counts,
            "usage_is_complete": not any(missing_counts.values()),
            "known_input_tokens": lower_bounds["input_tokens"],
            "known_output_tokens": lower_bounds["output_tokens"],
        }
