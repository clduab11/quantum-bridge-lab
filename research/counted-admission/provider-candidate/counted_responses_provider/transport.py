"""httpx 0.28.1 transport wrapper: the only path bytes can take to the wire.

For one armed attempt it (1) verifies method, URL and the ACTUAL serialized
JSON (strict parse, duplicate keys rejected) against the bound canonical
body, (2) writes the actual outgoing bytes durably with RequestRecords BEFORE
invoking the inner transport, (3) invokes the inner transport at most ONCE,
(4) reads the raw response and retains body, filtered headers, status,
request id and timestamps BEFORE the SDK sees them. A second request while
armed, or any request while disarmed, is refused before dispatch.

The inner transport is an httpx.MockTransport for every synthetic example;
a synthetic authority is refused with any other inner transport.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

import httpx

from .contract import ContractViolation, canonical_bytes, parse_json_strict

REDACTED_HEADER_MARKERS = ("authorization", "cookie", "api-key", "x-api-key")


def utc_now_text(wall_clock=time.time) -> str:
    return datetime.fromtimestamp(wall_clock(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def filtered_headers(headers) -> list:
    """[[name, value], ...] excluding authorization material; order preserved."""
    out = []
    for name, value in headers.multi_items() if hasattr(headers, "multi_items") else headers:
        lowered = str(name).lower()
        if any(marker in lowered for marker in REDACTED_HEADER_MARKERS):
            continue
        out.append([str(name), str(value)])
    return out


class DispatchRefused(ContractViolation):
    """Raised inside the transport before any inner dispatch."""


class RetentionFailed(RuntimeError):
    """Durable retention failed; dispatch state is recorded on the wrapper."""


class RecordingTransport(httpx.BaseTransport):
    def __init__(self, inner: httpx.BaseTransport, records, *, wall_clock=time.time):
        if not isinstance(inner, httpx.BaseTransport):
            raise TypeError("inner transport must be an httpx.BaseTransport")
        self.inner = inner
        self.records = records
        self.wall_clock = wall_clock
        self.armed = None
        self.reset_observation()

    @property
    def inner_is_mock(self) -> bool:
        return isinstance(self.inner, httpx.MockTransport)

    def reset_observation(self):
        self.dispatched = False
        self.request_retained = None
        self.response_retained = None
        self.refusal = None
        self.retention_error = None
        self.requests_seen = 0

    def arm(
        self, *, method: str, url: str, bound_object, bound_canonical: bytes, name: str, guard=None
    ):
        if self.armed is not None:
            raise ContractViolation("transport already armed for another attempt")
        if canonical_bytes(bound_object) != bound_canonical:
            raise ContractViolation("bound object and canonical bytes disagree")
        self.reset_observation()
        self.armed = {
            "method": method,
            "url": url,
            "object": bound_object,
            "canonical": bound_canonical,
            "canonical_sha256": hashlib.sha256(bound_canonical).hexdigest(),
            "name": name,
            "guard": guard,
        }

    def disarm(self):
        self.armed = None

    # -- the single wire path --------------------------------------------------
    def _refuse(self, reason: str, sent: bytes | None, url: str, klass: str = "compatibility"):
        self.refusal = {"reason": reason, "url": url, "sent_sha256": None, "klass": klass}
        if sent is not None:
            try:
                name = f"{self.armed['name']}.rejected_request.json" if self.armed else None
                if name:
                    self.refusal["sent_sha256"] = self.records.write(name, sent)
                    self.refusal["record"] = name
            except Exception as exc:  # noqa: BLE001 - best-effort retention of rejected bytes
                self.refusal["retention_error"] = type(exc).__name__
        raise DispatchRefused(reason)

    def handle_request(self, request):
        self.requests_seen += 1
        armed = self.armed
        url = str(request.url)
        if armed is None:
            self._refuse("request_while_disarmed", None, url)
        if self.requests_seen > 1 or self.dispatched or self.request_retained is not None:
            self._refuse("second_request_in_one_attempt", None, url)
        sent = bytes(request.read())
        if request.method != armed["method"] or url != armed["url"]:
            self._refuse("endpoint_or_method_mismatch", sent, url)
        parsed, error = parse_json_strict(sent)
        if error is not None:
            self._refuse(f"sent_bytes_not_strict_json:{error}", sent, url)
        if canonical_bytes(parsed) != armed["canonical"]:
            self._refuse("sent_bytes_differ_from_bound_body", sent, url)
        # Review fix R3: re-read durable halt / authority / ledger / price validity at the
        # wire boundary itself, after SDK preparation, immediately before retention+dispatch.
        if armed["guard"] is not None:
            verdict = armed["guard"]()
            if verdict is not None:
                reason, klass = verdict
                self._refuse(f"boundary_recheck:{reason}", None, url, klass)
        started = utc_now_text(self.wall_clock)
        try:
            digest = self.records.write(f"{armed['name']}.request.json", sent)
        except Exception as exc:
            self.retention_error = f"request_retention_failed:{type(exc).__name__}"
            raise RetentionFailed(self.retention_error) from exc
        self.request_retained = {
            "record": f"{armed['name']}.request.json",
            "sent_sha256": digest,
            "canonical_sha256": armed["canonical_sha256"],
            "bytes_identical_to_canonical": sent == armed["canonical"],
            "url": url,
            "method": request.method,
            "request_header_names": sorted({k.lower() for k in request.headers}),
            "started_utc": started,
            "started_monotonic": time.monotonic(),
        }
        self.dispatched = True
        response = self.inner.handle_request(request)
        try:
            response.read()
            body = bytes(response.content)
            received = utc_now_text(self.wall_clock)
            elapsed = time.monotonic() - self.request_retained["started_monotonic"]
            headers = filtered_headers(response.headers)
            meta = {
                "status": int(response.status_code),
                "headers": headers,
                "request_id": response.headers.get("x-request-id"),
                "date_header": response.headers.get("date"),
                "retry_after": response.headers.get("retry-after"),
                "retry_after_ms": response.headers.get("retry-after-ms"),
                "received_utc": received,
                "elapsed_seconds": elapsed,
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
            }
            body_name = f"{armed['name']}.response.body"
            meta_name = f"{armed['name']}.response.meta.json"
            self.records.write(body_name, body)
            self.records.write(meta_name, canonical_bytes(meta))
        except Exception as exc:
            self.retention_error = f"response_retention_failed:{type(exc).__name__}"
            response.close()
            raise RetentionFailed(self.retention_error) from exc
        finally:
            pass
        response.close()
        self.response_retained = {
            **meta,
            "body": body,
            "record": body_name,
            "meta_record": meta_name,
        }
        return httpx.Response(response.status_code, headers=response.headers, content=body)
