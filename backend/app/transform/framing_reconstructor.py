from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.agents.llm_client import LLMClient
from app.transform.node3_executor import Node3Executor
from app.transform.spec_renderer import SpecRenderer
from app.transform.spec_validator import SpecValidator

DATA_REF = "__revisio_primary_data__"
BASELINE_FIELD = "revisio_baseline"


@dataclass
class FramingContract:
    role: str
    incoming_claim: str
    agent_claim: str
    metric_label: str
    x_field: str
    y_field: str
    evidence_start: Any
    evidence_end: Any
    evidence_note: str
    structural_move: str
    taxonomy_ops: list[str] = field(default_factory=list)
    window_kind: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReconstructResult:
    ok: bool
    spec: dict[str, Any] | None
    contract: FramingContract | None
    executed_operations: list[dict[str, Any]]
    operation_audit: list[dict[str, Any]]
    layers_affected: list[str]
    variant_description: str
    execution_mode: str
    validation_errors: list[str]
    verify_reasons: list[str]


class FramingReconstructor:
    """Rebuild the incoming chart so this agent's claim is visible.

    LLM may rewrite Vega-Lite (thinking on). Deterministic fallback still
    changes structure. Color-only diffs fail verification.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.executor = Node3Executor(llm_client=llm_client)
        self.validator = SpecValidator()
        self.renderer = SpecRenderer()

    def reconstruct(
        self,
        parent_spec: dict[str, Any] | None,
        role: str,
        gap_type: str = "",
        perception: str = "",
        shift_magnitude: str = "sig",
        context: dict[str, Any] | None = None,
    ) -> ReconstructResult | None:
        if not isinstance(parent_spec, dict):
            return None
        role = "Extender" if role == "Analyst" else role
        ctx = context or {}
        contract = self.build_contract(parent_spec, role, gap_type, perception, ctx)
        if contract is None:
            return None

        self.executor._current_role = role
        self.executor._current_institution = str(ctx.get("institution") or "")
        self.executor._current_depth = int(ctx.get("depth") or 1)

        if self.llm_client is not None and self.llm_client.enabled:
            candidate, errors = self._reconstruct_via_llm(parent_spec, contract, perception, ctx)
            if candidate is not None:
                ok, reasons = self.verify_contract(parent_spec, candidate, contract)
                if ok:
                    return self._finish(candidate, contract, shift_magnitude, "reconstructed", reasons, errors)
                repaired = self._repair_via_llm(parent_spec, candidate, contract, reasons)
                if repaired is not None:
                    ok, reasons = self.verify_contract(parent_spec, repaired, contract)
                    if ok:
                        return self._finish(
                            repaired, contract, shift_magnitude, "reconstructed_repaired", reasons, errors
                        )

        fallback = self._reconstruct_deterministic(parent_spec, contract)
        if fallback is None:
            return ReconstructResult(
                ok=False,
                spec=None,
                contract=contract,
                executed_operations=[],
                operation_audit=[],
                layers_affected=[],
                variant_description="Framing reconstruct failed.",
                execution_mode="reconstruct_failed",
                validation_errors=["deterministic_reconstruct_failed"],
                verify_reasons=[],
            )
        ok, reasons = self.verify_contract(parent_spec, fallback, contract)
        if not ok:
            return ReconstructResult(
                ok=False,
                spec=fallback,
                contract=contract,
                executed_operations=[],
                operation_audit=[],
                layers_affected=[],
                variant_description="Deterministic reconstruct did not satisfy framing contract.",
                execution_mode="reconstruct_failed",
                validation_errors=reasons,
                verify_reasons=reasons,
            )
        return self._finish(fallback, contract, shift_magnitude, "reconstructed_fallback", reasons, [])

    def build_contract(
        self,
        parent_spec: dict[str, Any],
        role: str,
        gap_type: str,
        perception: str,
        context: dict[str, Any],
    ) -> FramingContract | None:
        series = LLMClient._extract_xy_series_summary(parent_spec)
        if not series:
            return None
        incoming = _title_text(parent_spec) or str(context.get("description") or "source chart")
        plan_step = context.get("chain_plan_step") if isinstance(context.get("chain_plan_step"), dict) else {}
        planned_claim = str(plan_step.get("agent_claim") or "").strip()
        planned_move = str(plan_step.get("structural_move") or "").strip()
        metric = _metric_from_incoming(incoming, str(series.get("y_label") or series["y_field"]))
        x_field = str(series["x_field"])
        y_field = str(series["y_field"])
        primary_y = _primary_channel(parent_spec, "y")
        if isinstance(primary_y, dict) and isinstance(primary_y.get("field"), str):
            candidate = str(primary_y["field"])
            if len(_story_rows(parent_spec, x_field, candidate)) >= 4:
                y_field = candidate
        rows = _story_rows(parent_spec, x_field, y_field)
        if len(rows) < 4:
            return None
        trend = str(series.get("trend") or "flat")

        if role == "Amplifier":
            window = _amplifier_zoom_window(rows, x_field, y_field, incoming) or _peak_zoom_window(rows, x_field, y_field)
            if window is None:
                return None
            claim = planned_claim or _next_amplifier_claim(incoming, metric, window)
            note = (
                f"{_compact_x(window['start_x'])}–{_compact_x(window['end_x'])}: "
                f"{_fmt_num(window['start_val'])} → {_fmt_num(window['end_val'])}"
            )
            zoom = str(window["kind"]) == "rise_zoom"
            return FramingContract(
                role=role,
                incoming_claim=incoming,
                agent_claim=claim,
                metric_label=metric,
                x_field=x_field,
                y_field=y_field,
                evidence_start=window["start_x"],
                evidence_end=window["end_x"],
                evidence_note=note,
                structural_move=planned_move
                or (
                    "convert to area and zoom y off zero so the recent climb fills the frame"
                    if zoom
                    else "crop the incoming dramatic window and retighten y"
                ),
                taxonomy_ops=["select_data_range", "change_axis_scale", "change_title", "add_annotation"]
                + (["change_chart_type"] if zoom else []),
                window_kind=str(window["kind"]),
            )

        if role == "Adverser":
            want_rise = _adverser_want_rise(incoming, trend)
            window = None
            for years in (20, 40, None):
                slice_rows = rows if years is None else _recent_rows(rows, x_field, years=years)
                if len(slice_rows) < 4:
                    continue
                window = _directional_window(slice_rows, x_field, y_field, want_rise)
                if window is not None:
                    break
            if window is None:
                window = _undercut_window(_recent_rows(rows, x_field, years=40), x_field, y_field)
            if window is None:
                window = _undercut_window(rows, x_field, y_field)
            if window is None:
                return None
            kind = window["kind"]
            if planned_claim:
                claim = planned_claim
            elif kind == "rise":
                claim = f"{metric} surged after {_compact_x(window['start_x'])}"
            elif kind == "undercut":
                claim = f"{metric} stayed lower before {_compact_x(window['end_x'])}"
            else:
                claim = f"{metric} eased after {_compact_x(window['start_x'])}"
            note = (
                f"{_compact_x(window['start_x'])}–{_compact_x(window['end_x'])}: "
                f"{_fmt_num(window['start_val'])} → {_fmt_num(window['end_val'])}"
            )
            return FramingContract(
                role=role,
                incoming_claim=incoming,
                agent_claim=claim,
                metric_label=metric,
                x_field=x_field,
                y_field=y_field,
                evidence_start=window["start_x"],
                evidence_end=window["end_x"],
                evidence_note=note,
                structural_move=planned_move or "crop a contrary or lower-evidence window on the incoming chart",
                taxonomy_ops=["select_data_range", "change_axis_scale", "change_title", "add_annotation"],
                window_kind=kind,
            )

        if role == "Bridger":
            claim = planned_claim or incoming
            if claim.lower() == incoming.lower():
                claim = f"{metric}: the recorded series"
            return FramingContract(
                role=role,
                incoming_claim=incoming,
                agent_claim=claim,
                metric_label=metric,
                x_field=x_field,
                y_field=y_field,
                evidence_start=series["first_x"],
                evidence_end=series["last_x"],
                evidence_note="repackage without changing the evidence window",
                structural_move=planned_move or "change mark/packaging, keep the incoming claim",
                taxonomy_ops=["change_chart_type", "change_title"],
                window_kind="repackage",
            )

        ys = [float(r[y_field]) for r in rows]
        mean_val = sum(ys) / len(ys)
        kind = _extender_rule_count(parent_spec)
        planned_ok = bool(planned_claim) and any(
            token in planned_claim.lower() for token in ("mean", "compar", "context", "versus", "vs ")
        )
        claim = planned_claim if planned_ok else _next_extender_claim(incoming, metric, kind)
        if not claim or claim.lower() == incoming.lower():
            claim = _next_extender_claim(incoming, metric, kind)
        return FramingContract(
            role=role,
            incoming_claim=incoming,
            agent_claim=claim,
            metric_label=metric,
            x_field=x_field,
            y_field=y_field,
            evidence_start=series["first_x"],
            evidence_end=series["last_x"],
            evidence_note=f"Peak {_fmt_num(float(series['peak_y']))} vs mean {_fmt_num(mean_val)}",
            structural_move=planned_move or "overlay a period-mean comparison on the incoming series",
            taxonomy_ops=["add_data_variables", "change_title", "add_annotation"],
            window_kind="compare",
        )

    def verify_contract(
        self,
        parent_spec: dict[str, Any],
        candidate: dict[str, Any],
        contract: FramingContract,
    ) -> tuple[bool, list[str]]:
        reasons = _structural_reasons(parent_spec, candidate)
        errors: list[str] = []
        if not reasons or reasons == ["color"]:
            errors.append("color_only_or_no_structural_diff")
        title = _title_text(candidate)
        if not title or title == _title_text(parent_spec):
            if contract.role != "Bridger":
                errors.append("title_unchanged")
        if contract.role in {"Analyst", "Extender"} and not _title_keeps_metric(
            title, contract.metric_label, contract.y_field
        ):
            errors.append("extender_title_dropped_metric")
        if contract.role in {"Adverser", "Amplifier"}:
            if "data_range" not in reasons and "x_scale" not in reasons:
                errors.append(f"{contract.role.lower()}_window_not_visible")
        if contract.role in {"Analyst", "Extender"} and not _has_baseline_layer(candidate):
            errors.append("extender_missing_comparison_layer")
        if contract.role in {"Analyst", "Extender"} and _has_invented_y_fields(candidate):
            errors.append("extender_invented_fields")
        validation = self.validator.validate(candidate)
        if not validation.ok:
            errors.extend(validation.errors)
        if Node3Executor._is_chart_data_empty(candidate):
            errors.append("chart_data_empty")
        ok = not errors
        return ok, (reasons if ok else errors)

    def as_node_c_payload(self, result: ReconstructResult, shift_magnitude: str) -> dict[str, Any]:
        layer_map = {"data": "D", "visual": "V", "text": "T"}
        if result.layers_affected:
            layer_text = "+".join(layer_map[item] for item in result.layers_affected)
        else:
            layer_text = "T"
        return {
            "variant_description": result.variant_description,
            "layers": f"{layer_text} {shift_magnitude}",
            "updated_chart_spec": result.spec,
            "executed_operations": result.executed_operations,
            "execution_mode": result.execution_mode,
            "validation_errors": result.validation_errors,
            "operation_audit": result.operation_audit,
            "framing_contract": result.contract.as_dict() if result.contract else None,
            "verify_reasons": result.verify_reasons,
        }

    def _finish(
        self,
        spec: dict[str, Any],
        contract: FramingContract,
        shift_magnitude: str,
        mode: str,
        reasons: list[str],
        extra_errors: list[str],
    ) -> ReconstructResult:
        ops = _ops_from_contract(contract, reasons)
        layers = sorted({_op_layer(op["operation"]) for op in ops})
        desc = f"Framing reconstruct [{mode}]: {contract.agent_claim}"
        _sanitize_chart_layout(spec)
        return ReconstructResult(
            ok=True,
            spec=spec,
            contract=contract,
            executed_operations=ops,
            operation_audit=ops,
            layers_affected=layers,
            variant_description=desc,
            execution_mode=mode,
            validation_errors=extra_errors,
            verify_reasons=reasons,
        )

    def _reconstruct_deterministic(self, parent_spec: dict[str, Any], contract: FramingContract) -> dict[str, Any] | None:
        spec = _prepare_incoming_canvas(parent_spec)
        if contract.role == "Bridger":
            _apply_claim_title(spec, contract.agent_claim)
            _maybe_repackage_mark(spec)
            return spec
        if contract.role in {"Adverser", "Amplifier"}:
            ok, _, _ = self.executor._select_data_range(
                spec,
                {
                    "x_field": contract.x_field,
                    "start": contract.evidence_start,
                    "end": contract.evidence_end,
                },
            )
            if not ok:
                return None
            if contract.window_kind == "rise_zoom":
                _amplifier_zoom_mark(spec)
            _rescale_y_to_visible_data(spec, contract.y_field, tighten_dual=True)
            _apply_claim_title(spec, contract.agent_claim)
            self.executor._add_annotation(
                spec,
                contract.evidence_note,
                {"include_trendline": False, "max_line_chars": 42, "min_font_size": 14, "prune_offtopic_annotations": True},
            )
            if contract.role == "Adverser":
                self.executor._delete_source(spec)
            return spec
        if not _add_baseline_comparison(spec, contract):
            return None
        _apply_claim_title(spec, contract.agent_claim)
        self.executor._add_annotation(
            spec,
            contract.evidence_note,
            {"include_trendline": False, "max_line_chars": 44, "min_font_size": 14, "prune_offtopic_annotations": True},
        )
        return spec

    def _reconstruct_via_llm(
        self,
        parent_spec: dict[str, Any],
        contract: FramingContract,
        perception: str,
        context: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[str]]:
        if self.llm_client is None:
            return None, ["llm_disabled"]
        compact, values = _stub_primary_data(_prepare_incoming_canvas(parent_spec))
        prompt = _rebuild_prompt(compact, contract, perception, context)
        # Thinking on DeepSeek spends the token budget on prose and truncates the spec.
        parsed = self.llm_client.complete_json(prompt, timeout=60.0, max_tokens=3500, thinking=False)
        if not parsed:
            return None, ["llm_rebuild_empty"]
        spec = parsed.get("chart_spec") if isinstance(parsed.get("chart_spec"), dict) else parsed
        if not isinstance(spec, dict):
            return None, ["llm_rebuild_not_spec"]
        restored = _restore_primary_data(spec, values, parent_spec)
        _copy_needed_transforms(parent_spec, restored)
        if contract.role in {"Extender", "Analyst"}:
            if _has_invented_y_fields(restored):
                return None, ["extender_invented_fields"]
            if _extender_rule_count(restored) <= _extender_rule_count(parent_spec):
                return None, ["extender_no_new_comparison"]
        if contract.role in {"Adverser", "Amplifier"} and contract.evidence_start is not None:
            self.executor._select_data_range(
                restored,
                {"x_field": contract.x_field, "start": contract.evidence_start, "end": contract.evidence_end},
            )
            if contract.window_kind == "rise_zoom":
                _amplifier_zoom_mark(restored)
            _rescale_y_to_visible_data(restored, contract.y_field, tighten_dual=True)
            _apply_claim_title(restored, contract.agent_claim)
        _sanitize_chart_layout(restored)
        if not self.validator.validate(restored).ok:
            return None, ["llm_rebuild_invalid"]
        if not _render_is_sane(restored, self.renderer):
            return None, ["llm_rebuild_insane_layout"]
        try:
            self.renderer.to_data_url(restored)
        except Exception as exc:  # noqa: BLE001
            return None, [f"render_failed:{exc}"]
        return restored, []

    def _repair_via_llm(
        self,
        parent_spec: dict[str, Any],
        candidate: dict[str, Any],
        contract: FramingContract,
        reasons: list[str],
    ) -> dict[str, Any] | None:
        if self.llm_client is None:
            return None
        compact, values = _stub_primary_data(candidate)
        prompt = (
            "Repair this Vega-Lite chart so the NEW CLAIM is visually inevitable. "
            "Return JSON with key chart_spec. Keep data as "
            f'{{"values": {{"$ref": "{DATA_REF}"}}}}.\n'
            f"Contract: {json.dumps(contract.as_dict(), ensure_ascii=False)}\n"
            f"Verify failures: {reasons}\n"
            f"Current spec: {json.dumps(compact, ensure_ascii=False)[:8000]}\n"
        )
        parsed = self.llm_client.complete_json(prompt, timeout=60.0, max_tokens=3500, thinking=False)
        if not parsed:
            return None
        spec = parsed.get("chart_spec") if isinstance(parsed.get("chart_spec"), dict) else parsed
        if not isinstance(spec, dict):
            return None
        restored = _restore_primary_data(spec, values, parent_spec)
        if not self.validator.validate(restored).ok:
            return None
        return restored


def _prepare_incoming_canvas(parent_spec: dict[str, Any]) -> dict[str, Any]:
    spec = copy.deepcopy(parent_spec)
    layer = spec.get("layer")
    if isinstance(layer, list):
        kept = []
        for item in layer:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            desc = str(item.get("description") or "").lower()
            if "revisio " in desc or "node3 added annotation" in desc:
                continue
            mark = item.get("mark")
            encoding = item.get("encoding") if isinstance(item.get("encoding"), dict) else {}
            text = encoding.get("text") if isinstance(encoding, dict) else None
            if isinstance(mark, dict) and mark.get("type") == "text" and isinstance(text, dict) and text.get("field") == "label":
                continue
            kept.append(item)
        spec["layer"] = kept
    _drop_baseline_field(spec)
    return spec


def _drop_baseline_field(spec: dict[str, Any]) -> None:
    def _unstamp(data_obj: dict[str, Any]) -> None:
        values = data_obj.get("values")
        if not isinstance(values, list):
            return
        for row in values:
            if isinstance(row, dict):
                row.pop(BASELINE_FIELD, None)

    data = spec.get("data")
    if isinstance(data, dict):
        _unstamp(data)
    for item in spec.get("layer") or []:
        if isinstance(item, dict) and isinstance(item.get("data"), dict):
            _unstamp(item["data"])


def _title_text(spec: dict[str, Any] | None) -> str:
    if not isinstance(spec, dict):
        return ""
    title = spec.get("title")
    if isinstance(title, dict):
        text = title.get("text")
        if isinstance(text, list):
            return " ".join(str(part) for part in text)
        return str(text or "")
    return str(title or "")


def _apply_claim_title(spec: dict[str, Any], claim: str) -> None:
    spec["title"] = {"text": claim, "fontSize": 20, "anchor": "start"}


def _metric_from_incoming(incoming_title: str, y_label: str) -> str:
    title = " ".join((incoming_title or "").split())
    lower = title.lower()
    for prefix in ("breaking:", "shocking:", "wake up:"):
        if lower.startswith(prefix):
            title = title[len(prefix) :].strip()
            lower = title.lower()
    title = title.rstrip("!").strip()
    lower = title.lower()
    for sep in (" against ", " climbed ", " surged ", " eased ", " after ", " peaked"):
        idx = lower.find(sep)
        if idx > 3:
            title = title[:idx].strip()
            lower = title.lower()
    short = title.split(",")[0].split(" - ")[0].split(":")[0].strip()
    for sep in (" vs ", " versus "):
        idx = short.lower().find(sep)
        if idx > 3:
            short = short[:idx].strip()
            break
    if 3 <= len(short) <= 64:
        return short
    return y_label or short or "the series"


def _compact_x(value: Any) -> str:
    text = str(value)
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else text


def _fmt_num(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:.1f}"


def _story_rows(spec: dict[str, Any], x_field: str, y_field: str) -> list[dict[str, Any]]:
    values = _primary_values(spec) or []
    return [
        row
        for row in values
        if isinstance(row, dict) and x_field in row and isinstance(row.get(y_field), (int, float))
    ]


def _primary_values(spec: dict[str, Any]) -> list[dict[str, Any]] | None:
    data = spec.get("data")
    if isinstance(data, dict) and isinstance(data.get("values"), list):
        return [row for row in data["values"] if isinstance(row, dict)]
    best: list[dict[str, Any]] = []
    for item in spec.get("layer") or []:
        if not isinstance(item, dict):
            continue
        item_data = item.get("data")
        if isinstance(item_data, dict) and isinstance(item_data.get("values"), list):
            rows = [row for row in item_data["values"] if isinstance(row, dict)]
            if len(rows) > len(best):
                best = rows
    return best or None


def _recent_rows(rows: list[dict[str, Any]], x_field: str, years: int) -> list[dict[str, Any]]:
    if len(rows) < 4:
        return rows
    last = rows[-1].get(x_field)
    try:
        cutoff = float(last) - years
        sliced = [row for row in rows if float(row.get(x_field)) >= cutoff]
        if len(sliced) >= 6:
            return sliced
    except (TypeError, ValueError):
        pass
    keep = max(6, int(len(rows) * 0.2) if years <= 20 else int(len(rows) * 0.35))
    return rows[-keep:]


def _recency_factor(rows: list[dict[str, Any]], end_i: int, x_field: str) -> float:
    try:
        age = float(rows[-1][x_field]) - float(rows[end_i][x_field])
        if age <= 20:
            return 3.0
        if age <= 40:
            return 1.15
        return 0.2
    except (TypeError, ValueError, IndexError):
        return 0.45 + 0.55 * (end_i / max(len(rows) - 1, 1))


def _is_secondary_y(enc: dict[str, Any]) -> bool:
    axis = enc.get("axis")
    return isinstance(axis, dict) and str(axis.get("orient") or "").lower() == "right"


def _incoming_says_up(incoming: str) -> bool | None:
    lower = (incoming or "").lower()
    up = ("surge", "climb", "peak", "rise", "record", "hottest", "breaking", "crisis", "shock", "alarm")
    down = ("ease", "fell", "drop", "declin", "cool", "lowest")
    hit_up = any(token in lower for token in up)
    hit_down = any(token in lower for token in down)
    if hit_up and not hit_down:
        return True
    if hit_down and not hit_up:
        return False
    return None


def _adverser_want_rise(incoming: str, overall_trend: str) -> bool:
    said = _incoming_says_up(incoming)
    if said is not None:
        return not said
    return overall_trend in {"falling", "flat"}


def _window_bounds(n: int) -> tuple[int, float]:
    if n >= 16:
        return 4, 0.72
    if n >= 10:
        return 3, 0.78
    if n >= 7:
        return 3, 0.88
    return 2, 0.94


def _directional_window(
    rows: list[dict[str, Any]], x_field: str, y_field: str, want_rise: bool
) -> dict[str, Any] | None:
    y_vals = [float(r[y_field]) for r in rows]
    n = len(y_vals)
    min_width, max_coverage = _window_bounds(n)
    best: dict[str, Any] | None = None
    best_score = -1.0
    for i in range(0, n - min_width):
        for j in range(i + min_width, n):
            start_v, end_v = y_vals[i], y_vals[j]
            if start_v == 0:
                continue
            if want_rise:
                if end_v <= start_v:
                    continue
                pct = (end_v - start_v) / abs(start_v) * 100
                kind = "rise"
            else:
                if end_v >= start_v:
                    continue
                pct = (start_v - end_v) / abs(start_v) * 100
                kind = "decline"
            coverage = (j - i) / max(n - 1, 1)
            if coverage > max_coverage:
                continue
            recency = _recency_factor(rows, j, x_field)
            score = pct * (1.15 - abs(coverage - 0.35)) * recency
            if score > best_score:
                best_score = score
                best = {
                    "kind": kind,
                    "start_x": rows[i][x_field],
                    "end_x": rows[j][x_field],
                    "start_val": start_v,
                    "end_val": end_v,
                    "pct": pct,
                }
    return best


def _steepest_window(rows: list[dict[str, Any]], x_field: str, y_field: str) -> dict[str, Any] | None:
    rise = _directional_window(rows, x_field, y_field, True)
    fall = _directional_window(rows, x_field, y_field, False)
    candidates = [item for item in (rise, fall) if item is not None]
    if not candidates:
        return _peak_zoom_window(rows, x_field, y_field)
    return max(candidates, key=lambda item: float(item["pct"]))


def _amplifier_zoom_window(
    rows: list[dict[str, Any]], x_field: str, y_field: str, incoming: str = ""
) -> dict[str, Any] | None:
    """Keep the incoming peak (or trough) and crop the left. Percent-from-near-zero
    windows drop the recent spike and make later Amplifier hops look weaker."""
    n = len(rows)
    if n < 5:
        return None
    ys = [float(r[y_field]) for r in rows]
    # Later hops on an already-positive, already-cropped series cannot raise the
    # peak with bars-from-zero. Convert+y-zoom instead. First hop stays a crop.
    already_amplified = not _is_source_like(incoming)
    if already_amplified and min(ys) >= 0 and 12 <= n <= 50:
        zoomed = _amplifier_axis_zoom_window(rows, x_field, y_field)
        if zoomed is not None:
            return zoomed
    peak_i = max(range(n), key=lambda idx: ys[idx])
    trough_i = min(range(n), key=lambda idx: ys[idx])
    net = ys[-1] - ys[0]
    frac = 0.38 if n >= 80 else 0.52 if n >= 40 else 0.62
    keep = max(5, min(n - 2, int(n * frac)))
    if net >= 0 or (ys[peak_i] - ys[0]) >= (ys[0] - ys[trough_i]):
        end_i = min(n - 1, peak_i + min(2, n - 1 - peak_i))
        start_i = max(0, end_i - keep + 1)
        kind = "rise"
    else:
        end_i = min(n - 1, max(trough_i, n - 1))
        start_i = max(0, min(peak_i, end_i - keep + 1))
        kind = "decline"
    if start_i == 0 and n > 8:
        keep = max(5, min(n - 2, int(n * min(frac, 0.48))))
        start_i = max(0, end_i - keep + 1)
    if end_i - start_i < 3 or start_i >= end_i:
        return None
    start_v, end_v = ys[start_i], ys[end_i]
    return {
        "kind": kind,
        "start_x": rows[start_i][x_field],
        "end_x": rows[end_i][x_field],
        "start_val": start_v,
        "end_val": end_v,
        "pct": abs(end_v - start_v) / abs(start_v) * 100 if start_v else 0.0,
    }


def _amplifier_axis_zoom_window(rows: list[dict[str, Any]], x_field: str, y_field: str) -> dict[str, Any] | None:
    n = len(rows)
    ys = [float(r[y_field]) for r in rows]
    peak_i = max(range(n), key=lambda idx: ys[idx])
    end_i = peak_i
    keep = max(8, min(n - 2, int(n * 0.42)))
    search_from = max(0, end_i - keep + 1)
    mid = search_from + max(2, (end_i - search_from) // 2)
    start_i = min(range(search_from, max(search_from + 1, mid)), key=lambda idx: ys[idx])
    if end_i - start_i < 4:
        start_i = search_from
    if start_i <= 0:
        start_i = 1
    if end_i - start_i < 4 or (end_i - start_i + 1) >= n:
        return None
    start_v, end_v = ys[start_i], ys[end_i]
    return {
        "kind": "rise_zoom",
        "start_x": rows[start_i][x_field],
        "end_x": rows[end_i][x_field],
        "start_val": start_v,
        "end_val": end_v,
        "pct": abs(end_v - start_v) / abs(start_v) * 100 if start_v else 0.0,
    }


def _peak_zoom_window(rows: list[dict[str, Any]], x_field: str, y_field: str) -> dict[str, Any] | None:
    n = len(rows)
    if n < 5:
        return None
    ys = [float(r[y_field]) for r in rows]
    peak_i = max(range(n), key=lambda idx: ys[idx])
    keep = max(4, min(n - 1, int(n * 0.45) or 4))
    start_i = max(0, peak_i - keep // 2)
    end_i = min(n - 1, start_i + keep)
    start_i = max(0, end_i - keep)
    if end_i - start_i < 3 or (end_i - start_i + 1) >= n:
        return None
    start_v, end_v = ys[start_i], ys[end_i]
    if start_v == 0:
        return None
    return {
        "kind": "rise" if end_v >= start_v else "decline",
        "start_x": rows[start_i][x_field],
        "end_x": rows[end_i][x_field],
        "start_val": start_v,
        "end_val": end_v,
        "pct": abs(end_v - start_v) / abs(start_v) * 100,
    }


def _undercut_window(rows: list[dict[str, Any]], x_field: str, y_field: str) -> dict[str, Any] | None:
    n = len(rows)
    if n < 4:
        return None
    ys = [float(r[y_field]) for r in rows]
    keep = max(3, n // 2)
    if keep >= n:
        return None
    left_mean = sum(ys[:keep]) / keep
    right_mean = sum(ys[-keep:]) / keep
    if left_mean <= right_mean:
        start_i, end_i = 0, keep - 1
    else:
        start_i, end_i = n - keep, n - 1
    if end_i - start_i < 2 or (end_i - start_i + 1) >= n:
        return None
    start_v, end_v = ys[start_i], ys[end_i]
    if start_v == 0:
        return None
    return {
        "kind": "undercut",
        "start_x": rows[start_i][x_field],
        "end_x": rows[end_i][x_field],
        "start_val": start_v,
        "end_val": end_v,
        "pct": abs(end_v - start_v) / abs(start_v) * 100,
    }


def _is_source_like(title: str) -> bool:
    text = " ".join((title or "").split())
    if len(text) < 4:
        return True
    return _incoming_says_up(text) is None


def _next_amplifier_claim(incoming: str, metric: str, window: dict[str, Any]) -> str:
    text = " ".join((incoming or "").split()).strip()
    kind = str(window.get("kind") or "")
    peak_x = _compact_x(window.get("end_x") if kind in {"rise", "rise_zoom"} else window.get("start_x"))
    peak_val = _fmt_num(window.get("end_val") if kind in {"rise", "rise_zoom"} else window.get("start_val"))
    start = _compact_x(window.get("start_x"))
    end = _compact_x(window.get("end_x"))
    if kind == "rise_zoom":
        return f"BREAKING: {metric} hits {peak_val} ({start}–{end})"
    if _is_source_like(text):
        if kind == "rise":
            return f"{metric} peaked near {peak_x}"
        return f"{metric} dropped after {peak_x}"
    lower = text.lower()
    if not lower.startswith("breaking"):
        clipped = text[:72].rsplit(" ", 1)[0] if len(text) > 72 else text
        return f"BREAKING: {clipped}"
    return f"BREAKING: {metric} hits {peak_val} ({start}–{end})"


def _next_extender_claim(incoming: str, metric: str, kind: int) -> str:
    if kind <= 0:
        return f"{metric} vs the long-run mean"
    if kind == 1:
        return f"{metric}: recent years vs the long-run mean"
    return f"{metric}: early, recent, and long-run means"


def _title_keeps_metric(title: str, metric_label: str, y_field: str) -> bool:
    hay = title.lower()
    label = (metric_label or "").strip().lower()
    if label and label in hay:
        return True
    tokens = [part for part in label.replace("(", " ").replace(")", " ").split() if len(part) >= 3]
    if y_field and len(y_field) >= 3:
        tokens.append(y_field.lower())
    return any(token in hay for token in tokens) if tokens else True


def _has_baseline_layer(spec: dict[str, Any]) -> bool:
    def _walk(items: Any) -> bool:
        if not isinstance(items, list):
            return False
        for item in items:
            if not isinstance(item, dict):
                continue
            if "revisio extender" in str(item.get("description") or "").lower():
                return True
            if _walk(item.get("layer")):
                return True
        return False

    if _walk(spec.get("layer")):
        return True
    values = _primary_values(spec) or []
    return any(isinstance(row, dict) and BASELINE_FIELD in row for row in values[:5])


def _extender_rule_count(spec: dict[str, Any]) -> int:
    count = 0

    def _walk(node: Any) -> None:
        nonlocal count
        if not isinstance(node, dict):
            return
        if "revisio extender" in str(node.get("description") or "").lower():
            count += 1
        for inner in node.get("layer") or []:
            _walk(inner)

    _walk(spec)
    return count


def _data_fields(spec: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    for row in (_primary_values(spec) or [])[:8]:
        if isinstance(row, dict):
            fields.update(str(key) for key in row.keys())
    for as_field, sources in _fold_maps(spec):
        fields.add(as_field)
        fields.update(sources)
    for channel in ("x", "y"):
        enc = _primary_channel(spec, channel)
        if isinstance(enc, dict) and isinstance(enc.get("field"), str):
            fields.add(enc["field"])
    return fields


def _has_invented_y_fields(spec: dict[str, Any]) -> bool:
    known = _data_fields(spec)
    if not known:
        return False
    for channel, enc in _walk_encoding_channels(spec):
        if channel != "y":
            continue
        if enc.get("datum") is not None:
            continue
        field = enc.get("field")
        if not isinstance(field, str) or field == "y_label":
            continue
        if field not in known:
            return True
    return False


def _mean_of_rows(rows: list[dict[str, Any]], y_field: str) -> float | None:
    ys = [float(row[y_field]) for row in rows if isinstance(row.get(y_field), (int, float))]
    if len(ys) < 2:
        return None
    return sum(ys) / len(ys)


def _recent_and_early_rows(
    values: list[dict[str, Any]], x_field: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    n = len(values)
    try:
        last = float(values[-1][x_field])
        recent = [row for row in values if float(row.get(x_field)) >= last - 20]
        early = [row for row in values if float(row.get(x_field)) < last - 40]
    except (TypeError, ValueError, KeyError):
        recent, early = values[-max(6, n // 4) :], values[: max(6, n // 3)]
    if len(recent) < 4:
        recent = values[-max(4, n // 4) :]
    if len(early) < 4:
        early = values[: max(4, n // 3)]
    return recent, early


def _append_extender_rule(spec: dict[str, Any], rule: dict[str, Any]) -> bool:
    layer = spec.get("layer")
    if not isinstance(layer, list) or not layer:
        return False
    if _has_dual_y_axes(spec):
        primary = layer[0]
        if isinstance(primary, dict) and isinstance(primary.get("layer"), list):
            primary["layer"].append(rule)
            return True
        if isinstance(primary, dict):
            layer[0] = {"layer": [primary, rule]}
            return True
    layer.append(rule)
    return True


def _add_baseline_comparison(spec: dict[str, Any], contract: FramingContract) -> bool:
    values = _primary_values(spec)
    if not values:
        return False
    ys = [float(row[contract.y_field]) for row in values if isinstance(row.get(contract.y_field), (int, float))]
    if len(ys) < 2:
        return False
    primary_y = _primary_channel(spec, "y")
    scale_domain = None
    if isinstance(primary_y, dict):
        scale = primary_y.get("scale")
        if isinstance(scale, dict) and isinstance(scale.get("domain"), list):
            scale_domain = list(scale["domain"])

    def _rule(mean_val: float, description: str, color: str) -> dict[str, Any]:
        y_enc: dict[str, Any] = {"datum": mean_val}
        if isinstance(primary_y, dict) and primary_y.get("type"):
            y_enc["type"] = primary_y["type"]
        if scale_domain:
            y_enc["scale"] = {"domain": list(scale_domain)}
        return {
            "description": description,
            "mark": {"type": "rule", "strokeDash": [4, 3], "color": color, "strokeWidth": 1.5},
            "encoding": {"y": y_enc},
        }

    count = _extender_rule_count(spec)
    if count <= 0:
        return _append_extender_rule(spec, _rule(sum(ys) / len(ys), "revisio extender baseline", "#9E9E9E"))
    recent_rows, early_rows = _recent_and_early_rows(values, contract.x_field)
    if count == 1:
        recent_mean = _mean_of_rows(recent_rows, contract.y_field)
        if recent_mean is None:
            return True
        return _append_extender_rule(spec, _rule(recent_mean, "revisio extender recent mean", "#E65100"))
    if count == 2:
        early_mean = _mean_of_rows(early_rows, contract.y_field)
        if early_mean is None:
            return True
        return _append_extender_rule(spec, _rule(early_mean, "revisio extender early mean", "#1565C0"))
    return True


def _strip_node3_overlays(spec: dict[str, Any]) -> None:
    def _clean(node: dict[str, Any]) -> None:
        layers = node.get("layer")
        if not isinstance(layers, list):
            return
        kept: list[Any] = []
        for item in layers:
            if isinstance(item, dict) and str(item.get("description") or "").startswith("Node3 added"):
                continue
            if isinstance(item, dict):
                _clean(item)
            kept.append(item)
        node["layer"] = kept
        if (
            len(kept) == 1
            and isinstance(kept[0], dict)
            and isinstance(kept[0].get("layer"), list)
            and not kept[0].get("mark")
            and not kept[0].get("encoding")
        ):
            node["layer"] = kept[0]["layer"]

    _clean(spec)


def _amplifier_zoom_mark(spec: dict[str, Any]) -> None:
    """Bar-from-zero cannot show a y-zoom. Area/line can fill the frame above 0."""
    _strip_node3_overlays(spec)
    layers = spec.get("layer")
    if isinstance(layers, list):
        kept: list[Any] = []
        for item in layers:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            mark = item.get("mark")
            y_enc = (item.get("encoding") or {}).get("y") if isinstance(item.get("encoding"), dict) else None
            ghost = isinstance(mark, dict) and (mark.get("opacity") == 0 or mark.get("size") == 0)
            if ghost and _is_secondary_y(y_enc if isinstance(y_enc, dict) else {}):
                continue
            kept.append(item)
        spec["layer"] = kept
    resolve = spec.get("resolve")
    if isinstance(resolve, dict):
        scale = resolve.get("scale")
        if isinstance(scale, dict):
            scale.pop("y", None)
            if not scale:
                resolve.pop("scale", None)
        if not resolve:
            spec.pop("resolve", None)
    for item in spec.get("layer") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("description") or "").startswith("Node3 added"):
            continue
        nested = item.get("layer")
        if isinstance(nested, list):
            _amplifier_zoom_mark(item)
            continue
        mark = item.get("mark")
        if isinstance(mark, dict) and mark.get("type") in {"bar", "line"}:
            mark["type"] = "area"
            mark.pop("width", None)
            mark.setdefault("opacity", 0.88)
            mark["line"] = True
        elif isinstance(mark, str) and mark in {"bar", "line"}:
            item["mark"] = {"type": "area", "opacity": 0.88, "line": True}


def _maybe_repackage_mark(spec: dict[str, Any]) -> None:
    for item in spec.get("layer") or []:
        if not isinstance(item, dict):
            continue
        mark = item.get("mark")
        if isinstance(mark, dict) and mark.get("type") in {"bar", "point"}:
            if mark.get("opacity") == 0 or mark.get("size") == 0:
                continue
            mark["type"] = "line"
            mark.setdefault("color", "#6A1B9A")
        elif isinstance(mark, str) and mark in {"bar", "point"}:
            item["mark"] = {"type": "line", "color": "#6A1B9A"}


def _fold_maps(spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    maps: list[tuple[str, list[str]]] = []

    def _from_transforms(transforms: Any) -> None:
        if not isinstance(transforms, list):
            return
        for item in transforms:
            if not isinstance(item, dict) or "fold" not in item:
                continue
            folded = item.get("fold")
            as_fields = item.get("as") or ["key", "value"]
            if isinstance(folded, list) and isinstance(as_fields, list) and len(as_fields) >= 2:
                sources = [str(name) for name in folded]
                maps.append((str(as_fields[1]), sources))

    _from_transforms(spec.get("transform"))
    for layer in spec.get("layer") or []:
        if isinstance(layer, dict):
            _from_transforms(layer.get("transform"))
    return maps


def _row_y_value(row: dict[str, Any], y_field: str, fold_maps: list[tuple[str, list[str]]]) -> float | None:
    raw = row.get(y_field)
    if isinstance(raw, (int, float)):
        return float(raw)
    for as_field, sources in fold_maps:
        if as_field != y_field:
            continue
        total = 0.0
        found = False
        for src in sources:
            val = row.get(src)
            if isinstance(val, (int, float)):
                total += float(val)
                found = True
        if found:
            return total
    return None


def _walk_encoding_channels(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []

    def _walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        encoding = node.get("encoding")
        if isinstance(encoding, dict):
            for channel, enc in encoding.items():
                if isinstance(enc, dict):
                    found.append((str(channel), enc))
        for inner in node.get("layer") or []:
            _walk(inner)

    _walk(spec)
    return found


def _encoded_y_values(spec: dict[str, Any]) -> list[float]:
    values = _primary_values(spec) or []
    folds = _fold_maps(spec)
    ys: list[float] = []
    for channel, enc in _walk_encoding_channels(spec):
        if channel != "y":
            continue
        field = enc.get("field")
        if not isinstance(field, str) or field == "y_label":
            continue
        if _is_secondary_y(enc):
            continue
        primary_field = (_primary_channel(spec, "y") or {}).get("field")
        if isinstance(primary_field, str) and field != primary_field:
            continue
        for row in values:
            if not isinstance(row, dict):
                continue
            val = _row_y_value(row, field, folds)
            if val is not None:
                ys.append(val)
    return ys


def _copy_needed_transforms(parent_spec: dict[str, Any], child_spec: dict[str, Any]) -> None:
    sample = next((row for row in (_primary_values(child_spec) or []) if isinstance(row, dict)), {})
    parent_lookup: dict[str, dict[str, Any]] = {}
    for layer in parent_spec.get("layer") or []:
        if not isinstance(layer, dict) or not layer.get("transform"):
            continue
        parent_lookup[str(layer.get("description") or "")] = layer
        y_enc = (layer.get("encoding") or {}).get("y") if isinstance(layer.get("encoding"), dict) else None
        if isinstance(y_enc, dict) and isinstance(y_enc.get("field"), str):
            parent_lookup[f"y:{y_enc['field']}"] = layer
    for layer in child_spec.get("layer") or []:
        if not isinstance(layer, dict) or layer.get("transform"):
            continue
        encoding = layer.get("encoding") if isinstance(layer.get("encoding"), dict) else {}
        y_field = encoding.get("y", {}).get("field") if isinstance(encoding.get("y"), dict) else None
        if isinstance(y_field, str) and y_field in sample:
            continue
        source = parent_lookup.get(str(layer.get("description") or "")) or parent_lookup.get(f"y:{y_field}")
        if source and source.get("transform"):
            layer["transform"] = copy.deepcopy(source["transform"])


def _svg_size(svg: str) -> tuple[float, float]:
    width_match = re.search(r'\bwidth="([\d.]+)"', svg[:400])
    height_match = re.search(r'\bheight="([\d.]+)"', svg[:400])
    width = float(width_match.group(1)) if width_match else 0.0
    height = float(height_match.group(1)) if height_match else 0.0
    return width, height


def _render_is_sane(spec: dict[str, Any], renderer: SpecRenderer) -> bool:
    if renderer._vlc is None:
        return True
    try:
        svg = renderer._vlc.vegalite_to_svg(spec)
    except Exception:
        return False
    if not isinstance(svg, str) or not svg:
        return False
    _, height = _svg_size(svg)
    expected = float(spec.get("height") or 400)
    if height > expected * 2.4 + 280:
        return False
    mark_hits = sum(
        svg.count(token)
        for token in (
            'aria-roledescription="bar"',
            'aria-roledescription="line"',
            'aria-roledescription="area"',
            'class="mark-rect',
            'class="mark-line',
        )
    )
    return mark_hits > 0


def _reset_floating_guides(spec: dict[str, Any]) -> None:
    title = spec.get("title")
    if isinstance(title, dict) and isinstance(title.get("offset"), (int, float)) and title["offset"] > 16:
        title["offset"] = 8
    padding = spec.get("padding")
    if isinstance(padding, dict):
        padding["left"] = max(int(padding.get("left") or 0), 56)
        padding["bottom"] = max(int(padding.get("bottom") or 0), 36)
        padding["top"] = min(max(int(padding.get("top") or 0), 12), 40)
        padding["right"] = max(int(padding.get("right") or 0), 16)

    def _walk(encoding: Any) -> None:
        if not isinstance(encoding, dict):
            return
        for value in encoding.values():
            if not isinstance(value, dict):
                continue
            axis = value.get("axis")
            if isinstance(axis, dict):
                axis.pop("titleX", None)
                axis.pop("titleY", None)
            legend = value.get("legend")
            if isinstance(legend, dict) and legend.get("orient") == "none":
                legend.pop("legendX", None)
                legend.pop("legendY", None)
                legend["orient"] = "bottom"

    _walk(spec.get("encoding"))
    for item in spec.get("layer") or []:
        if isinstance(item, dict):
            _walk(item.get("encoding"))


def _nice_ticks(lo: float, hi: float) -> list[float]:
    span = hi - lo
    if span <= 0:
        return []
    if span <= 1.5:
        step = 0.25
    elif span <= 4:
        step = 0.5
    elif span <= 12:
        step = 1.0
    else:
        step = 10 ** max(0, len(str(int(span))) - 2)
        if span / step > 8:
            step *= 2
    ticks: list[float] = []
    value = math.ceil(lo / step - 1e-9) * step
    while value <= hi + step * 1e-6 and len(ticks) < 10:
        ticks.append(round(value, 5))
        value = round(value + step, 10)
    return ticks


def _has_dual_y_axes(spec: dict[str, Any]) -> bool:
    orients: set[str] = set()
    for channel, enc in _walk_encoding_channels(spec):
        if channel != "y":
            continue
        axis = enc.get("axis")
        if isinstance(axis, dict):
            orients.add(str(axis.get("orient") or "left").lower())
    return "right" in orients


def _dual_y_factor(spec: dict[str, Any]) -> float:
    left_span = None
    right_span = None
    for channel, enc in _walk_encoding_channels(spec):
        if channel != "y":
            continue
        domain = (enc.get("scale") or {}).get("domain") if isinstance(enc.get("scale"), dict) else None
        if not isinstance(domain, list) or len(domain) < 2:
            continue
        try:
            span = float(domain[1]) - float(domain[0])
        except (TypeError, ValueError):
            continue
        if span <= 0:
            continue
        if _is_secondary_y(enc):
            right_span = span
        else:
            left_span = span
    if left_span and right_span:
        return right_span / left_span
    return 1.8


def _apply_y_domain(enc: dict[str, Any], domain: list[float], ticks: list[float]) -> None:
    scale = enc.get("scale")
    if not isinstance(scale, dict):
        scale = {}
        enc["scale"] = scale
    scale["domain"] = domain
    scale.pop("domainMax", None)
    scale.pop("domainMin", None)
    axis = enc.get("axis")
    if isinstance(axis, dict) and ticks:
        axis["values"] = ticks


def _rescale_y_to_visible_data(spec: dict[str, Any], y_field: str, *, tighten_dual: bool = False) -> bool:
    if _has_dual_y_axes(spec) and not tighten_dual:
        return False
    ys = _encoded_y_values(spec)
    if len(ys) < 2:
        for row in _primary_values(spec) or []:
            val = row.get(y_field)
            if isinstance(val, (int, float)):
                ys.append(float(val))
    if len(ys) < 2:
        return False
    ymin, ymax = min(ys), max(ys)
    span = ymax - ymin
    pad = span * 0.12 if span else (abs(ymax) * 0.05 or 1.0)
    bar = "bar" in _mark_types(spec)
    if bar and ymin >= 0:
        lo = 0.0
        hi = ymax + max(pad, ymax * 0.08)
    elif bar:
        lo = ymin - pad * 0.25
        hi = ymax + pad
    else:
        lo = ymin - pad
        hi = ymax + pad
    domain = [lo, hi]
    ticks = _nice_ticks(lo, hi)
    factor = _dual_y_factor(spec) if _has_dual_y_axes(spec) else None
    updated = 0
    for channel, enc in _walk_encoding_channels(spec):
        if channel != "y":
            continue
        if not isinstance(enc.get("axis"), dict) and not isinstance(enc.get("scale"), dict):
            continue
        if _is_secondary_y(enc):
            if not factor:
                continue
            right_domain = [lo * factor, hi * factor]
            right_ticks = [round(v * factor, 5) for v in ticks]
            _apply_y_domain(enc, right_domain, right_ticks)
            updated += 1
            continue
        _apply_y_domain(enc, domain, ticks)
        updated += 1
    if updated:
        _baseline_area_to_y_domain(spec, lo)
    return updated > 0


def _baseline_area_to_y_domain(spec: dict[str, Any], lo: float | None = None) -> None:
    """Area fills to y=0 by default. A zoomed scale starting above 0 then paints
    below the x-axis, so the axis looks like it sits in the middle of the fill."""
    if lo is None:
        primary = _primary_channel(spec, "y")
        domain = (primary.get("scale") or {}).get("domain") if isinstance(primary.get("scale"), dict) else None
        if not isinstance(domain, list) or not domain:
            return
        try:
            lo = float(domain[0])
        except (TypeError, ValueError):
            return
    if lo <= 0:
        return

    def _walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        mark = node.get("mark")
        is_area = mark == "area" or (isinstance(mark, dict) and mark.get("type") == "area")
        if is_area:
            if isinstance(mark, dict):
                mark["clip"] = True
            else:
                node["mark"] = {"type": "area", "clip": True}
            encoding = node.get("encoding")
            if not isinstance(encoding, dict):
                encoding = {}
                node["encoding"] = encoding
            encoding["y2"] = {"datum": lo}
            y_enc = encoding.get("y")
            if isinstance(y_enc, dict):
                scale = y_enc.get("scale")
                if not isinstance(scale, dict):
                    scale = {}
                    y_enc["scale"] = scale
                scale["zero"] = False
        for inner in node.get("layer") or []:
            _walk(inner)

    _walk(spec)


def _primary_channel(spec: dict[str, Any], channel: str) -> dict[str, Any]:
    def _walk(node: Any) -> dict[str, Any]:
        if not isinstance(node, dict):
            return {}
        overlay = str(node.get("description") or "").startswith("Node3 added")
        encoding = node.get("encoding")
        if not overlay and isinstance(encoding, dict):
            enc = encoding.get(channel)
            if isinstance(enc, dict) and isinstance(enc.get("field"), str) and enc["field"] != "y_label":
                if channel != "y" or not _is_secondary_y(enc):
                    return enc
        for inner in node.get("layer") or []:
            found = _walk(inner)
            if found:
                return found
        return {}

    found = _walk(spec)
    if found:
        return found
    encoding = spec.get("encoding")
    if isinstance(encoding, dict) and isinstance(encoding.get(channel), dict):
        return encoding[channel]
    return {}


def _drop_null_axes(node: dict[str, Any]) -> None:
    encoding = node.get("encoding")
    if isinstance(encoding, dict):
        for value in encoding.values():
            if isinstance(value, dict) and value.get("axis", "missing") is None:
                value.pop("axis", None)
    for item in node.get("layer") or []:
        if isinstance(item, dict):
            item.pop("width", None)
            item.pop("height", None)
            _drop_null_axes(item)


def _unwrap_concat(spec: dict[str, Any]) -> None:
    for key in ("hconcat", "vconcat", "concat"):
        items = spec.get(key)
        if not isinstance(items, list) or not items:
            continue
        inner = next(
            (
                item
                for item in items
                if isinstance(item, dict) and (item.get("mark") or item.get("layer"))
            ),
            items[0],
        )
        if not isinstance(inner, dict):
            return
        kept = {
            key_name: spec[key_name]
            for key_name in ("$schema", "title", "width", "height", "background", "padding", "config", "data")
            if key_name in spec
        }
        merged = {**kept, **inner}
        spec.clear()
        spec.update(merged)
        return


def _has_independent_y(spec: dict[str, Any]) -> bool:
    resolve = spec.get("resolve")
    if not isinstance(resolve, dict):
        return False
    scale = resolve.get("scale")
    return isinstance(scale, dict) and str(scale.get("y") or "").lower() == "independent"


def _align_overlay_y_to_primary(spec: dict[str, Any]) -> None:
    prim_y = _primary_channel(spec, "y")
    if not prim_y:
        return
    for item in spec.get("layer") or []:
        if not isinstance(item, dict):
            continue
        if not str(item.get("description") or "").startswith("Node3 added"):
            continue
        encoding = item.get("encoding")
        if not isinstance(encoding, dict):
            continue
        y_enc = encoding.get("y")
        if not isinstance(y_enc, dict):
            continue
        y_enc.pop("axis", None)
        if prim_y.get("field"):
            if "value" in y_enc and "field" not in y_enc:
                continue
            y_enc.pop("value", None)
            y_enc["field"] = prim_y["field"]
            if prim_y.get("type"):
                y_enc["type"] = prim_y["type"]
            if isinstance(prim_y.get("scale"), dict):
                y_enc["scale"] = copy.deepcopy(prim_y["scale"])


def _nest_node3_overlays(spec: dict[str, Any]) -> None:
    """Keep annotation layers on the primary y scale so they cannot spawn extra axes."""
    _align_overlay_y_to_primary(spec)
    if not _has_dual_y_axes(spec) and not _has_independent_y(spec):
        return
    layers = spec.get("layer")
    if not isinstance(layers, list) or not layers:
        return
    overlays = [
        item
        for item in layers
        if isinstance(item, dict) and str(item.get("description") or "").startswith("Node3 added")
    ]
    if not overlays:
        return
    primary = next(
        (
            item
            for item in layers
            if isinstance(item, dict) and not str(item.get("description") or "").startswith("Node3 added")
        ),
        None,
    )
    if not isinstance(primary, dict):
        return
    kept = [item for item in layers if item is not primary and item not in overlays]
    if isinstance(primary.get("layer"), list):
        primary["layer"].extend(overlays)
        spec["layer"] = [primary, *kept]
        return
    spec["layer"] = [{"layer": [primary, *overlays]}, *kept]


def _sanitize_chart_layout(spec: dict[str, Any]) -> None:
    """Keep axes on the shared plot and y domain covering every encoded series."""
    _unwrap_concat(spec)
    spec.pop("facet", None)
    spec.pop("repeat", None)
    _drop_null_axes(spec)
    _nest_node3_overlays(spec)
    _reset_floating_guides(spec)
    _rescale_y_to_visible_data(spec, "")
    _baseline_area_to_y_domain(spec)


def _mark_types(spec: dict[str, Any]) -> list[str]:
    types: list[str] = []

    def _walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        mark = node.get("mark")
        if isinstance(mark, dict):
            types.append(str(mark.get("type") or ""))
        elif isinstance(mark, str):
            types.append(mark)
        for item in node.get("layer") or []:
            _walk(item)

    _walk(spec)
    return types


def _structural_reasons(parent: dict[str, Any], child: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _title_text(parent) != _title_text(child):
        reasons.append("title")
    parent_n = len(_primary_values(parent) or [])
    child_n = len(_primary_values(child) or [])
    if parent_n and child_n and child_n < parent_n * 0.9:
        reasons.append("data_range")
    parent_layers = parent.get("layer") if isinstance(parent.get("layer"), list) else []
    child_layers = child.get("layer") if isinstance(child.get("layer"), list) else []
    if len(child_layers) > len(parent_layers):
        reasons.append("new_layer")
    if _mark_types(parent) != _mark_types(child):
        reasons.append("mark")
    parent_fields = {k for row in (_primary_values(parent) or [])[:20] if isinstance(row, dict) for k, val in row.items() if isinstance(val, (int, float))}
    child_fields = {k for row in (_primary_values(child) or [])[:20] if isinstance(row, dict) for k, val in row.items() if isinstance(val, (int, float))}
    if child_fields - parent_fields:
        reasons.append("new_field")
    return reasons


def _stub_primary_data(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    compact = copy.deepcopy(spec)
    values = _primary_values(compact) or []
    data = compact.get("data")
    if isinstance(data, dict) and isinstance(data.get("values"), list):
        data["values"] = {"$ref": DATA_REF}
    return compact, copy.deepcopy(values)


def _restore_primary_data(
    spec: dict[str, Any], values: list[dict[str, Any]], parent_spec: dict[str, Any]
) -> dict[str, Any]:
    restored = copy.deepcopy(spec)
    data = restored.get("data")
    if isinstance(data, dict):
        raw = data.get("values")
        if isinstance(raw, dict) and raw.get("$ref") == DATA_REF:
            data["values"] = copy.deepcopy(values)
        elif not isinstance(raw, list) or not raw:
            data["values"] = copy.deepcopy(values)
    elif values:
        restored["data"] = {"values": copy.deepcopy(values)}
    if _primary_values(restored) is None and values:
        restored["data"] = {"values": copy.deepcopy(values)}
    return restored


def _rebuild_prompt(
    compact_spec: dict[str, Any],
    contract: FramingContract,
    perception: str,
    context: dict[str, Any],
) -> str:
    plan_step = context.get("chain_plan_step") if isinstance(context.get("chain_plan_step"), dict) else {}
    return (
        "You are reconstructing a Vega-Lite chart so a NEW CLAIM is visually inevitable. "
        "Start from the incoming parent chart, not the original source. "
        "Keep existing fold/calculate transforms. Do not invent fields. "
        "Do not merely recolor. Return one JSON object only — no prose.\n"
        f"Role: {contract.role}\n"
        f"Platform: {context.get('institution') or 'unknown'}\n"
        f"Incoming claim: {contract.incoming_claim}\n"
        f"Agent claim that MUST be readable from the chart: {contract.agent_claim}\n"
        f"Structural move: {contract.structural_move}\n"
        f"Planned hop: {json.dumps(plan_step, ensure_ascii=False)}\n"
        f"Evidence: {contract.evidence_note}\n"
        f"Perception: {(perception or '')[:500]}\n"
        "Keep data as {\"values\": {\"$ref\": \"" + DATA_REF + "\"}}.\n"
        "Annotations must use datum/field encodings, never pixel x/y.\n"
        "Return JSON: {\"chart_spec\": { ... Vega-Lite v5 ... }, \"taxonomy_ops\": [\"change_title\", ...]}\n"
        f"Parent spec: {json.dumps(compact_spec, ensure_ascii=False)[:9000]}\n"
    )


def _ops_from_contract(contract: FramingContract, reasons: list[str]) -> list[dict[str, Any]]:
    intents = {
        "select_data_range": f"keep {contract.evidence_start}–{contract.evidence_end} from the incoming chart",
        "change_axis_scale": "rebuild y ticks to the visible window",
        "change_title": contract.agent_claim,
        "add_annotation": contract.evidence_note,
        "add_data_variables": "period-mean comparison on the incoming series",
        "change_chart_type": "repackage incoming chart for this platform",
        "delete_source": "drop source cues that contradict the new claim",
    }
    ops: list[dict[str, Any]] = []
    for name in contract.taxonomy_ops:
        ops.append(
            Node3Executor._build_op_record(
                name,
                intents.get(name, contract.structural_move),
                {"intent": intents.get(name, contract.structural_move)},
                "(parent)",
                ",".join(reasons),
                "applied",
                "",
                ["$.title"] if name == "change_title" else ["$.layer[*]"],
            )
        )
    return ops


def _op_layer(operation: str) -> str:
    if operation in {"select_data_range", "add_data_variables", "change_data_granularity"}:
        return "data"
    if operation in {"change_color", "change_chart_type", "change_axis_scale", "simplify_axis"}:
        return "visual"
    return "text"
