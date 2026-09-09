"""Single-attempt Responses provider for qbridge.counted_runner.CountedArmRunner.

prepare(request) -> RequestPair                  pure; literal texts; canonical bytes
count(pair, context, timeout) -> AttemptResult   at most ONE HTTP request
generate(pair, receipt, context, timeout) -> AttemptResult   at most ONE HTTP request

The runner owns caps, correction rules, retries/backoff, the common deadline,
admission and transport reservations. This provider owns: the wire profile,
pre-send verification, durable raw retention, dispatch authority and price
validity, monetary reservations for both classes, usage settlement, identity
checks and the exact runner result categories. It never sleeps, never retries,
never reads an API key itself (a caller-supplied provider function is invoked
only in the dispatching process) and never launches a study.

Halt classes persisted as `provider_halted` (the runner's kind) BEFORE return:
  ivf_halt (inferential_failure=True) > compatibility/credential/authority halts
  > accounting_halt. A stricter finding is persisted even if a weaker halt
  already exists, and the current-text accounting exception is returned only
  when no stricter finding exists on this object and no stricter halt is
  already durable.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from qbridge.counted_runner import (
    AttemptResult,
    CountReceipt,
    DispatchContext,
    RequestPair,
)
from qbridge.request_records import RequestRecords

from . import contract as C
from .authority import HTTPX_VERSION, SDK_VERSION, AuthorityRecord
from .ledger import LedgerHalted, MoneyLedger, decimal_text, fraction_to_text
from .transport import RecordingTransport, utc_now_text

HALT_RANK = {"accounting": 1, "compatibility": 2, "credential": 2, "authority": 2, "ivf": 3}
RUNNER_REQUEST_KEYS = frozenset({"system", "user", "max_tokens"})
POLICY_LABEL = {"e9": "e9_fail", "study": None}


class ProviderRefused(RuntimeError):
    """Construction-time refusal; nothing was journaled or dispatched."""


def _versions_ok():
    import httpx
    import openai

    return openai.__version__ == SDK_VERSION and httpx.__version__ == HTTPX_VERSION


def extract_output_text(payload) -> tuple[str, dict]:
    """Concatenate output_text parts of message items. Any refusal part, any
    non-string text or no text at all => "" (zero valid vectors). Reasoning
    items are never read."""
    info = {"message_items": 0, "output_text_parts": 0, "refusal_parts": 0, "other_item_types": []}
    output = payload.get("output") if isinstance(payload, dict) else None
    if not isinstance(output, list):
        info["output_missing"] = True
        return "", info
    texts = []
    for item in output:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind != "message":
            info["other_item_types"].append(str(kind))
            continue
        info["message_items"] += 1
        parts = item.get("content")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "refusal":
                info["refusal_parts"] += 1
            elif part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    info["output_text_parts"] += 1
                    texts.append(text)
                else:
                    info["refusal_parts"] += 1  # unusable part: treated as zero-valid
    info["other_item_types"] = sorted(set(info["other_item_types"]))
    if info["refusal_parts"] or not texts:
        return "", info
    return "".join(texts), info


def usage_for_runner(payload) -> dict:
    """Flat category->nonnegative int|None object accepted by DurableJournal.complete."""
    usage = payload.get("usage") if isinstance(payload, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("input_tokens_details")
    details = details if isinstance(details, dict) else {}
    out_details = usage.get("output_tokens_details")
    out_details = out_details if isinstance(out_details, dict) else {}

    def nonneg(value):
        return value if type(value) is int and value >= 0 else None

    return {
        "input_tokens": nonneg(usage.get("input_tokens")),
        "output_tokens": nonneg(usage.get("output_tokens")),
        "total_tokens": nonneg(usage.get("total_tokens")),
        "cached_tokens": nonneg(details.get("cached_tokens")),
        "cache_write_tokens": nonneg(details.get("cache_write_tokens")),
        "reasoning_tokens": nonneg(out_details.get("reasoning_tokens")),
    }


def seed_identity_baseline(journal, *, vector: dict, source: str, accepted_from_e9: bool):
    """Assembly helper (Codex): carry an ACCEPTED E9 baseline into a study journal.

    The provider never writes `identity_baseline` itself. In E9 scope it records
    provisional `identity_observation` events only; acceptance (E9 passed, all
    fixtures reconciled, manifest written) is a separate recorded decision and
    is asserted here by the caller with `accepted_from_e9=True` plus a nonempty
    provenance string. The vector is validated structurally (exact keys, list
    presence tags with canonical JSON values)."""
    if accepted_from_e9 is not True:
        raise ValueError("a study baseline requires an explicitly accepted E9 result")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must name the E9 record the baseline was accepted from")
    normalized = C.validate_identity_vector(vector)
    if any(
        e["kind"] == "identity_baseline" and e.get("scope") == "study"
        for e in journal.read_events()
    ):
        raise ValueError("a study baseline already exists in this journal")
    journal.append(
        "identity_baseline",
        scope="study",
        vector=normalized,
        source=source,
        accepted_from_e9=True,
        vector_sha256=C.sha256(C.canonical_bytes(normalized)),
    )
    return normalized


class SingleAttemptResponsesProvider:
    def __init__(
        self,
        *,
        journal,
        records: RequestRecords,
        authority: AuthorityRecord,
        transport_factory,
        api_key_provider,
        wall_clock=time.time,
    ):
        if not isinstance(authority, AuthorityRecord):
            raise ProviderRefused("an AuthorityRecord is required")
        if not isinstance(records, RequestRecords):
            raise ProviderRefused("a qbridge.request_records.RequestRecords store is required")
        if not callable(transport_factory) or not callable(api_key_provider):
            raise ProviderRefused("transport_factory and api_key_provider must be callables")
        if not _versions_ok():
            raise ProviderRefused(f"requires openai {SDK_VERSION} and httpx {HTTPX_VERSION}")
        self.journal = journal
        self.records = records
        self.authority = authority
        self.transport_factory = transport_factory
        self.api_key_provider = api_key_provider
        self.wall_clock = wall_clock
        self.scope = authority.scope
        self.effort = authority.reasoning_effort
        self.ledger = MoneyLedger(journal, scope=self.scope, ceiling=authority.ceiling())
        self._bind_authority()

    # ------------------------------------------------------------- durable state
    def _bind_authority(self):
        digest = self.authority.sha256()
        bound = [
            e
            for e in self.journal.read_events()
            if e["kind"] == "authority_bound" and e.get("scope") == self.scope
        ]
        if bound:
            if bound[0]["authority_sha256"] != digest:
                raise ProviderRefused("journal already binds a different authority for this scope")
            return
        self.journal.append(
            "authority_bound",
            scope=self.scope,
            authority_sha256=digest,
            authority=self.authority.as_dict(),
            profile_sha256=self.authority.profile_sha256,
        )

    def _authority_matches_journal(self) -> bool:
        try:
            AuthorityRecord.from_dict(self.authority.as_dict())  # re-validate (mutation check)
        except (ValueError, C.ContractViolation):
            return False
        digest = self.authority.sha256()
        return any(
            e["kind"] == "authority_bound"
            and e.get("scope") == self.scope
            and e["authority_sha256"] == digest
            for e in self.journal.read_events()
        )

    def _persisted_halts(self):
        return [e for e in self.journal.read_events() if e["kind"] == "provider_halted"]

    def _strictest_persisted_rank(self) -> int:
        rank = 0
        for event in self._persisted_halts():
            if event.get("inferential_failure"):
                rank = max(rank, 3)
            elif event.get("reason") == "accounting_halt":
                rank = max(rank, 1)
            else:
                rank = max(rank, 2)
        return rank

    def identity_baseline(self):
        """Study: the carried, validated E9 baseline (`identity_baseline`, scope study,
        accepted_from_e9 True). E9: the first provisional `identity_observation` of this
        E9 journal (drift within E9 is still detected). Invalid stored vectors -> None."""
        kind = "identity_baseline" if self.scope == "study" else "identity_observation"
        for event in self.journal.read_events():
            if event["kind"] == kind and event.get("scope") == self.scope:
                if kind == "identity_baseline" and event.get("accepted_from_e9") is not True:
                    return None, "invalid:not_accepted_from_e9"
                try:
                    return C.validate_identity_vector(event["vector"]), event.get("source")
                except (C.ContractViolation, KeyError):
                    return None, "invalid:vector"
        return None, None

    def _persist_halt(self, reason: str, *, klass: str, context, findings=(), request_class=None):
        ivf = klass == "ivf"
        rank = HALT_RANK[klass]
        if rank > self._strictest_persisted_rank():
            self.journal.append("provider_halted", reason=reason, inferential_failure=ivf)
        self.journal.append(
            "provider_halt_detail",
            scope=self.scope,
            halt_class=klass,
            reason=reason,
            inferential_failure=ivf,
            transport_reservation=getattr(context, "reservation", None),
            request_class=request_class,
            findings=list(findings),
        )

    # ------------------------------------------------------------------ prepare
    def prepare(self, request) -> RequestPair:
        if not isinstance(request, dict) or set(request) != RUNNER_REQUEST_KEYS:
            raise C.ContractViolation("runner request must have exactly system, user, max_tokens")
        if type(request["max_tokens"]) is not int or request["max_tokens"] != C.MAX_OUTPUT_TOKENS:
            raise C.ContractViolation("max_tokens must be the int 8192")
        body = C.build_generation_body(
            request["system"], request["user"], reasoning_effort=self.effort
        )
        # literal strings preserved: the body holds the very same str objects
        assert body["input"][0]["content"] is request["system"]
        assert body["input"][1]["content"] is request["user"]
        bound = C.bind_pair(body, reasoning_effort=self.effort)
        return RequestPair(bound["count_bytes"], bound["generation_bytes"])

    # ---------------------------------------------------------------- preflight
    def _preflight(self, context, request_class: str, transport: RecordingTransport):
        """Returns None when dispatch may proceed, else (halt_reason, klass)."""
        if not isinstance(context, DispatchContext) or context.request_class != request_class:
            return "dispatch_context_invalid", "compatibility"
        halts = self._persisted_halts()
        if halts:
            return f"already_halted:{halts[0]['reason']}", None
        if not _versions_ok():
            return "sdk_or_httpx_version_mismatch", "compatibility"
        if not self._authority_matches_journal():
            return "authority_mismatch", "authority"
        if self.authority.synthetic != transport.inner_is_mock:
            return "authority_transport_class_mismatch", "authority"
        if not self.authority.price_valid_at(self.wall_clock()):
            return "price_validity_expired", "authority"
        if self.ledger.state()["halted"]:
            return "ledger_halted", "accounting"
        if self.scope == "study":
            baseline, source = self.identity_baseline()
            if baseline is None:
                return f"study_baseline_missing_or_invalid:{source}", "authority"
        return None

    def _boundary_recheck(self, transport):
        """Runs inside the transport at the wire boundary (review fix R3)."""
        halts = self._persisted_halts()
        if halts:
            return f"already_halted:{halts[0]['reason']}", "compatibility"
        if not self._authority_matches_journal():
            return "authority_mismatch", "authority"
        if self.authority.synthetic != transport.inner_is_mock:
            return "authority_transport_class_mismatch", "authority"
        if not self.authority.price_valid_at(self.wall_clock()):
            return "price_validity_expired", "authority"
        if self.ledger.state()["halted"]:
            return "ledger_halted", "accounting"
        if self.scope == "study":
            baseline, source = self.identity_baseline()
            if baseline is None:
                return f"study_baseline_missing_or_invalid:{source}", "authority"
        return None

    def _transport(self) -> RecordingTransport:
        inner = self.transport_factory()
        return RecordingTransport(inner, self.records, wall_clock=self.wall_clock)

    @staticmethod
    def _record_name(context) -> str:
        return (
            f"{context.arm}_b{context.block}_bt{context.batch}_l{context.logical}"
            f"_{context.request_class}_a{context.attempt}"
        )

    # ------------------------------------------------------------------ dispatch
    def _dispatch(
        self,
        transport,
        *,
        request_class,
        body,
        canonical,
        url,
        timeout,
        api_key,
        name,
        parent_reservation,
    ):
        import httpx
        import openai

        limit = httpx.Timeout(float(timeout), connect=min(10.0, float(timeout)))
        client = httpx.Client(transport=transport, follow_redirects=False, timeout=limit)
        outcome = {"kind": None, "status": None, "exception": None}
        try:
            sdk = openai.OpenAI(
                api_key=api_key,
                max_retries=0,
                base_url="https://api.openai.com/v1",
                http_client=client,
            )
            if sdk.max_retries != 0:
                raise C.ContractViolation("SDK retries must be zero")
            transport.arm(
                method="POST",
                url=url,
                bound_object=body,
                bound_canonical=canonical,
                name=name,
                guard=lambda: self._boundary_recheck(transport),
            )
            self.journal.append(
                "provider_dispatch_intent",
                scope=self.scope,
                transport_reservation=parent_reservation,
                record_prefix=name,
                request_class=request_class,
                url=url,
                canonical_sha256=C.sha256(canonical),
                intent_utc=utc_now_text(self.wall_clock),
            )
            try:
                if request_class == "count":
                    sdk.responses.input_tokens.with_raw_response.count(**body, timeout=limit)
                else:
                    sdk.responses.with_raw_response.create(**body, timeout=limit)
                outcome["kind"] = "response"
            except openai.APITimeoutError:
                outcome["kind"] = "timeout"
            except openai.APIStatusError as exc:
                outcome["kind"] = "response"
                outcome["status"] = exc.status_code
            except openai.APIConnectionError as exc:
                cause = type(exc.__cause__).__name__ if exc.__cause__ else None
                outcome["exception"] = cause
                if transport.refusal is not None:
                    outcome["kind"] = "refused"
                elif transport.retention_error is not None:
                    outcome["kind"] = "retention_failed"
                else:
                    outcome["kind"] = "connection"
            except Exception as exc:  # noqa: BLE001 - classified, never retried
                outcome["kind"] = "client_exception"
                outcome["exception"] = type(exc).__name__
        finally:
            transport.disarm()
            client.close()
        return outcome

    # ------------------------------------------------------------------ helpers
    def _retry_after(self, retained) -> dict:
        if retained is None:
            return {"retry_after_seconds": None, "retry_after_valid": True, "finding": None}
        seconds, finding = C.parse_retry_after(
            retained.get("retry_after"),
            retained.get("date_header"),
            datetime.strptime(retained["received_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            ),
        )
        valid = finding != "retry_after_malformed"
        return {
            "retry_after_seconds": None if seconds is None else float(seconds),
            "retry_after_valid": valid,
            "finding": finding,
        }

    def _attempt_event(self, context, request_class, fields):
        self.journal.append(
            "provider_attempt",
            scope=self.scope,
            transport_reservation=context.reservation,
            request_class=request_class,
            **fields,
        )

    def _refusal_result(self, context, request_class, reason, klass):
        """No dispatch happened. Persist the halt (if any) before returning."""
        terminal = "count_terminal" if request_class == "count" else "gen_terminal"
        metadata = {"dispatched": False, "refusal": reason}
        if klass is not None:
            self._persist_halt(reason, klass=klass, context=context, request_class=request_class)
            if klass == "credential":
                category = (
                    "count_halt_credential" if request_class == "count" else "gen_halt_credential"
                )
                return AttemptResult(category, metadata=metadata, halt_reason=reason)
            return AttemptResult(terminal, metadata=metadata, halt_reason=reason)
        existing = self._persisted_halts()[0]
        return AttemptResult(
            terminal,
            metadata=metadata,
            halt_reason=existing["reason"],
            ivf=bool(existing.get("inferential_failure")),
        )

    def _settle_unknown(
        self, money_key, *, dispatched, outcome_text, findings, retained="retained_unknown"
    ):
        if money_key is None:
            return None
        if not dispatched:
            record = self.ledger.settle(
                money_key,
                outcome="released_not_dispatched",
                computed_charge=None,
                reconciled=False,
                findings=[outcome_text, *findings],
            )
        else:
            record = self.ledger.settle(
                money_key,
                outcome=retained,
                computed_charge=None,
                reconciled=False,
                findings=[outcome_text, *findings],
            )
        return record["outcome"]

    def _base_metadata(self, transport, outcome, money_key, reservation_amount):
        request = transport.request_retained or {}
        response = transport.response_retained
        meta = {
            "dispatched": bool(transport.dispatched),
            "requests_seen": transport.requests_seen,
            "outcome_kind": outcome["kind"],
            "client_exception": outcome["exception"],
            "sent_sha256": request.get("sent_sha256"),
            "canonical_sha256": request.get("canonical_sha256"),
            "bytes_identical_to_canonical": request.get("bytes_identical_to_canonical"),
            "request_record": request.get("record"),
            "started_utc": request.get("started_utc"),
            "money_reservation": money_key,
            "reserved_usd": None
            if reservation_amount is None
            else decimal_text(reservation_amount),
            "reserved_fraction": None
            if reservation_amount is None
            else fraction_to_text(reservation_amount),
            "refusal": transport.refusal,
            "retention_error": transport.retention_error,
        }
        if response is not None:
            meta.update(
                {
                    "http_status": response["status"],
                    "request_id": response["request_id"],
                    "date_header": response["date_header"],
                    "retry_after_raw": response["retry_after"],
                    "retry_after_ms_raw": response["retry_after_ms"],
                    "received_utc": response["received_utc"],
                    "elapsed_seconds": response["elapsed_seconds"],
                    "body_sha256": response["body_sha256"],
                    "body_bytes": response["body_bytes"],
                    "response_record": response["record"],
                    "response_meta_record": response["meta_record"],
                    "response_headers": response["headers"],
                }
            )
        return meta

    # -------------------------------------------------------------------- count
    def count(self, pair, context, timeout) -> AttemptResult:
        request_class = "count"
        transport = self._transport()
        refused = self._preflight(context, request_class, transport)
        if refused is not None:
            return self._refusal_result(context, request_class, *refused)
        if not isinstance(pair, RequestPair):
            return self._refusal_result(context, request_class, "pair_invalid", "compatibility")
        body, error = C.parse_json_strict(pair.count_body)
        if error is not None or C.canonical_bytes(body) != pair.count_body:
            return self._refusal_result(
                context, request_class, "count_body_not_canonical", "compatibility"
            )
        try:
            generation, gerror = C.parse_json_strict(pair.generation_body)
            if gerror is not None:
                raise C.ContractViolation(gerror)
            C.verify_pair(generation, body, reasoning_effort=self.effort)
        except C.ContractViolation as exc:
            return self._refusal_result(
                context, request_class, f"pair_violates_profile:{exc}", "compatibility"
            )
        api_key = self.api_key_provider()
        if not isinstance(api_key, str) or not api_key.strip():
            return self._refusal_result(
                context, request_class, "credential_unavailable", "credential"
            )
        amount = self.authority.count_fee_ceiling()
        try:
            money_key = self.ledger.reserve(
                request_class=request_class,
                transport_reservation=context.reservation,
                amount=amount,
                basis={
                    "kind": "count_fee_ceiling_verified",
                    "evidence": self.authority.count_fee_evidence,
                },
                class_cap=self.authority.count_attempt_cap,
            )
        except LedgerHalted as exc:
            klass = (
                "accounting"
                if str(exc) in ("ledger_halted", "monetary_ceiling_reached")
                else "authority"
            )
            return self._refusal_result(context, request_class, str(exc), klass)
        name = self._record_name(context)
        outcome = self._dispatch(
            transport,
            request_class=request_class,
            body=body,
            canonical=pair.count_body,
            url=C.COUNT_ENDPOINT,
            timeout=timeout,
            api_key=api_key,
            name=name,
            parent_reservation=context.reservation,
        )
        return self._finish_count(context, transport, outcome, money_key, amount)

    def _finish_count(self, context, transport, outcome, money_key, amount):
        request_class = "count"
        meta = self._base_metadata(transport, outcome, money_key, amount)
        findings = []
        result = None
        kind = outcome["kind"]
        if kind == "refused":
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=False,
                outcome_text="refused_before_dispatch",
                findings=[],
                retained="retained_ceiling",
            )
            reason = f"sent_bytes_violate_contract:{transport.refusal['reason']}"
            self._persist_halt(
                reason,
                klass=transport.refusal["klass"],
                context=context,
                request_class=request_class,
            )
            result = AttemptResult("count_contract_anomaly", metadata=meta, halt_reason=reason)
        elif kind == "retention_failed":
            dispatched = transport.dispatched
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=dispatched,
                outcome_text=transport.retention_error,
                findings=[],
                retained="retained_ceiling",
            )
            self._persist_halt(
                transport.retention_error,
                klass="compatibility",
                context=context,
                request_class=request_class,
            )
            result = AttemptResult(
                "count_terminal", metadata=meta, halt_reason=transport.retention_error
            )
        elif kind in ("timeout", "connection"):
            meta["settlement"] = self.ledger.settle(
                money_key,
                outcome="retained_ceiling" if transport.dispatched else "released_not_dispatched",
                computed_charge=None,
                reconciled=False,
                findings=[f"transport_{kind}"],
            )["outcome"]
            result = AttemptResult("count_retryable", metadata=meta)
        elif kind == "client_exception":
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=transport.dispatched,
                outcome_text="client_exception",
                findings=[],
                retained="retained_ceiling",
            )
            reason = f"provider_client_exception:{outcome['exception']}"
            self._persist_halt(
                reason, klass="compatibility", context=context, request_class=request_class
            )
            result = AttemptResult("count_contract_anomaly", metadata=meta, halt_reason=reason)
        else:  # response
            retained = transport.response_retained
            if retained is None or (
                outcome["status"] is not None and outcome["status"] != retained["status"]
            ):
                meta["settlement"] = self._settle_unknown(
                    money_key,
                    dispatched=True,
                    outcome_text="response_not_retained",
                    findings=[],
                    retained="retained_ceiling",
                )
                reason = "response_not_retained_before_parse"
                self._persist_halt(
                    reason, klass="compatibility", context=context, request_class=request_class
                )
                result = AttemptResult("count_contract_anomaly", metadata=meta, halt_reason=reason)
            else:
                status = retained["status"]
                payload = None
                if 200 <= status <= 299:
                    payload, perror = C.parse_json_strict(retained["body"])
                    if perror is not None:
                        findings.append(perror)
                    else:
                        counted, cfindings = C.validate_count_payload(payload)
                        findings.extend(cfindings)
                category, _ = C.classify_count_outcome(status, payload)
                if 200 <= status <= 299 and payload is not None:
                    counted, _ = C.validate_count_payload(payload)
                else:
                    counted = None
                meta["findings"] = findings
                meta["settlement"] = self.ledger.settle(
                    money_key,
                    outcome="retained_ceiling",
                    computed_charge=None,
                    reconciled=False,
                    findings=findings,
                )["outcome"]
                retry = self._retry_after(retained)
                meta["retry_after"] = retry
                if category == "count_ok":
                    result = AttemptResult("count_ok", counted_tokens=counted, metadata=meta)
                elif category == "count_retryable":
                    result = AttemptResult(
                        "count_retryable",
                        metadata=meta,
                        retry_after_seconds=retry["retry_after_seconds"],
                        retry_after_valid=retry["retry_after_valid"],
                    )
                elif category == "count_halt_credential":
                    reason = f"credential_halt:http_{status}"
                    self._persist_halt(
                        reason, klass="credential", context=context, request_class=request_class
                    )
                    result = AttemptResult(
                        "count_halt_credential", metadata=meta, halt_reason=reason
                    )
                elif category == "count_terminal":
                    result = AttemptResult("count_terminal", metadata=meta)
                else:
                    reason = "compatibility_halt:count_contract_anomaly:" + ",".join(
                        findings or [f"http_{status}"]
                    )
                    self._persist_halt(
                        reason,
                        klass="compatibility",
                        context=context,
                        findings=findings,
                        request_class=request_class,
                    )
                    result = AttemptResult(
                        "count_contract_anomaly", metadata=meta, halt_reason=reason
                    )
        self._attempt_event(
            context,
            request_class,
            {
                "category": result.category,
                "counted_tokens": result.counted_tokens,
                "metadata": meta,
            },
        )
        return result

    # ----------------------------------------------------------------- generate
    def _receipt_valid(self, pair, receipt, context) -> str | None:
        """Bind the receipt to ONE genuine count attempt: the runner's `reserved`
        event for receipt.reservation (class count, same arm/block/batch/logical,
        body_sha256 == receipt digest == sha256(pair.count_body)), its `completed`
        event (status count_ok, identical counted_tokens), the provider's own attempt
        record for that reservation (count_ok, identical counted_tokens and canonical
        hash) and exactly one matching `count_receipt`. A forged receipt that reuses a
        genuine reservation with another digest, token value or logical key fails."""
        if not isinstance(receipt, CountReceipt):
            return "receipt_type_invalid"
        if receipt.logical_key != context.logical_key:
            return "receipt_logical_key_mismatch"
        digest = C.sha256(pair.count_body)
        if receipt.count_body_sha256 != digest:
            return "receipt_count_digest_mismatch"
        if type(receipt.counted_tokens) is not int or receipt.counted_tokens < 0:
            return "receipt_count_invalid"
        if receipt.counted_tokens > self.authority.input_token_ceiling:
            return "receipt_exceeds_input_ceiling"
        events = self.journal.read_events()
        reserved = [
            e
            for e in events
            if e["kind"] == "reserved"
            and e.get("reservation") == receipt.reservation
            and e.get("resource") == "transport"
        ]
        if len(reserved) != 1:
            return "receipt_reservation_unknown"
        origin = reserved[0]
        if (
            origin.get("request_class") != "count"
            or origin.get("body_sha256") != digest
            or origin.get("arm") != context.arm
            or origin.get("block") != context.block
            or origin.get("batch") != context.batch
            or origin.get("logical") != context.logical
        ):
            return "receipt_reservation_context_mismatch"
        completed = [
            e
            for e in events
            if e["kind"] == "completed" and e.get("reservation") == receipt.reservation
        ]
        if (
            len(completed) != 1
            or completed[0].get("status") != "count_ok"
            or completed[0].get("counted_tokens") != receipt.counted_tokens
        ):
            return "receipt_count_completion_mismatch"
        attempts = [
            e
            for e in events
            if e["kind"] == "provider_attempt"
            and e.get("transport_reservation") == receipt.reservation
        ]
        if (
            len(attempts) != 1
            or attempts[0].get("category") != "count_ok"
            or attempts[0].get("counted_tokens") != receipt.counted_tokens
            or attempts[0].get("metadata", {}).get("canonical_sha256") != digest
        ):
            return "receipt_provider_count_mismatch"
        receipts = [
            e
            for e in events
            if e["kind"] == "count_receipt"
            and e.get("logical_key") == receipt.logical_key
            and e.get("count_body_sha256") == digest
            and e.get("counted_tokens") == receipt.counted_tokens
            and e.get("reservation") == receipt.reservation
        ]
        if len(receipts) != 1:
            return "receipt_not_durable"
        return None

    def generate(self, pair, receipt, context, timeout) -> AttemptResult:
        request_class = "generation"
        transport = self._transport()
        refused = self._preflight(context, request_class, transport)
        if refused is not None:
            return self._refusal_result(context, request_class, *refused)
        if not isinstance(pair, RequestPair):
            return self._refusal_result(context, request_class, "pair_invalid", "compatibility")
        body, error = C.parse_json_strict(pair.generation_body)
        if error is not None or C.canonical_bytes(body) != pair.generation_body:
            return self._refusal_result(
                context, request_class, "generation_body_not_canonical", "compatibility"
            )
        try:
            count_body, cerror = C.parse_json_strict(pair.count_body)
            if cerror is not None:
                raise C.ContractViolation(cerror)
            C.verify_pair(body, count_body, reasoning_effort=self.effort)
        except C.ContractViolation as exc:
            return self._refusal_result(
                context, request_class, f"pair_violates_profile:{exc}", "compatibility"
            )
        problem = self._receipt_valid(pair, receipt, context)
        if problem is not None:
            return self._refusal_result(context, request_class, problem, "compatibility")
        api_key = self.api_key_provider()
        if not isinstance(api_key, str) or not api_key.strip():
            return self._refusal_result(
                context, request_class, "credential_unavailable", "credential"
            )
        rates = self.authority.rates()
        amount = C.reservation_for_generation(receipt.counted_tokens, rates)
        try:
            money_key = self.ledger.reserve(
                request_class=request_class,
                transport_reservation=context.reservation,
                amount=amount,
                basis={
                    "kind": "exact_input_plus_output_cap",
                    "counted_input_tokens": receipt.counted_tokens,
                    "max_output_tokens": C.MAX_OUTPUT_TOKENS,
                    "rate_source_sha256": self.authority.rate_source_sha256,
                },
                class_cap=self.authority.generation_attempt_cap,
            )
        except LedgerHalted as exc:
            klass = (
                "accounting"
                if str(exc) in ("ledger_halted", "monetary_ceiling_reached")
                else "authority"
            )
            return self._refusal_result(context, request_class, str(exc), klass)
        name = self._record_name(context)
        outcome = self._dispatch(
            transport,
            request_class=request_class,
            body=body,
            canonical=pair.generation_body,
            url=C.GENERATION_ENDPOINT,
            timeout=timeout,
            api_key=api_key,
            name=name,
            parent_reservation=context.reservation,
        )
        return self._finish_generation(
            context, transport, outcome, money_key, amount, receipt, rates
        )

    def _finish_generation(self, context, transport, outcome, money_key, amount, receipt, rates):
        request_class = "generation"
        meta = self._base_metadata(transport, outcome, money_key, amount)
        kind = outcome["kind"]
        result = None
        if kind == "refused":
            meta["settlement"] = self._settle_unknown(
                money_key, dispatched=False, outcome_text="refused_before_dispatch", findings=[]
            )
            reason = f"sent_bytes_violate_contract:{transport.refusal['reason']}"
            self._persist_halt(
                reason,
                klass=transport.refusal["klass"],
                context=context,
                request_class=request_class,
            )
            result = AttemptResult("gen_contract_anomaly", metadata=meta, halt_reason=reason)
        elif kind == "retention_failed":
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=transport.dispatched,
                outcome_text=transport.retention_error,
                findings=[],
            )
            self._persist_halt(
                transport.retention_error,
                klass="compatibility",
                context=context,
                request_class=request_class,
            )
            result = AttemptResult(
                "gen_terminal", metadata=meta, halt_reason=transport.retention_error
            )
        elif kind in ("timeout", "connection"):
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=transport.dispatched,
                outcome_text=f"transport_{kind}",
                findings=[],
            )
            result = AttemptResult("gen_retryable", metadata=meta)
        elif kind == "client_exception":
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=transport.dispatched,
                outcome_text="client_exception",
                findings=[],
            )
            reason = f"provider_client_exception:{outcome['exception']}"
            self._persist_halt(
                reason, klass="compatibility", context=context, request_class=request_class
            )
            result = AttemptResult("gen_contract_anomaly", metadata=meta, halt_reason=reason)
        else:
            retained = transport.response_retained
            if retained is None or (
                outcome["status"] is not None and outcome["status"] != retained["status"]
            ):
                meta["settlement"] = self._settle_unknown(
                    money_key, dispatched=True, outcome_text="response_not_retained", findings=[]
                )
                reason = "response_not_retained_before_parse"
                self._persist_halt(
                    reason, klass="compatibility", context=context, request_class=request_class
                )
                result = AttemptResult("gen_contract_anomaly", metadata=meta, halt_reason=reason)
            elif 200 <= retained["status"] <= 299:
                result = self._received_object(
                    context, transport, meta, money_key, amount, receipt, rates
                )
            else:
                status = retained["status"]
                category, _ = C.classify_generation_outcome(status, None)
                retry = self._retry_after(retained)
                meta["retry_after"] = retry
                meta["settlement"] = self._settle_unknown(
                    money_key, dispatched=True, outcome_text=f"http_{status}", findings=[]
                )
                if category == "gen_retryable":
                    result = AttemptResult(
                        "gen_retryable",
                        metadata=meta,
                        retry_after_seconds=retry["retry_after_seconds"],
                        retry_after_valid=retry["retry_after_valid"],
                    )
                elif category == "gen_halt_credential":
                    reason = f"credential_halt:http_{status}"
                    self._persist_halt(
                        reason, klass="credential", context=context, request_class=request_class
                    )
                    result = AttemptResult("gen_halt_credential", metadata=meta, halt_reason=reason)
                elif category == "gen_terminal":
                    result = AttemptResult("gen_terminal", metadata=meta)
                else:
                    reason = f"compatibility_halt:unexpected_http_status:{status}"
                    self._persist_halt(
                        reason, klass="compatibility", context=context, request_class=request_class
                    )
                    result = AttemptResult(
                        "gen_contract_anomaly", metadata=meta, halt_reason=reason
                    )
        self._attempt_event(context, request_class, {"category": result.category, "metadata": meta})
        return result

    def _received_object(self, context, transport, meta, money_key, amount, receipt, rates):
        """Every 2xx object: strict parse -> settle usage/charge -> identity -> classify."""
        request_class = "generation"
        retained = transport.response_retained
        status = retained["status"]
        payload, perror = C.parse_json_strict(retained["body"])
        if perror is not None or not isinstance(payload, dict):
            meta["settlement"] = self._settle_unknown(
                money_key,
                dispatched=True,
                outcome_text="body_unparseable",
                findings=[perror or "not_object"],
            )
            reason = f"compatibility_halt:gen_body_unparseable:{perror or 'not_object'}"
            self._persist_halt(
                reason, klass="compatibility", context=context, request_class=request_class
            )
            return AttemptResult("gen_contract_anomaly", metadata=meta, halt_reason=reason)

        # 1. settlement of usage and charge (before any classification)
        settlement = C.settle_response(
            payload, receipt.counted_tokens, amount, rates, policy=self.scope
        )
        findings = list(settlement["findings"])
        charge = settlement["charge"]
        runner_usage = usage_for_runner(payload)
        meta["usage_findings"] = findings
        meta["computed_charge_usd"] = None if charge is None else decimal_text(charge)
        meta["computed_charge_fraction"] = None if charge is None else fraction_to_text(charge)
        meta["reconciled_usage"] = settlement["reconciled"]
        meta["overrun"] = settlement["overrun"]
        ivf_findings = [f for f in findings if f.startswith(C.IVF_FINDING_PREFIXES)]
        accounting_findings = [
            f
            for f in findings
            if f.startswith(C.ACCOUNTING_FINDING_PREFIXES) or f == "response_not_object"
        ]
        if settlement["overrun"]:
            accounting_findings.append(
                f"overrun:computed={decimal_text(charge)},reserved={decimal_text(amount)}"
            )
        if charge is None:
            accounting_findings.append("charge_unknown")

        # 2. profile and identity
        profile_findings = C.validate_expected_profile(payload, reasoning_effort=self.effort)
        vector = C.identity_vector(payload)
        baseline, baseline_source = self.identity_baseline()
        identity_findings = [] if baseline is None else C.compare_identity(vector, baseline)
        meta["profile_findings"] = profile_findings
        meta["identity_findings"] = identity_findings
        meta["identity_vector"] = vector
        meta["baseline_source"] = baseline_source
        compatibility_findings = []
        if profile_findings:
            if baseline is None:
                compatibility_findings.extend(profile_findings)  # before baseline: compatibility
            else:
                ivf_findings.extend(profile_findings)  # after baseline: drift
        ivf_findings.extend(identity_findings)

        # 3. classification (status/error code)
        category, _ = C.classify_generation_outcome(status, payload)
        meta["response_status"] = payload.get("status")
        meta["response_id"] = payload.get("id") if isinstance(payload.get("id"), str) else None
        details = payload.get("incomplete_details")
        meta["incomplete_reason"] = details.get("reason") if isinstance(details, dict) else None
        if category == "gen_contract_anomaly":
            compatibility_findings.append(f"unexpected_response_status:{payload.get('status')!r}")
        text, text_info = extract_output_text(payload)
        meta["text_extraction"] = text_info
        received = category in ("received_completed", "received_incomplete")

        # 4. ledger settlement (unknown/unreconciled retained in full; overrun unclipped)
        if charge is None:
            outcome = "retained_unknown"
        elif not settlement["reconciled"]:
            outcome = "retained_unreconciled"
        elif settlement["overrun"]:
            outcome = "overrun_recorded"
        else:
            outcome = "settled_actual"
        meta["settlement"] = self.ledger.settle(
            money_key,
            outcome=outcome,
            computed_charge=charge,
            reconciled=settlement["reconciled"],
            findings=findings,
            usage=runner_usage,
        )["outcome"]

        # 5. halt priority: ivf > compatibility > accounting
        e9 = self.scope == "e9"
        if ivf_findings:
            reason = ("e9_fail:" if e9 else "ivf_halt:") + ivf_findings[0]
            self._persist_halt(
                reason,
                klass="ivf",
                context=context,
                findings=ivf_findings,
                request_class=request_class,
            )
            return AttemptResult(
                category,
                text=text if received else None,
                usage=runner_usage,
                metadata=meta,
                halt_reason=reason,
                ivf=True,
            )
        if compatibility_findings:
            reason = ("e9_fail:" if e9 else "compatibility_halt:") + compatibility_findings[0]
            self._persist_halt(
                reason,
                klass="compatibility",
                context=context,
                findings=compatibility_findings,
                request_class=request_class,
            )
            return AttemptResult(
                category,
                text=text if received else None,
                usage=runner_usage,
                metadata=meta,
                halt_reason=reason,
            )
        if accounting_findings:
            reason = "e9_fail:accounting" if e9 else "accounting_halt"
            self._persist_halt(
                reason,
                klass="accounting",
                context=context,
                findings=accounting_findings,
                request_class=request_class,
            )
            accept = (
                received and not e9 and self._strictest_persisted_rank() <= HALT_RANK["accounting"]
            )
            return AttemptResult(
                category,
                text=text if received else None,
                usage=runner_usage,
                metadata=meta,
                halt_reason=reason,
                accept_received_on_halt=accept,
            )
        # clean object: E9 records a PROVISIONAL observation (never a baseline);
        # study scope already required a carried baseline before dispatch.
        if self.scope == "e9" and category == "received_completed":
            self.journal.append(
                "identity_observation",
                scope=self.scope,
                vector=vector,
                transport_reservation=context.reservation,
                provisional=True,
                accepted=False,
            )
            meta["provisional_observation_recorded"] = baseline is None
        retry = self._retry_after(retained)
        meta["retry_after"] = retry
        if received:
            return AttemptResult(category, text=text, usage=runner_usage, metadata=meta)
        if category == "gen_failed_retryable":
            return AttemptResult(
                category,
                usage=runner_usage,
                metadata=meta,
                retry_after_seconds=retry["retry_after_seconds"],
                retry_after_valid=retry["retry_after_valid"],
            )
        return AttemptResult(category, usage=runner_usage, metadata=meta)


__all__ = [
    "ProviderRefused",
    "SingleAttemptResponsesProvider",
    "extract_output_text",
    "seed_identity_baseline",
    "usage_for_runner",
]
