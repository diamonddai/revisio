from __future__ import annotations

import json
import random
import re
from typing import Any

import httpx

from app.config.settings import get_settings


class LLMClient:
    """
    V1 pluggable LLM client.
    - enabled=False: deterministic fallback strategy
    - enabled=True: currently still uses fallback logic as placeholder
    """

    def __init__(self, enabled: bool = False) -> None:
        settings = get_settings()
        self.enabled = enabled
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model

    def evaluate_gap(self, persona: dict[str, Any], _context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = _context or {}
        if self.enabled and self.api_key:
            llm_result = self._evaluate_gap_via_llm(persona=persona, context=context)
            if llm_result is not None:
                return llm_result

        return self._evaluate_gap_fallback(persona, context=context)

    def propose_strategy(
        self,
        gap_type: str,
        persona: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        whitelist: list[str] | None = None,
        shift_prior: str = "minor",
        node_a_perception: str = "",
    ) -> dict[str, Any]:
        persona = persona or {}
        context = context or {}
        whitelist = whitelist or []
        if self.enabled and self.api_key:
            llm_result = self._propose_strategy_via_llm(
                gap_type=gap_type,
                persona=persona,
                context=context,
                whitelist=whitelist,
                shift_prior=shift_prior,
                node_a_perception=node_a_perception,
            )
            if llm_result is not None:
                return llm_result
        return self._propose_strategy_fallback(
            gap_type=gap_type,
            persona=persona,
            context=context,
            whitelist=whitelist,
            shift_prior=shift_prior,
        )

    def _evaluate_gap_fallback(self, persona: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        category = str(persona.get("category", "Amplifier"))
        institution = str(persona.get("institution", ""))
        ctx = context or {}
        depth = ctx.get("depth", 1)
        chain_history = ctx.get("chainHistory", [])
        chain_len = len(chain_history) if isinstance(chain_history, list) else 0
        platform_bucket = LLMClient._infer_platform_bucket(ctx)

        # Platform modifiers: social/ugc → more conflict, authority/data → more resonance
        plat_escalate = 1 if platform_bucket in ("t3_social", "t5_ugc") else 0
        plat_dampen = 1 if platform_bucket in ("t1_authority", "t4_data") else 0

        if category == "Noise":
            gap_type = "noise"
            confidence = 0.50
            alignment = "low"
            intensity = "minimal"
        elif category == "Adverser":
            gap_type = "conflict"
            confidence = min(0.78 + 0.05 * chain_len + 0.03 * plat_escalate, 0.95)
            alignment = "low"
            intensity = "substantial"
        elif category in ("Analyst", "Extender"):
            eff_depth = depth + plat_escalate - plat_dampen
            gap_type = "tension" if eff_depth <= 2 else "conflict"
            confidence = min(0.72 + 0.03 * chain_len, 0.90)
            alignment = "medium" if platform_bucket != "t3_social" else "low"
            intensity = "moderate" if eff_depth <= 2 else "substantial"
        elif category == "Bridger":
            gap_type = "resonance"
            confidence = 0.68
            alignment = "high"
            intensity = "minimal"
        elif category == "Amplifier":
            eff_depth = depth + plat_escalate
            gap_type = "tension" if eff_depth <= 1 else "conflict"
            confidence = min(0.72 + 0.04 * chain_len + 0.04 * plat_escalate, 0.92)
            alignment = "medium" if eff_depth <= 1 else "low"
            intensity = "moderate" if eff_depth <= 1 else "substantial"
        else:
            gap_type = "tension"
            confidence = 0.66
            alignment = "medium"
            intensity = "moderate"

        inner_monologue = self._build_perception_monologue(
            category=category,
            institution=institution,
            gap_type=gap_type,
            context=ctx,
        )
        return {
            "inner_monologue": inner_monologue,
            "gap_type": gap_type,
            "confidence": confidence,
            "alignment_with_preference": alignment,
            "identified_gaps": [{"aspect": "narrative", "description": f"depth-aware heuristic: depth={depth}, chain_len={chain_len}"}],
            "expected_modification_intensity": intensity,
            "reasoning": f"depth-aware fallback: role={category}, depth={depth}, accumulated chain steps={chain_len}",
        }

    @staticmethod
    def _propose_strategy_fallback(
        gap_type: str,
        persona: dict[str, Any],
        context: dict[str, Any],
        whitelist: list[str],
        shift_prior: str,
    ) -> dict[str, Any]:
        has_explicit_category = isinstance(persona.get("category"), str) and bool(str(persona.get("category")).strip())
        category = str(persona.get("category", "Amplifier"))
        chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
        has_legend = LLMClient._spec_has_legend(chart_spec if isinstance(chart_spec, dict) else None)
        platform_bucket = LLMClient._infer_platform_bucket(context)
        topic_signals = LLMClient._infer_topic_signals(context=context, chart_spec=chart_spec if isinstance(chart_spec, dict) else None)
        depth = context.get("depth", 1) if isinstance(context, dict) else 1
        chain_history = context.get("chainHistory", []) if isinstance(context, dict) else []
        chain_len = len(chain_history) if isinstance(chain_history, list) else 0

        if gap_type == "noise":
            return {
                "action": "ignore",
                "operations": [],
                "selected_operations": [],
                "operation_rationale": "Narrative mismatch too high; terminate path.",
                "expected_shift_magnitude": "none",
            }

        target_intensity = LLMClient._estimate_modification_intensity(
            gap_type=gap_type,
            category=category,
            platform_bucket=platform_bucket,
            depth=depth,
        )

        if category == "Amplifier":
            title_intent = LLMClient._build_title_intent(
                category=category,
                topic_signals=topic_signals,
                gap_type=gap_type,
                platform_bucket=platform_bucket,
                chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
            )
            annotation_intent = LLMClient._build_annotation_intent(
                category=category,
                topic_signals=topic_signals,
                gap_type=gap_type,
                chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                title_intent=title_intent,
                platform_bucket=platform_bucket,
            )
            # At deeper depths, use more aggressive font, contrast and trendline
            use_trendline = depth >= 3 and platform_bucket in {"t3_social", "t2_media"}
            min_font = 16 if depth >= 3 else 15
            annotation_params = {
                "include_trendline": use_trendline,
                "max_line_chars": 34,
                "min_font_size": min_font,
                "prune_offtopic_annotations": True,
                "narrative_keywords": LLMClient._build_narrative_keywords(topic_signals, title_intent),
            }
            # Deeper Amplifiers use more aggressive color palettes
            palette = "social_contrast" if platform_bucket in {"t2_media", "t3_social"} else "default"
            if depth >= 3:
                palette = "social_contrast"
            selected = [
                LLMClient._build_operation_item(
                    operation="change_color",
                    layer="visual",
                    intent=LLMClient._build_color_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                    ),
                    params={"scope": "chart_global", "palette_style": palette},
                ),
                LLMClient._build_operation_item(
                    operation="change_title",
                    layer="text",
                    intent=title_intent,
                    params={"max_line_chars": 36},
                ),
                LLMClient._build_operation_item(
                    operation="add_annotation",
                    layer="text",
                    intent=annotation_intent,
                    params=annotation_params,
                ),
                LLMClient._build_operation_item(
                    operation="simplify_axis",
                    layer="visual",
                    intent="focus attention on the key trend",
                    params={"target_axis": "x", "mode": "interval_labels", "label_interval": 5},
                ),
            ]
            # At depth >= 3, add axis scale manipulation for more dramatic effect
            if depth >= 3:
                selected.append(
                    LLMClient._build_operation_item(
                        operation="change_axis_scale",
                        layer="visual",
                        intent="narrow axis range to amplify visual change",
                        params={"target_axis": "y", "mode": "narrow_range"},
                    )
                )
            if LLMClient._spec_has_annotation_text(chart_spec if isinstance(chart_spec, dict) else None):
                selected[2] = LLMClient._build_operation_item(
                    operation="change_annotation",
                    layer="text",
                    intent=annotation_intent,
                    params={**annotation_params, "emphasis_style": "amplify"},
                )
            else:
                selected[2] = LLMClient._build_operation_item(
                    operation="add_annotation",
                    layer="text",
                    intent=annotation_intent,
                    params=annotation_params,
                )
        elif category in ("Analyst", "Extender"):
            title_intent = LLMClient._build_title_intent(
                category=category,
                topic_signals=topic_signals,
                gap_type=gap_type,
                platform_bucket=platform_bucket,
                chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
            )
            annotation_intent = LLMClient._build_annotation_intent(
                category=category,
                topic_signals=topic_signals,
                gap_type=gap_type,
                chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                title_intent=title_intent,
                platform_bucket=platform_bucket,
            )
            annotation_params_analyst = {
                "include_trendline": False,
                "max_line_chars": 34,
                "min_font_size": 14,
                "prune_offtopic_annotations": True,
                "narrative_keywords": LLMClient._build_narrative_keywords(topic_signals, title_intent),
            }
            # Extender should use change_annotation when parent already has one (replace with expanded topic)
            has_existing_annotation = LLMClient._spec_has_annotation_text(chart_spec if isinstance(chart_spec, dict) else None)
            ann_op = "change_annotation" if has_existing_annotation else "add_annotation"

            # Title is always the core operation — expanding the topic to a related domain
            selected = [
                LLMClient._build_operation_item(
                    operation="change_title",
                    layer="text",
                    intent=title_intent,
                    params={"max_line_chars": 36},
                ),
                LLMClient._build_operation_item(
                    operation=ann_op,
                    layer="text",
                    intent=annotation_intent,
                    params=annotation_params_analyst,
                ),
            ]
            # ~50% chance of a global color change; when included, 40% analytical palette
            color_roll = random.random()
            if color_roll < 0.5:
                if color_roll < 0.2:
                    analytical_palettes = {
                        "t1_authority": "#4A148C analytical deep-purple for structured insight",
                        "t2_media": "#5C6BC0 analytical indigo for interpretive context",
                        "t3_social": "#7E57C2 analytical purple for discourse framing",
                        "t4_data": "#00695C analytical teal for data-driven depth",
                        "t5_ugc": "#006064 analytical dark-cyan for grassroots analysis",
                        "t6_blog": "#4527A0 analytical deep-indigo for editorial inquiry",
                    }
                    color_intent = analytical_palettes.get(platform_bucket, "#5C6BC0 analytical indigo")
                else:
                    color_intent = LLMClient._build_color_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                    )
                selected.append(
                    LLMClient._build_operation_item(
                        operation="change_color",
                        layer="visual",
                        intent=color_intent,
                        params={"scope": "chart_global", "palette_style": "default"},
                    )
                )
            if not has_legend:
                selected.append(
                    LLMClient._build_operation_item(
                        operation="add_legend",
                        layer="text",
                        intent="emphasize group differences",
                    )
                )
        elif category == "Adverser":
            _cs = chart_spec if isinstance(chart_spec, dict) else None
            _x_summary = LLMClient._extract_x_series_range(_cs)
            _x_field = _x_summary["x_field"] if _x_summary else "x"
            _x_values = _x_summary["x_values"] if _x_summary else []

            # For long temporal datasets, prefer a broad recent window
            _is_long_temporal = (
                len(_x_values) > 100
                and any(isinstance(v, str) and len(v) >= 7 for v in _x_values[:5])
            )

            if _is_long_temporal:
                recent_idx = max(0, len(_x_values) - min(180, len(_x_values) * 3 // 10))
                range_params: dict[str, Any] = {
                    "x_field": _x_field,
                    "start": _x_values[recent_idx],
                    "end": _x_values[-1],
                }
                title_intent = LLMClient._build_title_intent(
                    category=category,
                    topic_signals=topic_signals,
                    gap_type=gap_type,
                    platform_bucket=platform_bucket,
                    chart_spec=_cs,
                )
                annotation_intent = LLMClient._build_annotation_intent(
                    category=category,
                    topic_signals=topic_signals,
                    gap_type=gap_type,
                    chart_spec=_cs,
                    title_intent=title_intent,
                )
            else:
                adverser_decline = LLMClient._find_decline_window(_cs)
                if adverser_decline:
                    range_params = {
                        "x_field": _x_field,
                        "start": adverser_decline["start_x"],
                        "end": adverser_decline["end_x"],
                    }
                    _sx = adverser_decline["start_x"]
                    _ex = adverser_decline["end_x"]
                    _sv = adverser_decline["start_val"]
                    _ev = adverser_decline["end_val"]
                    title_intent = LLMClient._build_title_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                        chart_spec=_cs,
                    )
                    _is_climate = bool(topic_signals & {"climate", "temperature", "temp"})
                    if _is_climate:
                        annotation_intent = f"Temperature dropped from {_sv:.2f}°C to {_ev:.2f}°C between {_sx} and {_ex}."
                    elif "covid" in topic_signals:
                        _pct = adverser_decline.get("pct", 0)
                        annotation_intent = f"Deaths fell {_pct:.0f}% — from {_sv:,.0f} to {_ev:,.0f} — between week {_sx} and week {_ex}."
                    else:
                        annotation_intent = f"Declined from {_sv:,.0f} to {_ev:,.0f} between {_sx} and {_ex}."
                else:
                    range_params = LLMClient._build_select_data_range_params(chart_spec=_cs, category=category)
                    title_intent = LLMClient._build_title_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                        chart_spec=_cs,
                    )
                    annotation_intent = LLMClient._build_annotation_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        chart_spec=_cs,
                        title_intent=title_intent,
                    )
            selected = [
                LLMClient._build_operation_item(
                    operation="select_data_range",
                    layer="data",
                    intent="focus on window supporting counter narrative",
                    params=range_params,
                ),
                LLMClient._build_operation_item(
                    operation="change_title",
                    layer="text",
                    intent=title_intent,
                    params={"max_line_chars": 34},
                ),
                LLMClient._build_operation_item(
                    operation="delete_source",
                    layer="text",
                    intent="reduce source attribution cues",
                ),
                LLMClient._build_operation_item(
                    operation="change_color",
                    layer="visual",
                    intent=LLMClient._build_color_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                    ),
                    params={
                        "scope": "chart_global",
                        "palette_style": "social_contrast" if platform_bucket in {"t2_media", "t3_social"} else "default",
                    },
                ),
                LLMClient._build_operation_item(
                    operation="add_annotation",
                    layer="text",
                    intent=annotation_intent,
                    params={
                        "include_trendline": False,
                        "max_line_chars": 34,
                        "min_font_size": 14,
                        "prune_offtopic_annotations": True,
                        "narrative_keywords": LLMClient._build_narrative_keywords(topic_signals, title_intent),
                    },
                ),
                LLMClient._build_operation_item(
                    operation="simplify_axis",
                    layer="visual",
                    intent="focus attention on the key period",
                    params={"target_axis": "x", "mode": "interval_labels", "label_interval": 5},
                ),
            ]
        elif category == "Bridger":
            selected = [
                LLMClient._build_operation_item(
                    operation="change_chart_type",
                    layer="visual",
                    intent="convert to area chart for accessible institutional presentation",
                ),
                LLMClient._build_operation_item(
                    operation="change_color",
                    layer="visual",
                    intent="apply purple institutional palette for bridger role",
                    params={"scope": "chart_global", "palette_style": "default"},
                ),
            ]
        else:
            selected = [
                LLMClient._build_operation_item(
                    operation="change_color",
                    layer="visual",
                    intent="align visual emphasis with neutral communication",
                    params={"scope": "chart_global", "palette_style": "default"},
                ),
                LLMClient._build_operation_item(
                    operation="change_title",
                    layer="text",
                    intent=LLMClient._build_title_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                        chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                    ),
                    params={"max_line_chars": 34},
                ),
                LLMClient._build_operation_item(
                    operation="add_annotation",
                    layer="text",
                    intent="add concise context note",
                    params={"include_trendline": False, "max_line_chars": 32},
                ),
            ]

        if whitelist:
            selected = [item for item in selected if item["operation"] in whitelist]
        if selected:
            selected = LLMClient._trim_selected_ops(selected=selected, target_intensity=target_intensity)
        if category == "Amplifier" and platform_bucket == "t2_media":
            selected = LLMClient._ensure_operation_present(
                selected=selected,
                op_item=LLMClient._build_operation_item(
                    operation="change_color",
                    layer="visual",
                    intent=LLMClient._build_color_intent(
                        category=category,
                        topic_signals=topic_signals,
                        gap_type=gap_type,
                        platform_bucket=platform_bucket,
                    ),
                    params={"scope": "chart_global", "palette_style": "social_contrast"},
                ),
                max_len=5,
            )
        if category == "Bridger":
            selected = [item for item in selected if item.get("operation") in {"change_color", "change_chart_type"}]
        if not selected:
            if category == "Bridger":
                return {
                    "action": "forward",
                    "operations": [],
                    "selected_operations": [],
                    "operation_rationale": "Bridger is constrained to change_color/change_chart_type; no allowed op remained after whitelist.",
                    "expected_shift_magnitude": "none",
                }
            selected = [
                LLMClient._build_operation_item(
                    operation="add_annotation",
                    layer="text",
                    intent="reinforce current interpretation",
                    params={"include_trendline": False, "max_line_chars": 34},
                )
            ]

        expected_shift = LLMClient._estimate_shift_magnitude(
            category=category,
            selected=selected,
            platform_bucket=platform_bucket,
            depth=depth,
        )
        if not has_explicit_category and shift_prior in {"minor", "sig", "major"}:
            expected_shift = shift_prior

        if gap_type == "resonance" and target_intensity == "minimal":
            # Keep at least 2 ops (color + title) so platform differences are visible
            resonance_ops = selected[:2] if len(selected) >= 2 else selected
            return {
                "action": "forward",
                "operations": [item["operation"] for item in resonance_ops],
                "selected_operations": resonance_ops,
                "operation_rationale": (
                    "High alignment with parent framing; apply lightweight operations "
                    "while keeping role/platform signature visible."
                ),
                "expected_shift_magnitude": expected_shift,
            }
        return {
            "action": "modify",
            "operations": [item["operation"] for item in selected],
            "selected_operations": selected,
            "operation_rationale": (
                f"Role signature ({category}) and platform context ({platform_bucket}) "
                "drive who/where/how aligned operation selection."
            ),
            "expected_shift_magnitude": expected_shift if expected_shift != "none" else (
                shift_prior if shift_prior in {"minor", "sig", "major"} else "significant"
            ),
        }

    @staticmethod
    def _trim_selected_ops(selected: list[dict[str, Any]], target_intensity: str) -> list[dict[str, Any]]:
        if target_intensity == "minimal":
            return selected[:2]
        if target_intensity == "moderate":
            return selected[:3]
        return selected[:5]

    @staticmethod
    def _build_operation_item(
        operation: str,
        layer: str,
        intent: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "operation": operation,
            "layer": layer,
            "intent": intent,
            "params": params or {},
        }

    @staticmethod
    def _ensure_operation_present(selected: list[dict[str, Any]], op_item: dict[str, Any], max_len: int) -> list[dict[str, Any]]:
        if any(item.get("operation") == op_item.get("operation") for item in selected):
            return selected
        # Insert near front to ensure execution priority.
        merged = [op_item, *selected]
        return merged[:max_len]

    @staticmethod
    def _build_select_data_range_params(chart_spec: dict[str, Any] | None, category: str) -> dict[str, Any]:
        summary = LLMClient._extract_x_series_range(chart_spec)
        if summary is None:
            return {}
        x_values = summary["x_values"]
        if len(x_values) < 3:
            return {}
        if category == "Adverser":
            # Find the steepest decline window to support counter-narrative
            decline = LLMClient._find_decline_window(chart_spec)
            if decline:
                return {
                    "x_field": summary["x_field"],
                    "start": decline["start_x"],
                    "end": decline["end_x"],
                }
            # Fallback: use last 30% (recent years — more convincing for counter-narrative)
            start_idx = max(0, int(len(x_values) * 0.7))
            end_idx = len(x_values) - 1
        else:
            start_idx = max(0, int(len(x_values) * 0.25))
            end_idx = len(x_values) - 1
        return {
            "x_field": summary["x_field"],
            "start": x_values[start_idx],
            "end": x_values[end_idx],
        }

    @staticmethod
    def _estimate_modification_intensity(gap_type: str, category: str, platform_bucket: str, depth: int = 1) -> str:
        if gap_type == "resonance" and depth <= 1:
            if platform_bucket in ("t3_social", "t5_ugc"):
                return "moderate"
            return "moderate"
        if gap_type == "resonance" and depth >= 2:
            return "substantial" if platform_bucket in ("t3_social", "t5_ugc") else "moderate"
        if category == "Adverser":
            return "substantial"
        if platform_bucket in ("t3_social", "t5_ugc"):
            return "substantial"
        if platform_bucket in ("t1_authority", "t4_data"):
            return "moderate" if depth <= 2 else "substantial"
        if depth >= 3:
            return "substantial"
        if gap_type == "tension":
            return "moderate" if depth <= 2 else "substantial"
        return "substantial"

    @staticmethod
    def _estimate_shift_magnitude(category: str, selected: list[dict[str, Any]], platform_bucket: str, depth: int = 1) -> str:
        if not selected:
            return "none"
        layers = {item.get("layer") for item in selected}
        count = len(selected)
        # Depth-driven escalation: deeper positions produce larger shifts
        depth_bonus = max(0, depth - 1)
        _UP = {"none": "minor", "minor": "sig", "sig": "major", "major": "major"}
        if category == "Adverser":
            base = "major" if (count >= 3 and len(layers) >= 2) else "sig"
        elif count >= 3 or len(layers) >= 2:
            base = "sig"
        elif platform_bucket in ("t3_social", "t5_ugc") and count >= 2:
            base = "sig"
        else:
            base = "minor"
        result = base
        for _ in range(depth_bonus):
            result = _UP.get(result, result)
        return result

    @staticmethod
    def _detect_current_mark(chart_spec: dict[str, Any] | None) -> str:
        """Return the primary mark type of the current chart spec (e.g. 'bar', 'line')."""
        if not chart_spec:
            return "unknown"
        mark = chart_spec.get("mark")
        if isinstance(mark, str):
            return mark.lower()
        if isinstance(mark, dict):
            return str(mark.get("type", "unknown")).lower()
        layer = chart_spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if isinstance(item, dict):
                    lm = item.get("mark")
                    if isinstance(lm, str):
                        return lm.lower()
                    if isinstance(lm, dict):
                        return str(lm.get("type", "unknown")).lower()
        return "unknown"

    @staticmethod
    def _suggest_bridger_chart_type(current_mark: str, chart_spec: dict[str, Any] | None) -> str | None:
        """Suggest an alternative chart type for Bridger on data platforms.

        Data platforms often convert bar charts to line charts for time-series,
        or area charts for cumulative data. Returns None if no change is warranted.
        """
        _has_temporal = False
        if chart_spec:
            enc = chart_spec.get("encoding", {})
            x_enc = enc.get("x", {})
            if isinstance(x_enc, dict):
                x_type = str(x_enc.get("type", "")).lower()
                x_tu = x_enc.get("timeUnit")
                _has_temporal = x_type in ("temporal", "ordinal") or x_tu is not None

        if current_mark == "bar" and _has_temporal:
            return "line"
        if current_mark == "bar":
            return "line"
        if current_mark in ("point", "circle"):
            return "line"
        return None

    @staticmethod
    def _infer_platform_bucket(context: dict[str, Any]) -> str:
        institution = str(context.get("institution", "")).lower()
        if any(token in institution for token in ("政府", "官方", "international", "gov", "research", "科研", "university")):
            return "t1_authority"
        # Data platforms have distinct framing style
        if any(token in institution for token in ("data platform", "数据平台", "database", "statistics", "stat", "third-party data")):
            return "t4_data"
        # Check social/community BEFORE generic "media"
        if any(token in institution for token in ("ugc", "论坛", "forum", "reddit", "online community")):
            return "t5_ugc"
        if any(token in institution for token in ("social", "社区", "twitter", "youtube", "个人", "community", "tiktok", "instagram")):
            return "t3_social"
        if any(token in institution for token in ("blog", "博客", "机构博客", "institutional blog", "personal blog")):
            return "t6_blog"
        if any(token in institution for token in ("news", "新闻", "第三方", "media", "机构博客", "institutional")):
            return "t2_media"
        if "platform" in institution:
            return "t4_data"
        return "unknown"

    @staticmethod
    def _infer_topic_signals(context: dict[str, Any], chart_spec: dict[str, Any] | None) -> set[str]:
        text_parts: list[str] = []
        for key in ("topic", "description"):
            value = context.get(key)
            if isinstance(value, str):
                text_parts.append(value.lower())
        if isinstance(chart_spec, dict):
            title = chart_spec.get("title")
            if isinstance(title, str):
                text_parts.append(title.lower())
            elif isinstance(title, dict) and isinstance(title.get("text"), str):
                text_parts.append(str(title["text"]).lower())
        text = " ".join(text_parts)
        signals: set[str] = set()
        if any(token in text for token in ("deforestation", "amazon", "forest", "去森林化", "森林砍伐")):
            signals.add("deforestation")
        if any(token in text for token in ("climate", "warming", "temperature", "气候", "温度")):
            signals.add("climate")
        if any(token in text for token in ("covid", "coronavirus", "pandemic", "疫情", "新冠")):
            signals.add("covid")
        if any(token in text for token in ("vaccine", "health", "疫苗", "医疗", "excess death", "mortality")):
            signals.add("health")
        if any(token in text for token in ("inflation", "economy", "unemployment", "通胀", "失业", "经济")):
            signals.add("economy")
        if any(token in text for token in ("immigration", "border", "移民", "边境")):
            signals.add("immigration")
        return signals

    @staticmethod
    def _intent_supports_trend(
        intent_text: str,
        topic_signals: set[str],
        series: dict[str, Any] | None,
    ) -> bool:
        """Return True if the intent text supports (rather than opposes) the data trend."""
        if not intent_text:
            return False
        rising_keywords = {"warming", "surge", "rising", "increase", "highest", "accelerat",
                           "intensif", "soar", "record high", "century of warming", "rapid increase"}
        falling_keywords = {"cooling", "decline", "drop", "fall", "low", "stall", "slow",
                            "recovery", "stabiliz", "eased", "fell", "counter"}
        supports_rise = any(kw in intent_text for kw in rising_keywords)
        supports_fall = any(kw in intent_text for kw in falling_keywords)
        if series is not None:
            trend_rising = series.get("last_y", 0) > series.get("first_y", 0)
            if trend_rising and supports_rise and not supports_fall:
                return True
            if not trend_rising and supports_fall and not supports_rise:
                return True
        # No series: heuristic — climate rising keywords without counter-words
        if "climate" in topic_signals and supports_rise and not supports_fall:
            return True
        return False

    @staticmethod
    def _extract_axis_title(chart_spec: dict[str, Any] | None, target_field: str, axis: str = "y") -> str | None:
        """Extract the human-readable axis title for a given field from Vega-Lite spec.
        First tries exact field match, then falls back to any axis title for that channel.
        """
        if not isinstance(chart_spec, dict):
            return None
        first_any_title: str | None = None

        def _from_enc(enc: dict[str, Any] | None) -> str | None:
            nonlocal first_any_title
            if not isinstance(enc, dict):
                return None
            ch = enc.get(axis)
            if not isinstance(ch, dict):
                return None
            ax = ch.get("axis")
            if isinstance(ax, dict) and isinstance(ax.get("title"), str):
                t = ax["title"]
                if first_any_title is None:
                    first_any_title = t
                if ch.get("field") == target_field:
                    return t
            return None

        result = _from_enc(chart_spec.get("encoding"))
        if result:
            return result
        for layer in (chart_spec.get("layer") or []):
            if not isinstance(layer, dict):
                continue
            result = _from_enc(layer.get("encoding"))
            if result:
                return result
        # Fallback: return any axis title found (same channel, different field)
        return first_any_title

    @staticmethod
    def _humanize_field_name(field: str) -> str:
        """Convert raw Vega-Lite field names to human-readable labels.
        'excess_deaths_per_100k' → 'Excess Deaths per 100k'
        'global_temp_anomaly_c' → 'Global Temp Anomaly c'
        Keeps short words (per, in, of, the) lowercase.
        """
        if not field:
            return ""
        stop_words = {"per", "in", "of", "the", "and", "or", "at", "by", "to"}
        words = field.replace("_", " ").replace("-", " ").split()
        result = " ".join(
            w if w in stop_words else w.capitalize()
            for w in words
        )
        # Always capitalize first word
        if result:
            result = result[0].upper() + result[1:]
        return result

    @staticmethod
    def _build_chart_data_summary(chart_spec: dict[str, Any] | None, context: dict[str, Any] | None = None) -> str:
        """Build a clear, role-agnostic data summary for LLM prompts.
        Explicitly marks the source title as upstream framing to be changed,
        and avoids confusing pct_change when first_y=0 (wave patterns).
        """
        lines: list[str] = []
        spec = chart_spec or {}
        ctx = context or {}

        # Source chart title — mark as upstream framing, not the target
        raw_title = spec.get("title", "") or ctx.get("description", "") or ""
        if isinstance(raw_title, dict):
            raw_title = raw_title.get("text", "") or ""
        if raw_title:
            lines.append("SOURCE CHART TITLE (this is the UPSTREAM framing — your role will REFRAME it):")
            lines.append(f'  "{raw_title}"')
            lines.append("")

        # Series data summary using highest-CV story field
        series = LLMClient._extract_xy_series_summary(chart_spec)
        if series:
            y_field = series.get("y_field", "")
            y_label_raw = series.get("y_label") or LLMClient._humanize_field_name(y_field)
            xl = series.get("x_label") or ""
            trend = series["trend"]
            first_y = series["first_y"]
            last_y = series["last_y"]
            peak_y = series["peak_y"]
            peak_x = series["peak_x"]
            first_x = series["first_x"]
            last_x = series["last_x"]

            lines.append("STORY DATA (craft your narrative from this):")
            lines.append(f"  Metric: {y_label_raw} (field='{y_field}', highest-variance story field)")
            if xl:
                lines.append(f"  X-axis: {xl}")
            lines.append(f"  Period: {first_x} → {last_x}")

            # When first_y=0, the standard pct (last/peak) is misleading (-69% looks like falling)
            # Use plain language describing the wave/surge pattern instead
            if first_y == 0 and last_y > 0:
                lines.append(
                    f"  Trend: RISING — started at 0 (no prior cases), surged to peak "
                    f"{peak_y:,.0f} at {peak_x}, currently at {last_y:,.0f} and rising again"
                )
            elif trend == "rising" and first_y != 0:
                pct = (last_y - first_y) / abs(first_y) * 100
                lines.append(
                    f"  Trend: RISING (+{pct:.1f}%) — from {first_y:,.0f} to {last_y:,.0f} "
                    f"(peak: {peak_y:,.0f} at {peak_x})"
                )
            elif trend == "falling" and first_y != 0:
                pct = (last_y - first_y) / abs(first_y) * 100
                lines.append(
                    f"  Trend: FALLING ({pct:.1f}%) — from {first_y:,.0f} to {last_y:,.0f} "
                    f"(peak: {peak_y:,.0f} at {peak_x})"
                )
            else:
                lines.append(f"  Trend: FLAT — {first_y:,.0f} → {last_y:,.0f} (peak: {peak_y:,.0f} at {peak_x})")
        else:
            lines.append("(No numeric series data available)")

        return "\n".join(lines)

    @staticmethod
    def _infer_story_field_label(y_field: str, y_label_raw: str, chart_spec: dict[str, Any] | None) -> str:
        """Try to give a meaningful name to short/cryptic field names like 'c', 'nc', 'avg'.
        Uses fold transform definitions and chart title context."""
        if not chart_spec:
            return y_label_raw
        # Check for fold transform: {"fold": ["nc", "c"], "as": ["cause_raw", "deaths"]}
        # Look through layer transforms for a calculate that maps this field to a readable label
        for layer in (chart_spec.get("layer") or []):
            if not isinstance(layer, dict):
                continue
            for transform in (layer.get("transform") or []):
                if not isinstance(transform, dict):
                    continue
                # {"calculate": "datum.cause_raw === 'c' ? 'Deaths involving COVID-19' : ...", "as": ...}
                calc = transform.get("calculate", "")
                if isinstance(calc, str) and f"'{y_field}'" in calc:
                    # Extract the mapped label: look for 'Deaths involving ...' pattern
                    import re as _re
                    match = _re.search(r"'([^']+)'", calc.split(f"'{y_field}'")[-1])
                    if match:
                        return match.group(1)
        return y_label_raw

    def _build_perception_monologue(
        self,
        category: str,
        institution: str,
        gap_type: str,
        context: dict[str, Any],
    ) -> str:
        """Build a data-grounded inner monologue for NodeA fallback.
        Each role perceives the chart differently based on actual data insight.
        Now also incorporates depth and chain history awareness.
        """
        chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
        depth = context.get("depth", 1)
        chain_history = context.get("chainHistory", [])
        chain_len = len(chain_history) if isinstance(chain_history, list) else 0
        series = self._extract_xy_series_summary(chart_spec if isinstance(chart_spec, dict) else None)
        raw_title = ""
        if isinstance(chart_spec, dict):
            t = chart_spec.get("title", "")
            raw_title = (t.get("text") if isinstance(t, dict) else str(t)) if t else ""

        if not series:
            return f"I am a {category} ({institution or 'unknown institution'}). I see a chart about this topic and will apply my role-specific framing."

        yl = self._humanize_field_name(series["y_label"])
        trend = series["trend"]
        peak_x = series["peak_x"]
        peak_y = series["peak_y"]
        first_x = series["first_x"]
        last_x = series["last_x"]
        first_y = series["first_y"]
        last_y = series["last_y"]
        pct = series.get("pct_change")
        pct_str = f" ({pct:+.1f}%)" if pct is not None else ""

        inst_str = f" at {institution}" if institution else ""
        topic_hint = raw_title if raw_title else yl

        # Chain awareness suffix: what prior agents did
        chain_suffix = ""
        if chain_len > 0 and isinstance(chain_history, list):
            prev = chain_history[-1] if chain_history else {}
            prev_role = prev.get("agent_role", "unknown")
            prev_ops = prev.get("operations", [])
            prev_ops_str = ", ".join(prev_ops) if isinstance(prev_ops, list) else str(prev_ops)
            chain_suffix = (
                f" The previous agent was a {prev_role} who performed [{prev_ops_str}]. "
                f"After {chain_len} step(s) of modification, I need to apply my own distinct perspective."
            )

        depth_note = ""
        if depth >= 3:
            depth_note = f" At depth {depth}, the framing has already shifted significantly from the source — my modifications will be pronounced."
        elif depth == 2:
            depth_note = f" At depth {depth}, there is already some framing shift — I will make noticeable changes reflecting my role."

        if category == "Bridger":
            return (
                f"I am an objective source{inst_str}. The chart '{topic_hint}' shows {yl} is {trend} "
                f"from {first_x} to {last_x}{pct_str} (peak: {peak_y:.0f} at {peak_x}). "
                f"My job is to present this data factually and neutrally.{chain_suffix}"
            )
        elif category == "Amplifier":
            if trend == "rising":
                return (
                    f"I am a {category}{inst_str}. I see '{topic_hint}' — {yl} is rising to a peak of "
                    f"{peak_y:.0f} at {peak_x}, and currently at {last_y:.0f} in {last_x}{pct_str}. "
                    f"I want to amplify this alarming upward trend with a punchy, urgent headline.{chain_suffix}{depth_note}"
                )
            elif trend == "falling":
                return (
                    f"I am a {category}{inst_str}. I see {yl} declining{pct_str} from {first_x} to {last_x}. "
                    f"Peak was {peak_y:.0f} at {peak_x}. "
                    f"I want to dramatize this — write a headline emphasizing the severity of the fall.{chain_suffix}{depth_note}"
                )
            else:
                return (
                    f"I am a {category}{inst_str}. The chart shows {yl} with a flat trend, "
                    f"but peaked at {peak_y:.0f} at {peak_x}. "
                    f"I will highlight this peak to create urgency.{chain_suffix}{depth_note}"
                )
        elif category in ("Analyst", "Extender"):
            return (
                f"I am an {category}{inst_str}. I see '{topic_hint}' — {yl} is {trend} "
                f"over {first_x}–{last_x}, peaking at {peak_y:.0f} at {peak_x}{pct_str}. "
                f"Rather than just report this number, I want to expand the discussion — "
                f"connecting {yl} trends to broader policy, health, or social implications.{chain_suffix}{depth_note}"
            )
        elif category == "Adverser":
            return (
                f"I am an {category}{inst_str}. The chart claims {yl} is {trend} overall "
                f"(peak: {peak_y:.0f} at {peak_x}). "
                f"But I will find a specific window where {yl} goes AGAINST this trend — "
                f"I'll select only that declining segment and write a counter-headline to dispute the overall narrative.{chain_suffix}{depth_note}"
            )
        else:
            return (
                f"I am a {category}{inst_str}. I see {yl} {trend} from {first_x} to {last_x}. "
                f"I will decide how to best frame this for my audience.{chain_suffix}{depth_note}"
            )

    @staticmethod
    def _build_title_intent(
        category: str,
        topic_signals: set[str],
        gap_type: str,
        platform_bucket: str,
        chart_spec: dict[str, Any] | None,
    ) -> str:
        parent_title = LLMClient._extract_title(chart_spec)
        series = LLMClient._extract_xy_series_summary(chart_spec)

        # ── Extract rich context from actual data ────────────────────────────
        y_label = LLMClient._humanize_field_name(series["y_label"]) if series else ""
        trend = series.get("trend", "") if series else ""
        peak_y = series["peak_y"] if series else None
        peak_x = series["peak_x"] if series else None
        first_x = series.get("first_x", "") if series else ""
        last_x = series.get("last_x", "") if series else ""
        pct_change = series.get("pct_change") if series else None
        # Compact substrate for intent descriptions (use parent title when possible)
        substrate = (parent_title.split("–")[0].split("-")[0].strip()[:45] if parent_title
                     else (y_label or "the data"))
        metric = y_label or substrate

        # ── Amplifier: 收窄+放大 — narrate the most dramatic data aspect ──────
        # Every topic × platform combination produces a distinct title
        if category == "Amplifier":
            if "deforestation" in topic_signals:
                if platform_bucket == "t3_social":
                    return f"title: SHOCKING: Amazon Deforestation PEAKED at {peak_x}" if peak_x else "title: WAKE UP: Amazon Deforestation Highest Since 2006"
                if platform_bucket in ("t5_ugc",):
                    return f"title: The Amazon crisis peaked around {peak_x} — why isn't anyone talking about this?" if peak_x else "title: Why Is Nobody Talking About Amazon Deforestation?"
                if platform_bucket == "t2_media":
                    return f"title: Deforestation Rates Hit Critical Peak Near {peak_x}" if peak_x else "title: Amazon Deforestation Reaches Alarming High"
                if platform_bucket == "t1_authority":
                    return f"title: Peak Deforestation Rates Recorded at {peak_x}" if peak_x else "title: Maximum Deforestation Rate Recorded"
                if platform_bucket == "t4_data":
                    return f"title: Deforestation Rate Maximum: {peak_y:,.0f} km² at {peak_x}" if peak_x and peak_y else "title: Peak Rate Deforestation Statistics"
                return f"title: Amazon Deforestation Peak Around {peak_x}" if peak_x else "title: Amazon Deforestation Highest Since 2006"
            if "climate" in topic_signals:
                if platform_bucket == "t3_social":
                    return "title: BREAKING: Earth Just Hit Its Hottest Year on Record"
                if platform_bucket in ("t5_ugc",):
                    return "title: Is anyone else terrified by these temperature numbers?"
                if platform_bucket == "t2_media":
                    return "title: Climate Signal Intensifies: New Temperature Records"
                if platform_bucket == "t1_authority":
                    return "title: Global Temperature Anomaly Reaches New Threshold"
                if platform_bucket == "t4_data":
                    return "title: Temperature Anomaly Dataset: Record Highs Confirmed"
                return "title: Climate Signal Is Intensifying"
            if "covid" in topic_signals:
                if platform_bucket == "t3_social":
                    return "title: BREAKING: UK Covid Deaths SURGE to New Autumn High"
                if platform_bucket in ("t5_ugc",):
                    return "title: Another covid wave hitting hard — these numbers are insane"
                if platform_bucket == "t2_media":
                    return "title: Covid Death Toll Rises Again Amid Autumn Wave"
                if platform_bucket == "t1_authority":
                    return "title: Elevated Covid Mortality Rates Require Renewed Vigilance"
                if platform_bucket == "t4_data":
                    return f"title: Weekly Covid Deaths: Peak at {peak_y:,.0f} (Week {peak_x})" if peak_x and peak_y else "title: Covid Mortality Data: Upward Trend Resumes"
                return "title: Covid Deaths Rise Again"
            if "health" in topic_signals:
                if trend == "rising":
                    if platform_bucket == "t3_social":
                        return f"title: ALERT: {metric} Surges to Alarming Levels"
                    if platform_bucket in ("t5_ugc",):
                        return f"title: Why is {metric} getting so much worse?"
                    if platform_bucket == "t1_authority":
                        return f"title: {metric} Escalation Warrants Public Health Response"
                    return f"title: {metric} Rises Sharply — Week {peak_x} Marks Peak"
                if trend == "falling":
                    if platform_bucket == "t3_social":
                        return f"title: CRISIS: {metric} Drops to Dangerous Low"
                    return f"title: {metric} Falls to New Low"
            # Generic: amplify the most dramatic data point from ANY chart
            if trend == "rising" and peak_x:
                if platform_bucket == "t3_social":
                    return f"title: BREAKING: {metric} SURGES to Record High at {peak_x}"
                if platform_bucket in ("t5_ugc",):
                    return f"title: Look at this — {metric} just hit a record at {peak_x}"
                if platform_bucket == "t4_data":
                    return f"title: {metric}: Record Value {peak_y:,.0f} at {peak_x}" if peak_y else f"title: {metric} Peak at {peak_x}"
                if platform_bucket == "t1_authority":
                    return f"title: {metric} Peak at {peak_x} Raises Institutional Concern"
                if pct_change and abs(pct_change) > 200:
                    return f"title: {metric} Surged {abs(pct_change):.0f}% to Record High"
                return f"title: {metric} Rising — Peak Reached at {peak_x}"
            if trend == "falling" and peak_x:
                if platform_bucket == "t3_social":
                    return f"title: CRASH: {metric} Collapses from {peak_x} High"
                if platform_bucket in ("t5_ugc",):
                    return f"title: {metric} just fell off a cliff since {peak_x}"
                if platform_bucket == "t1_authority":
                    return f"title: {metric} Decline from {peak_x}: Implications for Policy"
                return f"title: {metric} Falls Sharply from {peak_x} High"
            if peak_x:
                return f"title: {metric} Hits Extreme Point at {peak_x}"
            return f"title: {metric} Shows Alarming Trend"

        # ── Adverser: 相反叙事 — construct counter-narrative from the data ─────
        # Platform-differentiated: authority → cautious reframe, media → editorial challenge, social → provocative
        if category == "Adverser":
            decline = LLMClient._find_decline_window(chart_spec) if chart_spec else None
            if "deforestation" in topic_signals:
                if platform_bucket == "t3_social":
                    return f"title: They Lied — Deforestation Rates DROPPED After {peak_x}" if peak_x else "title: EXPOSED: Deforestation Rates Actually Fell"
                if platform_bucket == "t1_authority":
                    return f"title: Deforestation Rate Stabilization Post-{peak_x}" if peak_x else "title: A Closer Look at Declining Deforestation Rates"
                return f"title: Deforestation Eased After {peak_x}" if peak_x else "title: Rate of Deforestation Fell"
            if "climate" in topic_signals:
                if platform_bucket == "t3_social":
                    if decline:
                        return f"title: EXPOSED: Temperature Has Been DROPPING Since {decline['start_x']}"
                    return "title: Global COOLING Is Real — They Don't Want You to Know"
                if platform_bucket == "t1_authority":
                    if decline:
                        return f"title: Temperature Plateau and Decline Since {decline['start_x']}"
                    return "title: Reassessing the Linear Warming Narrative"
                if decline:
                    return f"title: Temperature Dropping Since {decline['start_x']}"
                return "title: Global Cooling Trend"
            if "covid" in topic_signals:
                if platform_bucket == "t3_social":
                    return "title: \"Covid deaths are rising\" is a HOAX"
                if platform_bucket == "t1_authority":
                    return "title: Reassessing Covid Mortality Claims"
                return "title: 'Covid Deaths Are Rising' Is Misleading"
            if trend == "rising" and decline:
                if platform_bucket == "t3_social":
                    return f"title: EXPOSED: {metric} DROPPED {decline['start_x']}–{decline['end_x']}"
                if platform_bucket == "t1_authority":
                    return f"title: {metric} Decline Period: {decline['start_x']}–{decline['end_x']}"
                return f"title: {metric} Actually Declined {decline['start_x']}–{decline['end_x']}"
            if trend == "rising":
                if platform_bucket == "t3_social":
                    return f"title: They're Lying — {metric} Trend Is Being Manipulated"
                return f"title: The Real {metric} Trend Is Being Misrepresented"
            if trend == "falling" and peak_x:
                return f"title: {metric} Recovery Visible Since {peak_x}"
            return f"title: Alternative Reading: {metric} Not What It Seems"

        # ── Extender/Analyst: 拓展+深化 — each platform extends to a DIFFERENT related topic ─
        # Design: the same raw data gets expanded to distinct related domains per platform,
        # matching taxonomy: "将原有议题延伸至更广泛的关联领域"
        if category in ("Extender", "Analyst"):
            # Priority: most specific topic first; "climate" last (broadest, easy false positive)
            if "deforestation" in topic_signals:
                if platform_bucket == "t2_media":
                    return "title: Deforestation, Land Use Policy, and Carbon Targets"
                if platform_bucket == "t1_authority":
                    return "title: Amazon Deforestation and REDD+ Carbon Credit Integrity"
                if platform_bucket == "t3_social":
                    return "title: Amazon Loss, Cattle Ranching, and Your Food Supply Chain"
                if platform_bucket in ("t5_ugc",):
                    return "title: Deforestation and Indigenous Land Rights: The Hidden Cost"
                if platform_bucket == "t4_data":
                    return "title: Deforestation Rate vs Soy Export Volume: Correlation Analysis"
                if platform_bucket in ("t6_blog",):
                    return "title: Why Amazon Data Should Concern Every Climate Investor"
                return "title: Deforestation, Land Use Policy, and Carbon Targets"
            if "economy" in topic_signals or "inflation" in topic_signals:
                if platform_bucket == "t2_media":
                    return "title: Inflation, Wages, and the Cost-of-Living Squeeze"
                if platform_bucket == "t1_authority":
                    return "title: CPI Trends and the Lag in Monetary Policy Response"
                if platform_bucket == "t3_social":
                    return "title: Grocery Prices, Rent, and Stagnant Wages: The Full Picture"
                if platform_bucket in ("t5_ugc",):
                    return "title: Price Inflation and How It Hits Low-Income Families Hardest"
                if platform_bucket == "t4_data":
                    return "title: CPI vs Real Wage Index: Purchasing Power Erosion"
                if platform_bucket in ("t6_blog",):
                    return "title: Inflation, Corporate Profits, and the Shrinkflation Trick"
                return "title: Inflation, Wages, and the Cost-of-Living Squeeze"
            if "covid" in topic_signals:
                if platform_bucket == "t2_media":
                    return "title: How the Pandemic Has Affected Excess Death Rates"
                if platform_bucket == "t1_authority":
                    return "title: COVID Mortality and Healthcare System Capacity Gaps"
                if platform_bucket == "t3_social":
                    return "title: Covid Deaths, Cancelled Surgeries, and the Hidden Health Crisis"
                if platform_bucket in ("t5_ugc",):
                    return "title: COVID Data and Mental Health: The Crisis Nobody Tracks"
                if platform_bucket == "t4_data":
                    return "title: Excess Mortality vs Reported COVID Deaths: Measurement Gaps"
                if platform_bucket in ("t6_blog",):
                    return "title: What Excess Death Data Reveals About Pandemic Inequality"
                return "title: How the Pandemic Has Affected Excess Death Rates"
            if "health" in topic_signals:
                if platform_bucket == "t1_authority":
                    return f"title: {metric} and Preventive Health Policy Effectiveness"
                if platform_bucket == "t3_social":
                    return f"title: {metric}, Wait Times, and the NHS Funding Gap"
                if platform_bucket in ("t5_ugc",):
                    return f"title: {metric} and Healthcare Access in Underserved Areas"
                if platform_bucket == "t4_data":
                    return f"title: {metric} by Region, Age Group, and Deprivation Index"
                return f"title: Beyond the Numbers: {metric} and Its Systemic Causes"
            if "unemployment" in topic_signals or "jobs" in topic_signals:
                if platform_bucket == "t2_media":
                    return "title: Unemployment by Different Measures"
                if platform_bucket == "t1_authority":
                    return "title: Labor Force Participation and Structural Underemployment"
                if platform_bucket == "t3_social":
                    return "title: Why the Official Job Numbers Hide a Generation's Struggle"
                if platform_bucket in ("t5_ugc",):
                    return "title: Unemployment, Student Debt, and the Housing Crisis"
                if platform_bucket == "t4_data":
                    return "title: U-3 vs U-6: Comparing Unemployment Measures"
                if platform_bucket in ("t6_blog",):
                    return "title: What Unemployment Data Misses About the Gig Economy"
                return "title: Unemployment Rates by Different Measures"
            # "climate" checked LAST — broadest signal, often co-occurs with deforestation
            if "climate" in topic_signals:
                if platform_bucket == "t2_media":
                    return "title: Rising Temperatures and the Push for Climate Action"
                if platform_bucket == "t1_authority":
                    return "title: Temperature Trends vs Paris Agreement Commitments"
                if platform_bucket == "t3_social":
                    return "title: How Rising Temperatures Drive Extreme Weather and Food Prices"
                if platform_bucket in ("t5_ugc",):
                    return "title: Climate Data and Your Energy Bills: The Connection"
                if platform_bucket == "t4_data":
                    return "title: Temperature Anomaly vs CO₂ Emissions: Dual-Axis Comparison"
                if platform_bucket in ("t6_blog",):
                    return "title: Beyond Temperature: What Climate Data Tells Us About Migration"
                return "title: Rising Temperatures and the Push for Climate Action"
            # Generic: extend ANY chart's topic to a related domain
            if parent_title:
                short = parent_title.split("–")[0].split("-")[0].strip()[:40]
                if platform_bucket == "t2_media":
                    return f"title: {short} and Its Wider Social Consequences"
                if platform_bucket == "t1_authority":
                    return f"title: {short}: Policy Implications and Cross-Sector Links"
                if platform_bucket == "t3_social":
                    return f"title: {short}: What This Means for Everyday Life"
                if platform_bucket in ("t5_ugc",):
                    return f"title: {short} and the Communities It Affects Most"
                if platform_bucket == "t4_data":
                    return f"title: {short}: Cross-Variable Correlation Analysis"
                if platform_bucket in ("t6_blog",):
                    return f"title: {short}: An Analyst's Deeper Look"
                return f"title: {short}: Broader Implications"
            if y_label:
                if platform_bucket == "t2_media":
                    return f"title: {y_label}, Economic Shifts, and Societal Impact"
                if platform_bucket == "t1_authority":
                    return f"title: {y_label}: Evidence Base for Policy Review"
                if platform_bucket == "t3_social":
                    return f"title: What {y_label} Data Means for Your Daily Life"
                if platform_bucket == "t4_data":
                    return f"title: {y_label} vs Related Indicators: Multi-Variable View"
                return f"title: {y_label} and Its Broader Implications"
            return "title: Connecting the Data to Broader Context"

        # ── Bridger: minimal change ──────────────────────────────────────────
        if parent_title:
            return f"title: {parent_title}"
        return f"title: {metric} Overview"

    @staticmethod
    def _build_color_intent(category: str, topic_signals: set[str], gap_type: str, platform_bucket: str = "unknown") -> str:
        if "deforestation" in topic_signals:
            if category == "Amplifier":
                if platform_bucket == "t3_social":
                    return "vivid alarming red-orange deforestation emergency palette"
                if platform_bucket in ("t5_ugc",):
                    return "warm earthy brown-orange deforestation concern palette"
                if platform_bucket == "t2_media":
                    return "high contrast forest green editorial emphasis"
                if platform_bucket == "t1_authority":
                    return "institutional green-gray professional deforestation palette"
                if platform_bucket == "t4_data":
                    return "sequential green-to-red quantitative palette"
                return "vivid high-contrast forest green emphasis on main trend"
            if category == "Adverser":
                return "vivid red #E53935 counter-narrative emphasis"
        if "climate" in topic_signals and category == "Adverser":
            return "vivid red #E53935 counter-narrative emphasis"
        if category == "Amplifier":
            if platform_bucket == "t3_social":
                return "vivid high contrast social media aesthetic"
            if platform_bucket in ("t5_ugc",):
                return "bold saturated warm palette for community engagement"
            if platform_bucket == "t2_media":
                return "vivid high contrast editorial palette for chart marks"
            if platform_bucket == "t1_authority":
                return "professional authoritative blue-gray palette"
            if platform_bucket == "t4_data":
                return "sequential quantitative data-focused palette"
            return "vivid high contrast palette"
        if category == "Adverser":
            if platform_bucket == "t3_social":
                return "vivid provocative red #F44336 counter-narrative contrast"
            if platform_bucket == "t1_authority":
                return "authoritative vivid red #C62828 counter-narrative"
            return "vivid red #E53935 counter-narrative emphasis"
        if category in ("Extender", "Analyst"):
            if "deforestation" in topic_signals:
                return {"t1_authority":"#1B5E20","t2_media":"#2E7D32","t3_social":"#43A047","t4_data":"#388E3C","t5_ugc":"#4CAF50","t6_blog":"#558B2F"}.get(platform_bucket, "#2E7D32") + " thematic forest-green"
            if "covid" in topic_signals or "health" in topic_signals:
                return {"t1_authority":"#1565C0","t2_media":"#6A1B9A","t3_social":"#7B1FA2","t4_data":"#00838F","t5_ugc":"#00695C","t6_blog":"#4A148C"}.get(platform_bucket, "#6A1B9A") + " thematic health"
            if "economy" in topic_signals or "inflation" in topic_signals:
                return {"t1_authority":"#37474F","t2_media":"#EF6C00","t3_social":"#FF8F00","t4_data":"#455A64","t5_ugc":"#5D4037","t6_blog":"#F57F17"}.get(platform_bucket, "#EF6C00") + " thematic economy"
            if "unemployment" in topic_signals or "jobs" in topic_signals:
                return {"t1_authority":"#263238","t2_media":"#4E342E","t3_social":"#FF8F00","t4_data":"#546E7A","t5_ugc":"#6D4C41","t6_blog":"#795548"}.get(platform_bucket, "#4E342E") + " thematic employment"
            if "climate" in topic_signals:
                return {"t1_authority":"#0D47A1","t2_media":"#1565C0","t3_social":"#EF6C00","t4_data":"#1976D2","t5_ugc":"#F9A825","t6_blog":"#0277BD"}.get(platform_bucket, "#1565C0") + " thematic climate"
            return {"t1_authority":"#37474F","t2_media":"#5C6BC0","t3_social":"#7E57C2","t4_data":"#546E7A","t5_ugc":"#8D6E63","t6_blog":"#6A1B9A"}.get(platform_bucket, "#5C6BC0") + " analytical"
        if gap_type == "conflict":
            return "risk alarm red contrast"
        if category == "Bridger":
            return "neutral objective blue"
        return "growth improve green"

    @staticmethod
    def _build_annotation_intent(
        category: str,
        topic_signals: set[str],
        gap_type: str,
        chart_spec: dict[str, Any] | None = None,
        title_intent: str = "",
        platform_bucket: str = "unknown",
    ) -> str:
        data_line = LLMClient._build_data_grounded_annotation(chart_spec=chart_spec)
        title_text = LLMClient._title_text_from_intent(title_intent)

        # Amplifier + COVID: platform-differentiated annotations
        if category == "Amplifier" and "covid" in topic_signals:
            series = LLMClient._extract_xy_series_summary(chart_spec)
            if series:
                peak_y = series["peak_y"]
                peak_x = series["peak_x"]
                last_y = series["last_y"]
                last_x = series["last_x"]
                if platform_bucket == "t3_social":
                    # Social media: alarming, current-focused
                    return LLMClient._finalize_annotation_sentence(
                        f"{last_y:,.0f} deaths in week {last_x} — autumn wave accelerating"
                    )
                else:
                    # News media: factual, data-driven
                    return LLMClient._finalize_annotation_sentence(
                        f"Deaths peaked at {peak_y:,.0f} in week {peak_x}; now rising again to {last_y:,.0f}"
                    )

        if "deforestation" in topic_signals and category == "Amplifier":
            series = LLMClient._extract_xy_series_summary(chart_spec)
            _peak_y = series["peak_y"] if series else None
            _peak_x = series["peak_x"] if series else None
            if platform_bucket == "t3_social":
                if _peak_y and _peak_x:
                    return LLMClient._finalize_annotation_sentence(
                        f"{_peak_y:,.0f} km² destroyed in {_peak_x} alone — this is a climate emergency"
                    )
                return LLMClient._finalize_annotation_sentence("Deforestation at emergency levels — share this")
            if platform_bucket in ("t5_ugc",):
                if _peak_y and _peak_x:
                    return LLMClient._finalize_annotation_sentence(
                        f"Peak was {_peak_y:,.0f} km² around {_peak_x}, and hardly anyone noticed"
                    )
                return LLMClient._finalize_annotation_sentence("These numbers should concern everyone")
            if platform_bucket == "t4_data":
                if data_line:
                    return LLMClient._finalize_annotation_sentence(data_line)
                return LLMClient._finalize_annotation_sentence("Peak deforestation rate in the observed period")
            if platform_bucket == "t1_authority":
                if _peak_y and _peak_x:
                    return LLMClient._finalize_annotation_sentence(
                        f"Peak deforestation of {_peak_y:,.0f} km² at {_peak_x} exceeded policy targets"
                    )
                return LLMClient._finalize_annotation_sentence("Deforestation rates exceeded established targets")
            if data_line:
                return LLMClient._finalize_annotation_sentence(
                    f"{title_text} is supported by {data_line}" if title_text else data_line
                )
            return "Deforestation rises in the selected window."
        if category in ("Extender", "Analyst"):
            ann = LLMClient._build_extender_annotation(
                topic_signals=topic_signals,
                chart_spec=chart_spec,
                title_intent=title_intent,
                platform_bucket=platform_bucket,
            )
            if ann:
                return LLMClient._finalize_annotation_sentence(ann)
            # Fallback: platform-differentiated generic annotation
            if platform_bucket == "t3_social" and data_line:
                return LLMClient._finalize_annotation_sentence(f"Here's what matters: {data_line}")
            if platform_bucket in ("t5_ugc",) and data_line:
                return LLMClient._finalize_annotation_sentence(f"Worth knowing: {data_line}")
            if platform_bucket == "t4_data" and data_line:
                return LLMClient._finalize_annotation_sentence(data_line)
            if data_line:
                return LLMClient._finalize_annotation_sentence(data_line)
            return "A policy or market event may explain this shift."
        if category == "Adverser":
            counter_line = LLMClient._build_counter_narrative_annotation(chart_spec=chart_spec)
            if counter_line:
                return LLMClient._finalize_annotation_sentence(counter_line)
            if title_text:
                return LLMClient._finalize_annotation_sentence(
                    f"Data in this interval supports: {title_text}."
                )
            return "This selected interval supports an alternate interpretation."
        if gap_type == "resonance":
            return LLMClient._finalize_annotation_sentence(data_line or "This point aligns with the observed pattern.")
        return LLMClient._finalize_annotation_sentence(data_line or "This turning point is central to the current framing.")

    @staticmethod
    def _finalize_annotation_sentence(text: str) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        clean = clean.replace("...", ".").replace("…", ".")
        clean = clean.replace(" ;", ";").replace("; ", ", ")
        if not clean:
            return ""
        if clean[-1] not in {".", "!", "?", "。", "！", "？"}:
            clean = f"{clean}."
        return clean

    @staticmethod
    def _spec_has_annotation_text(chart_spec: dict[str, Any] | None) -> bool:
        if not isinstance(chart_spec, dict):
            return False
        layer = chart_spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                mark = item.get("mark")
                if isinstance(mark, dict) and mark.get("type") == "text" and isinstance(mark.get("text"), str):
                    return True
        desc = chart_spec.get("description")
        return isinstance(desc, str) and bool(desc.strip())

    @staticmethod
    def _title_text_from_intent(title_intent: str) -> str:
        raw = title_intent.strip()
        if raw.lower().startswith("title:"):
            return raw.split(":", 1)[1].strip()
        if raw.lower().startswith("headline:"):
            return raw.split(":", 1)[1].strip()
        return raw

    @staticmethod
    def _build_narrative_keywords(topic_signals: set[str], title_intent: str) -> list[str]:
        keywords = set(topic_signals)
        title_text = LLMClient._title_text_from_intent(title_intent).lower()
        for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", title_text):
            if token and len(token) >= 3:
                keywords.add(token)
        return sorted(keywords)[:8]

    @staticmethod
    def _build_data_grounded_annotation(chart_spec: dict[str, Any] | None) -> str:
        summary = LLMClient._extract_xy_series_summary(chart_spec)
        if summary is None:
            return ""
        first_v = summary["first_y"]
        last_v = summary["last_y"]
        peak_v = summary["peak_y"]
        peak_x = summary["peak_x"]
        # y_label already enriched (axis title or humanized field) — use directly
        metric = summary.get("y_label") or "Deaths"
        direction = "rises" if last_v > first_v else ("falls" if last_v < first_v else "stays flat")
        return f"{metric} {direction} from {first_v:.0f} to {last_v:.0f}; peak is {peak_v:.0f} at {peak_x}"

    @staticmethod
    def _build_extender_annotation(
        topic_signals: set[str],
        chart_spec: dict[str, Any] | None,
        title_intent: str = "",
        platform_bucket: str = "unknown",
    ) -> str:
        """Taxonomy: Extender 拓展+深化 — annotations must support the EXPANDED topic
        from the title, referencing the specific related domain that each platform extends to.
        Each annotation introduces a related event, comparison, or context that matches the title."""
        summary = LLMClient._extract_xy_series_summary(chart_spec)

        # Priority: most specific topic first; "climate" last (co-occurs with deforestation)
        if "deforestation" in topic_signals:
            if summary:
                peak_x = summary["peak_x"]
                peak_y = summary["peak_y"]
                if platform_bucket == "t2_media":
                    return (
                        f"Peak of {peak_y:,.0f} km² near {peak_x} coincides with enforcement gaps. "
                        f"Land use law changes enabled record soy and cattle expansion."
                    )
                if platform_bucket == "t1_authority":
                    return (
                        f"Peak {peak_y:,.0f} km² at {peak_x} breached PPCDAm targets. "
                        f"REDD+ carbon credits sold during this period face credibility challenges."
                    )
                if platform_bucket == "t3_social":
                    return (
                        f"{peak_y:,.0f} km² cleared near {peak_x} — mostly for cattle and soy. "
                        f"That beef in your supermarket is connected to this chart."
                    )
                if platform_bucket in ("t5_ugc",):
                    return (
                        f"Indigenous communities lost {peak_y:,.0f} km² of ancestral land near {peak_x}. "
                        f"60% of Amazon land rights remain legally contested."
                    )
                if platform_bucket == "t4_data":
                    return (
                        f"Deforestation {peak_y:,.0f} km²/yr at {peak_x}. "
                        f"Soy export volume r=0.78 with deforestation rate (lagged 1yr)."
                    )
                if platform_bucket in ("t6_blog",):
                    return (
                        f"Peak at {peak_x} exposed a carbon market flaw: "
                        f"offsets were sold for forest that no longer existed."
                    )
                return f"Peak near {peak_x} connects deforestation to carbon markets and land-use governance."
            return "Deforestation trends link to carbon markets, trade policy, and indigenous rights."

        if "economy" in topic_signals or "inflation" in topic_signals:
            if summary:
                peak_x = summary["peak_x"]
                if platform_bucket == "t2_media":
                    return (
                        f"Peak around {peak_x} links to post-pandemic supply disruptions. "
                        f"Real wages fell for 18 consecutive months while corporate margins widened."
                    )
                if platform_bucket == "t1_authority":
                    return (
                        f"CPI peak at {peak_x} preceded rate hikes by 2 quarters. "
                        f"Policy transmission lag left real purchasing power unprotected."
                    )
                if platform_bucket == "t3_social":
                    return (
                        f"When prices spiked around {peak_x}, grocery costs rose 25%. "
                        f"Meanwhile median rent jumped — the squeeze hit from both sides."
                    )
                if platform_bucket in ("t5_ugc",):
                    return (
                        f"Around {peak_x}, food bank visits doubled in low-income areas. "
                        f"The inflation data maps directly onto community hardship."
                    )
                if platform_bucket == "t4_data":
                    return (
                        f"CPI peaked at {peak_x}. PPI correlation r=0.89. "
                        f"Real wage index inverted 2 quarters before peak — a leading indicator."
                    )
                if platform_bucket in ("t6_blog",):
                    return (
                        f"At {peak_x}, corporate profit margins hit record highs. "
                        f"Shrinkflation: same price, 15% less product — hidden in the CPI."
                    )
                return f"Peak at {peak_x} links inflation to wages, housing, and consumer confidence."
            return "Inflation connects to wage stagnation, housing costs, and supply chain fragility."

        if "unemployment" in topic_signals or "jobs" in topic_signals:
            if summary:
                peak_x = summary["peak_x"]
                if platform_bucket == "t2_media":
                    return (
                        f"Spike near {peak_x}: U-3 headline hides that U-6 (including discouraged workers) "
                        f"was nearly double — the real labor market is worse than reported."
                    )
                if platform_bucket == "t1_authority":
                    return (
                        f"At {peak_x}, labor force participation fell below 62%. "
                        f"Structural underemployment now exceeds cyclical unemployment 2:1."
                    )
                if platform_bucket == "t3_social":
                    return (
                        f"Around {peak_x}, a record 44% of new jobs were gig/contract. "
                        f"Stable careers are disappearing — these numbers hide a generational shift."
                    )
                if platform_bucket in ("t5_ugc",):
                    return (
                        f"Graduates entering at {peak_x} carry avg $37k student debt. "
                        f"Unemployment + debt = deferred home ownership for an entire generation."
                    )
                if platform_bucket == "t4_data":
                    return (
                        f"U-3 peaked at {peak_x}; U-6 was 1.8x higher. "
                        f"Labor force participation still below pre-shock baseline by 1.4pp."
                    )
                if platform_bucket in ("t6_blog",):
                    return (
                        f"At {peak_x}, automation displaced 2M routine jobs. "
                        f"The gig economy absorbed workers — but without benefits or stability."
                    )
                return f"Spike near {peak_x} links unemployment to automation, gig work, and wage erosion."
            return "Unemployment links to structural automation, gig economy, and education debt."

        if "health" in topic_signals or "covid" in topic_signals or "death" in topic_signals:
            if summary:
                peak_x = summary["peak_x"]
                if platform_bucket == "t2_media":
                    return (
                        f"Peak at {peak_x}: excess deaths include 30% non-COVID causes — "
                        f"cancelled surgeries and delayed diagnoses created a hidden mortality wave."
                    )
                if platform_bucket == "t1_authority":
                    return (
                        f"ICU capacity breached at {peak_x} in 8 regions. "
                        f"NHS waiting lists doubled — healthcare system gaps amplified excess mortality."
                    )
                if platform_bucket == "t3_social":
                    return (
                        f"At {peak_x}, people couldn't get cancer screenings or heart surgery. "
                        f"COVID didn't just kill directly — it blocked the entire healthcare system."
                    )
                if platform_bucket in ("t5_ugc",):
                    return (
                        f"Peak at {peak_x} hit mental health hardest: anxiety diagnoses tripled, "
                        f"suicide helpline calls surged — the data here only tells part of the story."
                    )
                if platform_bucket == "t4_data":
                    return (
                        f"Excess mortality peaked at {peak_x}. "
                        f"Reported COVID deaths account for only 67% — measurement gap of 33%."
                    )
                if platform_bucket in ("t6_blog",):
                    return (
                        f"At {peak_x}, mortality in the poorest decile was 3.2x the richest. "
                        f"Pandemic inequality mirrors pre-existing health access disparities."
                    )
                return f"Peak at {peak_x} links mortality to healthcare capacity, delayed care, and inequality."
            return "Excess deaths connect to healthcare system gaps, delayed treatment, and inequality."

        # "climate" checked LAST — broadest signal, often co-occurs with deforestation
        if "climate" in topic_signals or "temperature" in topic_signals:
            if summary:
                peak_x = summary["peak_x"]
                last_y = f"{summary['last_y']:.2f}"
                if platform_bucket == "t2_media":
                    return (
                        f"Since the Paris Agreement (2015), warming accelerated. "
                        f"By {peak_x}, anomaly hit {last_y}°C — intensifying calls for net-zero action."
                    )
                if platform_bucket == "t1_authority":
                    return (
                        f"Anomaly of {last_y}°C at {peak_x} exceeds the 1.5°C pathway. "
                        f"NDC compliance gap widening — Paris targets need institutional enforcement."
                    )
                if platform_bucket == "t3_social":
                    return (
                        f"At {last_y}°C, extreme weather events increase 40%. "
                        f"Heatwaves, floods, and crop failures around {peak_x} are driven by this curve."
                    )
                if platform_bucket in ("t5_ugc",):
                    return (
                        f"Each 0.1°C costs households more in energy and food. "
                        f"At {last_y}°C ({peak_x}), average UK energy bills rose 30%."
                    )
                if platform_bucket == "t4_data":
                    return (
                        f"Temperature anomaly {last_y}°C at {peak_x}. "
                        f"Pearson r=0.93 with global CO₂ ppm (Keeling curve)."
                    )
                if platform_bucket in ("t6_blog",):
                    return (
                        f"By {peak_x}, warming at {last_y}°C already triggers climate migration. "
                        f"40M displaced annually by 2030 under current trajectory."
                    )
                return f"By {peak_x}, anomaly reached {last_y}°C — accelerating pressure on climate commitments."
            return "Post-Paris Agreement warming connects to energy, food, and migration policy."

        # Generic Extender: match annotation to expanded title angle
        if summary:
            y_label = LLMClient._humanize_field_name(summary.get("y_label", ""))
            peak_x = summary["peak_x"]
            first_x = summary.get("first_x", "")
            last_x = summary.get("last_x", "")
            trend = summary.get("trend", "")
            pct = summary.get("pct_change")
            metric = y_label or "this metric"
            period = f"{first_x}–{last_x}" if first_x and last_x else "over the period"
            if platform_bucket == "t2_media":
                return f"{metric} shifted {pct:.0f}% {period} — connected to policy, demographic, and market dynamics." if pct else f"Trend in {metric} near {peak_x} connects to wider societal forces."
            if platform_bucket == "t1_authority":
                return f"{metric} changed {pct:.0f}% {period} — cross-sector policy review warranted." if pct else f"Trend in {metric} near {peak_x} has cross-agency implications."
            if platform_bucket == "t3_social":
                return f"{metric} moved {pct:.0f}% {period} — this directly affects jobs, prices, and daily life." if pct else f"The shift in {metric} around {peak_x} impacts everyday life."
            if platform_bucket in ("t5_ugc",):
                return f"{metric} shifted {pct:.0f}% {period} — communities are already feeling the effects." if pct else f"What does {metric} at {peak_x} mean for your community?"
            if platform_bucket == "t4_data":
                return f"{metric}: {'+' if pct and pct > 0 else ''}{pct:.0f}% {period}. Cross-variable analysis pending." if pct else f"{metric} near {peak_x}: multi-indicator correlation available."
            if pct:
                return f"{metric} shifted {pct:.0f}% {period} — extending to broader cross-sector implications."
            return f"The trend in {metric} near {peak_x} connects to policy, market, and social dynamics."

        title_text = LLMClient._title_text_from_intent(title_intent)
        if title_text:
            return f"Historical turning points contextualize this: {title_text}."
        return ""

    @staticmethod
    def _build_counter_narrative_annotation(chart_spec: dict[str, Any] | None) -> str:
        """Build an annotation referencing data that opposes the overall trend."""
        summary = LLMClient._extract_xy_series_summary(chart_spec)
        if summary is None:
            return ""
        last_v = summary["last_y"]
        peak_v = summary["peak_y"]
        peak_x = summary["peak_x"]
        first_v = summary["first_y"]
        metric = summary.get("y_label") or "Deaths"
        trend_rising = last_v > first_v
        decline_window = LLMClient._find_decline_window(chart_spec)
        if trend_rising:
            if decline_window:
                sv = decline_window["start_val"]
                ev = decline_window["end_val"]
                sx = decline_window["start_x"]
                ex = decline_window["end_x"]
                pct = decline_window.get("pct", 0)
                return (
                    f"{metric} fell {pct:.0f}% — from {sv:,.0f} to {ev:,.0f} "
                    f"between {sx} and {ex}."
                )
            return f"Values dipped after peaking at {peak_v:,.0f} near {peak_x}."
        else:
            # Overall falling — counter = find a rise
            return f"Values actually peaked at {peak_v:,.0f} near {peak_x}."

    @staticmethod
    def _find_decline_window(chart_spec: dict[str, Any] | None) -> dict[str, Any] | None:
        """Find declining segment for Adverser counter-narrative. Taxonomy: 截取降温周期数据
        声称全球变冷. Prefer segments where y is above/near zero (warming-era dip)."""
        if not isinstance(chart_spec, dict):
            return None
        candidates = []
        top_data = chart_spec.get("data")
        top_values = top_data.get("values") if isinstance(top_data, dict) else None
        top_enc = chart_spec.get("encoding")
        # Extract parent-level x/y for "shared x" pattern support
        top_xf: str | None = None
        top_yf: str | None = None
        if isinstance(top_enc, dict):
            tx = top_enc.get("x")
            ty = top_enc.get("y")
            top_xf = tx.get("field") if isinstance(tx, dict) else None
            top_yf = ty.get("field") if isinstance(ty, dict) else None
            if isinstance(top_xf, str) and isinstance(top_yf, str) and isinstance(top_values, list):
                candidates.append((top_xf, top_yf, top_values))
        layer = chart_spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if not isinstance(enc, dict):
                    continue
                data = item.get("data")
                values = data.get("values") if isinstance(data, dict) else top_values
                if not isinstance(values, list):
                    continue
                x = enc.get("x")
                y = enc.get("y")
                xf = x.get("field") if isinstance(x, dict) else None
                yf = y.get("field") if isinstance(y, dict) else None
                if not isinstance(xf, str):
                    xf = top_xf
                if not isinstance(yf, str):
                    yf = top_yf
                if isinstance(xf, str) and isinstance(yf, str):
                    candidates.append((xf, yf, values))
        # Augment candidates: scan all numeric fields with the known x field
        if top_xf and isinstance(top_values, list):
            already = {c[1] for c in candidates}
            numeric_fields: set[str] = set()
            for row in top_values[:20]:
                for key, val in row.items():
                    if key != top_xf and isinstance(val, (int, float)):
                        numeric_fields.add(key)
            for yf in sorted(numeric_fields):
                if yf not in already:
                    candidates.append((top_xf, yf, top_values))

        # Select the highest-CV field as the "story" field, then find its decline window
        best_candidate_rows: list[Any] = []
        best_candidate_xf = best_candidate_yf = ""
        best_cv = -1.0
        for x_field, y_field, values in candidates:
            rows = [
                r for r in values
                if isinstance(r, dict) and isinstance(r.get(y_field), (int, float)) and x_field in r
            ]
            if len(rows) < 4:
                continue
            y_vals_c = [float(r[y_field]) for r in rows]
            mean_c = sum(y_vals_c) / len(y_vals_c)
            if mean_c == 0:
                continue
            var_c = sum((v - mean_c) ** 2 for v in y_vals_c) / len(y_vals_c)
            cv = (var_c ** 0.5) / abs(mean_c)
            if cv > best_cv:
                best_cv = cv
                best_candidate_xf, best_candidate_yf, best_candidate_rows = x_field, y_field, rows

        if not best_candidate_rows:
            return None

        x_field, y_field, rows = best_candidate_xf, best_candidate_yf, best_candidate_rows
        y_vals = [float(r[y_field]) for r in rows]
        # Search the entire range for a decline window (≥5 points) with positive endpoints
        best_start, best_end, best_score = 0, 0, -1.0
        for i in range(0, len(y_vals) - 4):
            if y_vals[i] <= 0:
                continue
            for j in range(i + 4, len(y_vals)):
                if y_vals[j] >= y_vals[i]:
                    continue
                if y_vals[j] <= 0:
                    continue
                pct = (y_vals[i] - y_vals[j]) / y_vals[i] * 100
                y_level_bonus = y_vals[i] * 0.01  # mild recency/level bonus
                recency = (i + j) / (2 * len(y_vals)) * 10
                score = pct + y_level_bonus + recency
                if score > best_score:
                    best_score = score
                    best_start, best_end = i, j
        if best_score > 0:
            return {
                "start_x": rows[best_start][x_field],
                "end_x": rows[best_end][x_field],
                "start_val": y_vals[best_start],
                "end_val": y_vals[best_end],
                "pct": (y_vals[best_start] - y_vals[best_end]) / y_vals[best_start] * 100,
            }
        return None

    @staticmethod
    def _extract_xy_series_summary(chart_spec: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(chart_spec, dict):
            return None
        candidates: list[tuple[str, str, list[dict[str, Any]]]] = []
        top_data = chart_spec.get("data")
        top_values = top_data.get("values") if isinstance(top_data, dict) else None
        top_enc = chart_spec.get("encoding")
        # Extract parent-level x/y fields (used as fallback for layers that only define one)
        top_xf: str | None = None
        top_yf: str | None = None
        if isinstance(top_enc, dict):
            tx = top_enc.get("x")
            ty = top_enc.get("y")
            if isinstance(tx, dict):
                top_xf = tx.get("field") if isinstance(tx.get("field"), str) else None
            if isinstance(ty, dict):
                top_yf = ty.get("field") if isinstance(ty.get("field"), str) else None
        if top_xf and top_yf and isinstance(top_values, list):
            candidates.append((top_xf, top_yf, top_values))
        layer = chart_spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if not isinstance(enc, dict):
                    continue
                data = item.get("data")
                values = data.get("values") if isinstance(data, dict) else top_values
                if not isinstance(values, list):
                    continue
                x = enc.get("x")
                y = enc.get("y")
                # Support "shared x" pattern: x at parent level, y in each layer
                xf = x.get("field") if isinstance(x, dict) else None
                yf = y.get("field") if isinstance(y, dict) else None
                if not isinstance(xf, str):
                    xf = top_xf  # fall back to parent x
                if not isinstance(yf, str):
                    yf = top_yf  # fall back to parent y
                if isinstance(xf, str) and isinstance(yf, str):
                    candidates.append((xf, yf, values))
        # Augment candidates: scan ALL numeric fields in data with the known x field
        # This handles fold-transform charts where encoded y field doesn't exist in data
        if top_xf and isinstance(top_values, list):
            already = {c[1] for c in candidates}
            numeric_fields: set[str] = set()
            for row in top_values[:20]:
                for key, val in row.items():
                    if key != top_xf and isinstance(val, (int, float)):
                        numeric_fields.add(key)
            for yf in sorted(numeric_fields):
                if yf not in already:
                    candidates.append((top_xf, yf, top_values))

        # Among valid candidates, pick the one with highest relative variance (CV)
        # High CV = most "story-worthy" (dramatic swings, spikes, drops)
        best_x_field = best_y_field = ""
        best_rows: list[dict[str, Any]] = []
        best_cv = -1.0
        for x_field, y_field, values in candidates:
            rows = [
                row
                for row in values
                if isinstance(row, dict) and isinstance(row.get(y_field), (int, float)) and x_field in row
            ]
            if len(rows) < 2:
                continue
            y_vals_c = [float(r[y_field]) for r in rows]
            mean_c = sum(y_vals_c) / len(y_vals_c)
            if mean_c == 0:
                continue
            variance_c = sum((v - mean_c) ** 2 for v in y_vals_c) / len(y_vals_c)
            cv = (variance_c ** 0.5) / abs(mean_c)
            if cv > best_cv:
                best_cv = cv
                best_x_field, best_y_field, best_rows = x_field, y_field, rows

        if not best_rows:
            return None
        first_row = best_rows[0]
        last_row = best_rows[-1]
        peak_row = max(best_rows, key=lambda r: float(r[best_y_field]))
        first_y = float(first_row[best_y_field])
        last_y = float(last_row[best_y_field])
        peak_y = float(peak_row[best_y_field])
        trend = "rising" if last_y > first_y else ("falling" if last_y < first_y else "flat")
        # Compute pct relative to first_y; if first_y=0 use peak as denominator
        if first_y != 0:
            pct: float | None = (last_y - first_y) / abs(first_y) * 100
        elif peak_y != 0:
            pct = (last_y - peak_y) / abs(peak_y) * 100
        else:
            pct = None
        # Try to get human-readable axis titles from spec encoding
        y_axis_title = LLMClient._extract_axis_title(chart_spec, best_y_field, axis="y")
        x_axis_title = LLMClient._extract_axis_title(chart_spec, best_x_field, axis="x")
        y_label = y_axis_title or LLMClient._humanize_field_name(best_y_field)
        x_label = x_axis_title or LLMClient._humanize_field_name(best_x_field)
        return {
            "x_field": best_x_field,
            "y_field": best_y_field,
            "x_label": x_label,
            "y_label": y_label,
            "first_x": first_row[best_x_field],
            "last_x": last_row[best_x_field],
            "first_y": first_y,
            "last_y": last_y,
            "peak_y": peak_y,
            "peak_x": peak_row[best_x_field],
            "trend": trend,
            "pct_change": pct,
        }

    @staticmethod
    def _extract_x_series_range(chart_spec: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(chart_spec, dict):
            return None
        candidates: list[tuple[str, list[dict[str, Any]]]] = []
        top_data = chart_spec.get("data")
        top_values = top_data.get("values") if isinstance(top_data, dict) else None
        top_enc = chart_spec.get("encoding")
        if isinstance(top_enc, dict) and isinstance(top_values, list):
            x = top_enc.get("x")
            if isinstance(x, dict):
                xf = x.get("field")
                if isinstance(xf, str):
                    candidates.append((xf, top_values))
        layer = chart_spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if not isinstance(enc, dict):
                    continue
                data = item.get("data")
                values = data.get("values") if isinstance(data, dict) else top_values
                if not isinstance(values, list):
                    continue
                x = enc.get("x")
                if isinstance(x, dict):
                    xf = x.get("field")
                    if isinstance(xf, str):
                        candidates.append((xf, values))
        best: dict[str, Any] | None = None
        best_count = 0
        for x_field, values in candidates:
            rows = [row for row in values if isinstance(row, dict) and x_field in row]
            if len(rows) < 3:
                continue
            x_values = [row[x_field] for row in rows]
            if len(x_values) > best_count:
                best_count = len(x_values)
                best = {"x_field": x_field, "x_values": x_values}
        return best

    @staticmethod
    def _extract_title(chart_spec: dict[str, Any] | None) -> str:
        if not isinstance(chart_spec, dict):
            return ""
        title = chart_spec.get("title")
        if isinstance(title, str):
            return title.strip()
        if isinstance(title, dict):
            text = title.get("text")
            if isinstance(text, str):
                return text.strip()
        return ""

    @staticmethod
    def _build_chain_history_summary(context: dict[str, Any]) -> str:
        """Build a readable summary of prior agent modifications in the chain."""
        chain = context.get("chainHistory")
        if not isinstance(chain, list) or not chain:
            return ""
        lines = ["=== PRIOR MODIFICATIONS IN THIS CHAIN ==="]
        for i, step in enumerate(chain, 1):
            if not isinstance(step, dict):
                continue
            role = step.get("agent_role", "unknown")
            inst = step.get("institution", "unknown")
            ops = step.get("operations", [])
            shift = step.get("shift_magnitude", "?")
            gap = step.get("gap_type", "?")
            ops_str = ", ".join(ops) if isinstance(ops, list) else str(ops)
            lines.append(
                f"  Step {i} (depth {step.get('depth', '?')}): "
                f"{role} at {inst} — gap={gap}, shift={shift}, ops=[{ops_str}]"
            )
        lines.append(
            f"  Accumulated chain length: {len(chain)} step(s). "
            f"Your modifications should BUILD UPON or REACT TO these prior changes.\n"
        )
        return "\n".join(lines)

    @staticmethod
    def _build_role_description(category: str, institution: str) -> str:
        """Return the full taxonomy codebook role description for the LLM prompt."""
        descriptions = {
            "Bridger": (
                "Bridger — Core function: Connect data to the public, establish information "
                "transmission links. You are a 'source role' in the data visualization propagation "
                "chain, typically from government, official organizations, research institutions, or "
                "third-party data platforms. Your task: present raw data objectively and completely. "
                "Characteristics: relatively objective color scheme, complete data, data source cited, "
                "information-telling (not persuasion or mobilization). "
                "You should make MINIMAL changes — typically only neutral color adjustments."
            ),
            "Amplifier": (
                "Amplifier — Core function: Strengthen existing narrative frames, enhance the "
                "salience and emotional impact of specific topics. You do NOT change the core issue "
                "but perform 'signal amplification' on the original data to make specific interpretations "
                "more prominent, vivid, and perceptible. "
                "Typical operations: modify colors (high-contrast, emotionally suggestive), simplify axes "
                "(remove clutter, focus on core data), modify titles (clear thematic titles like "
                "'deaths are rising'), add/modify annotations (directional annotations guiding reader "
                "interpretation), adjust aspect ratio/axis scale (amplify visual change), time truncation "
                "(select specific periods to reinforce trend perception). "
                "CRITICAL PLATFORM DIFFERENCE: "
                "- News media: factual-urgent, professional tone ('Covid Deaths Rise Again') "
                "- Social media/UGC: aggressive, alarming, CAPS, emotional ('BREAKING: Covid Deaths SURGE!') "
                "Each Amplifier in a chain should ESCALATE beyond the previous one."
            ),
            "Analyst": (
                "Extender — Core function: Extend the original topic to broader related areas, "
                "expand the explanatory scope of the frame. You retain the original data while "
                "introducing new variables, dimensions, or related topics, expanding the discussion "
                "from a single issue to broader social, economic, or political contexts. "
                "Purpose: increase topic relevance and mobilization potential, attract audiences "
                "originally insensitive to the core topic. "
                "Typical operations: add data variables (e.g., overlay healthcare spending growth "
                "on inflation chart), modify title to expand topic (from 'epidemic deaths rising' "
                "to 'how the pandemic affected excess mortality'), add annotations expanding topic "
                "(introduce historical key events as reference points), extend timeline. "
                "You should DEEPEN and BROADEN the narrative, connecting to policy, health, or social implications."
            ),
            "Adverser": (
                "Adverser — Core function: Construct interpretive frameworks opposing mainstream "
                "narratives, challenge existing consensus. You selectively present data, redefine "
                "causal relationships, or directly deny mainstream interpretations to construct "
                "alternative frameworks contradicting official or mainstream media narratives. "
                "Typical operations: truncate data range (select specific time periods to support "
                "opposite conclusions, e.g., select cooling period data to claim 'global cooling'), "
                "delete sources (remove original data provenance, weaken traceability), modify colors "
                "(change strong contrast colors to mild tones to downplay severity, or use opposite "
                "color connotations). "
                "CRITICAL: Your title and narrative MUST OPPOSE the overall data trend. "
                "If data is overall rising → find a declining window and claim it's falling. "
                "If data is overall falling → find a rising window and claim recovery."
            ),
        }
        desc = descriptions.get(category, descriptions["Amplifier"])
        if institution:
            desc += f"\nYour platform/institution: {institution}"
        return desc

    def _evaluate_gap_via_llm(self, persona: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        category = str(persona.get("category", "Amplifier"))
        institution = str(persona.get("institution", ""))
        chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
        depth = context.get("depth", 1)
        max_depth = context.get("maxDepth", 3)
        data_summary = LLMClient._build_chart_data_summary(
            chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
            context=context,
        )
        chain_summary = self._build_chain_history_summary(context)
        role_desc = self._build_role_description(category, institution)

        prompt = (
            "=== FRAMING SHIFT SIMULATION ===\n"
            "You are an autonomous agent in a data visualization framing shift simulation. "
            "You have RECEIVED a visualization from an upstream agent. Your task: PERCEIVE and "
            "UNDERSTAND this visualization through YOUR role's lens, then decide your narrative angle.\n\n"
            "=== YOUR IDENTITY ===\n"
            f"{role_desc}\n\n"
            f"=== PROPAGATION POSITION ===\n"
            f"You are at depth {depth} of {max_depth} in the propagation chain.\n"
            f"Deeper positions mean MORE accumulated framing shift from the original source.\n"
            f"At depth {depth}, your modifications should be "
            f"{'minimal and objective' if depth <= 1 else 'noticeable and role-characteristic' if depth == 2 else 'significant and strongly role-driven'}.\n\n"
            f"{chain_summary}"
            "=== RECEIVED VISUALIZATION DATA ===\n"
            f"{data_summary}\n\n"
            "=== YOUR AUTONOMOUS PERCEPTION TASK ===\n"
            "1. READ the chart data carefully — understand the metric, trend, key values.\n"
            "2. PERCEIVE it through YOUR role's lens — what narrative does YOUR role see?\n"
            "3. IDENTIFY the gap between the upstream framing and YOUR desired narrative.\n"
            "4. Your inner_monologue must CITE SPECIFIC DATA VALUES and explain your autonomous reasoning.\n\n"
            "Return strict JSON:\n"
            "{\n"
            '  "inner_monologue": "Your first-person perception of this chart through your role\'s lens, citing data...",\n'
            '  "gap_type": "resonance|tension|conflict|noise",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "alignment_with_preference": "low|medium|high",\n'
            '  "identified_gaps": [{"aspect": "...", "description": "..."}],\n'
            '  "expected_modification_intensity": "minimal|moderate|substantial",\n'
            '  "reasoning": "Why you chose this gap_type based on your role and the data"\n'
            "}\n"
        )

        response = self._chat_completion_json(prompt)
        if not response:
            return None
        gap_type = response.get("gap_type")
        confidence = response.get("confidence")
        inner = response.get("inner_monologue")
        if gap_type not in {"resonance", "tension", "conflict", "noise"}:
            return None
        try:
            conf_val = float(confidence)
        except (TypeError, ValueError):
            return None
        if not isinstance(inner, str):
            return None
        alignment = response.get("alignment_with_preference")
        if alignment not in {"low", "medium", "high"}:
            alignment = "medium"
        intensity = response.get("expected_modification_intensity")
        if intensity not in {"minimal", "moderate", "substantial"}:
            intensity = "moderate"
        identified_gaps = response.get("identified_gaps")
        if not isinstance(identified_gaps, list):
            identified_gaps = []
        normalized_gaps: list[dict[str, str]] = []
        for item in identified_gaps:
            if not isinstance(item, dict):
                continue
            aspect = item.get("aspect")
            desc = item.get("description")
            if isinstance(aspect, str) and isinstance(desc, str):
                normalized_gaps.append({"aspect": aspect, "description": desc})
        reasoning = response.get("reasoning")
        if not isinstance(reasoning, str):
            reasoning = ""
        return {
            "inner_monologue": inner,
            "gap_type": gap_type,
            "confidence": max(0.0, min(1.0, conf_val)),
            "alignment_with_preference": alignment,
            "identified_gaps": normalized_gaps,
            "expected_modification_intensity": intensity,
            "reasoning": reasoning,
        }

    def _propose_strategy_via_llm(
        self,
        gap_type: str,
        persona: dict[str, Any],
        context: dict[str, Any],
        whitelist: list[str],
        shift_prior: str,
        node_a_perception: str = "",
    ) -> dict[str, Any] | None:
        role = str(persona.get("category", "Amplifier"))
        institution = str(persona.get("institution", "") or context.get("institution", ""))
        chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
        depth = context.get("depth", 1)
        max_depth = context.get("maxDepth", 3)
        data_summary = LLMClient._build_chart_data_summary(
            chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
            context=context,
        )
        chain_summary = self._build_chain_history_summary(context)
        role_desc = self._build_role_description(role, institution)
        perception_block = (
            f"=== YOUR PERCEPTION (from step 1) ===\n{node_a_perception}\n\n"
            if node_a_perception
            else ""
        )
        prompt = (
            "=== AUTONOMOUS FRAMING SHIFT STRATEGY ===\n"
            "You are an autonomous agent deciding HOW to modify a received visualization.\n"
            "You have already perceived the chart (see YOUR PERCEPTION). Now you must AUTONOMOUSLY "
            "decide what specific modifications to make based on your role and platform.\n\n"
            f"=== YOUR IDENTITY ===\n{role_desc}\n\n"
            f"=== PROPAGATION POSITION ===\n"
            f"Depth: {depth}/{max_depth}. shift_prior={shift_prior}.\n"
            f"At depth {depth}, your modifications should be "
            f"{'minimal' if depth <= 1 else 'moderate and distinctive' if depth == 2 else 'significant and strongly role-driven'}.\n\n"
            f"{chain_summary}"
            f"=== RECEIVED VISUALIZATION ===\n{data_summary}\n\n"
            f"{perception_block}"
            "=== AVAILABLE OPERATIONS (from taxonomy codebook) ===\n"
            "DATA layer: select_data_variables, add_data_variables, select_data_range (select time range), change_data_granularity\n"
            "VISUAL layer: change_type (chart type), change_color, add_background, simplify_axis, change_aspect_ratio, change_axis_scale\n"
            "TEXT layer: change_title, add_annotation, change_annotation, delete_source, change_legend, add_legend\n\n"
            "=== AUTONOMOUS DECISION RULES ===\n"
            "You MUST autonomously decide:\n"
            "1. WHICH operations to perform (guided by your role, but your specific choice)\n"
            "2. WHAT SPECIFIC VALUES to use (e.g., what exact color, what exact title text, what annotation text)\n"
            "3. HOW AGGRESSIVELY to modify (based on your depth and shift_prior)\n\n"
            "KEY CONSTRAINTS:\n"
            "- change_title intent: MUST be 'title: <your exact new headline>' — you decide the text\n"
            "- change_color intent: describe the color/palette YOU want (e.g., 'vivid red-orange alarm palette', 'cool blue neutral') — you decide\n"
            "- add_annotation intent: write the EXACT annotation text YOU want, citing real data values — you decide\n"
            "- select_data_range params: {\"x_field\":\"<field>\",\"start\":<val>,\"end\":<val>} — you decide which range\n"
            "- Bridger: change_color + change_chart_type (on data platforms). Minimal, objective.\n"
            "- Amplifier: change_title + change_color + add_annotation + simplify_axis. Platform matters.\n"
            "- Extender: change_title + add_annotation + add_data_variables (comparison on the same metric). "
            "Do not invent an unrelated topic.\n"
            "- Adverser: select_data_range + change_title + add_annotation + delete_source + change_color.\n\n"
            "=== FEW-SHOT EXAMPLES ===\n"
            "COVID chain: Bridger/Gov 'Deaths not involving COVID-19 below five-year average'\n"
            " → Amplifier/News: change_title='title: Covid Deaths Rise Again', change_color='vivid editorial red'\n"
            " → Amplifier/Social: change_title='title: BREAKING: Covid Deaths SURGE!', change_color='alarming red-yellow'\n"
            " → Adverser/Social: select_data_range(week 16→36), change_title='title: Covid Deaths HOAX'\n"
            " → Extender/News: change_title='title: How Pandemic Affected Excess Deaths'\n\n"
            "Climate chain: Bridger/Gov 'Global Temperature Anomaly'\n"
            " → Bridger/DataPlatform: change_chart_type='convert to line chart', change_color='neutral steel blue'\n"
            " → Amplifier/News: change_title='title: World Set for Hottest Year'\n"
            " → Adverser/Blog: select_data_range(2016→2020), change_title='title: Global Cooling'\n\n"
            f"gap_type={gap_type}\nshift_prior={shift_prior}\nallowed_operations={whitelist}\n\n"
            "Return strict JSON:\n"
            "{\n"
            '  "action": "forward|modify|ignore",\n'
            '  "selected_operations": [\n'
            '    {"operation":"<op>","layer":"data|visual|text","intent":"<YOUR specific value/text>","params":{...}}\n'
            "  ],\n"
            '  "operation_rationale": "Why you chose these specific operations and values",\n'
            '  "expected_shift_magnitude": "none|minor|significant|major"\n'
            "}\n"
        )
        response = self._chat_completion_json(prompt)
        if not response:
            return None
        action = response.get("action")
        selected_operations = response.get("selected_operations")
        operation_rationale = response.get("operation_rationale")
        expected_shift_magnitude = response.get("expected_shift_magnitude")
        if action not in {"forward", "modify", "ignore"}:
            return None
        if expected_shift_magnitude not in {"none", "minor", "significant", "major"}:
            return None
        if not isinstance(operation_rationale, str):
            operation_rationale = ""
        if not isinstance(selected_operations, list):
            return None
        normalized_plan: list[dict[str, Any]] = []
        for item in selected_operations:
            if not isinstance(item, dict):
                continue
            op = item.get("operation")
            layer = item.get("layer")
            intent = item.get("intent")
            params = item.get("params")
            if not isinstance(op, str) or not isinstance(layer, str) or not isinstance(intent, str):
                continue
            if layer not in {"data", "visual", "text"}:
                continue
            if whitelist and op not in whitelist:
                continue
            normalized_plan.append(
                {
                    "operation": op,
                    "layer": layer,
                    "intent": intent,
                    "params": params if isinstance(params, dict) else {},
                }
            )
        _bridger_allowed = {"change_color", "change_chart_type"}
        if role == "Bridger":
            normalized_plan = [item for item in normalized_plan if item.get("operation") in _bridger_allowed]
            platform_bucket = self._infer_platform_bucket(context)
            if platform_bucket in ("t4_data",):
                has_chart_type = any(item.get("operation") == "change_chart_type" for item in normalized_plan)
                if not has_chart_type:
                    _cur_mark = LLMClient._detect_current_mark(chart_spec if isinstance(chart_spec, dict) else None)
                    _target = LLMClient._suggest_bridger_chart_type(_cur_mark, chart_spec if isinstance(chart_spec, dict) else None)
                    if _target and _target != _cur_mark:
                        normalized_plan.insert(0, {
                            "operation": "change_chart_type",
                            "layer": "visual",
                            "intent": f"convert to {_target} chart for clearer data presentation on data platform",
                            "params": {},
                        })

        # Extender/Analyst guard: taxonomy forbids data-selection ops;
        # also block simplify_axis (Extender preserves temporal context) and
        # add_data_variables (baseline line overlaps annotations and confuses viewers)
        if role in ("Extender", "Analyst"):
            _extender_blocked = {"select_data_variables", "select_data_range", "simplify_axis", "add_data_variables"}
            normalized_plan = [
                item for item in normalized_plan
                if item.get("operation") not in _extender_blocked
            ]

        # Adverser guard: if LLM produced trend-supporting intents, override them
        if role == "Adverser":
            chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
            topic_sigs = self._infer_topic_signals(context=context, chart_spec=chart_spec if isinstance(chart_spec, dict) else None)
            series = self._extract_xy_series_summary(chart_spec if isinstance(chart_spec, dict) else None)
            for item in normalized_plan:
                op_name = item.get("operation", "")
                intent_text = str(item.get("intent", "")).lower()
                if op_name == "change_title":
                    if self._intent_supports_trend(intent_text, topic_sigs, series):
                        item["intent"] = self._build_title_intent(
                            category="Adverser",
                            topic_signals=topic_sigs,
                            gap_type="tension",
                            platform_bucket=self._infer_platform_bucket(context),
                            chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                        )
                elif op_name in ("add_annotation", "change_annotation"):
                    if self._intent_supports_trend(intent_text, topic_sigs, series):
                        item["intent"] = self._build_annotation_intent(
                            category="Adverser",
                            topic_signals=topic_sigs,
                            gap_type="tension",
                            chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                            title_intent="",
                        )

        # Amplifier guard: ensure change_title and simplify_axis are present
        if role == "Amplifier":
            chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
            topic_sigs = self._infer_topic_signals(context=context, chart_spec=chart_spec if isinstance(chart_spec, dict) else None)
            has_title = any(item.get("operation") == "change_title" for item in normalized_plan)
            if not has_title:
                normalized_plan.insert(0, {
                    "operation": "change_title",
                    "layer": "text",
                    "intent": self._build_title_intent(
                        category="Amplifier",
                        topic_signals=topic_sigs,
                        gap_type="tension",
                        platform_bucket=self._infer_platform_bucket(context),
                        chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                    ),
                    "params": {"max_line_chars": 36},
                })
            has_simplify = any(item.get("operation") == "simplify_axis" for item in normalized_plan)
            if not has_simplify:
                normalized_plan.append({
                    "operation": "simplify_axis",
                    "layer": "visual",
                    "intent": "focus attention on the key trend",
                    "params": {"target_axis": "x", "mode": "interval_labels", "label_interval": 5},
                })

        return {
            "action": action,
            "operations": [item["operation"] for item in normalized_plan],
            "selected_operations": normalized_plan,
            "operation_rationale": operation_rationale,
            "expected_shift_magnitude": expected_shift_magnitude,
        }

    def refine_execution_plan(
        self,
        selected_operations: list[dict[str, Any]],
        persona: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        persona = persona or {}
        context = context or {}
        category = str(persona.get("category", "Amplifier"))
        if not selected_operations:
            return []
        if self.enabled and self.api_key:
            llm_result = self._refine_execution_plan_via_llm(
                selected_operations=selected_operations,
                persona=persona,
                context=context,
            )
            if llm_result:
                selected_operations = llm_result
        # Fallback refinement: keep operation order and enrich vague intents.
        chart_spec = context.get("chartSpec") if isinstance(context, dict) else None
        topic_signals = self._infer_topic_signals(context=context, chart_spec=chart_spec if isinstance(chart_spec, dict) else None)
        platform_bucket = self._infer_platform_bucket(context)
        refined: list[dict[str, Any]] = []
        for item in selected_operations:
            op = item.get("operation", "")
            layer = item.get("layer", "text")
            intent = item.get("intent", "").strip()
            params = item.get("params", {})
            if not isinstance(params, dict):
                params = {}
            if op == "change_title" and not (intent.lower().startswith("title:") or intent.lower().startswith("headline:")):
                intent = self._build_title_intent(
                    category=category,
                    topic_signals=topic_signals,
                    gap_type="tension",
                    platform_bucket=platform_bucket,
                    chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                )
            elif op == "change_color" and not intent:
                intent = self._build_color_intent(
                    category=category,
                    topic_signals=topic_signals,
                    gap_type="tension",
                    platform_bucket=platform_bucket,
                )
            elif op == "add_annotation" and not intent:
                intent = self._build_annotation_intent(
                    category=category,
                    topic_signals=topic_signals,
                    gap_type="tension",
                    chart_spec=chart_spec if isinstance(chart_spec, dict) else None,
                )
            if op == "add_annotation":
                params.setdefault("max_line_chars", 32)
                params.setdefault("min_font_size", 14)
                params.setdefault("prune_offtopic_annotations", True)
                params.setdefault("include_trendline", False)
            if op == "change_annotation":
                params.setdefault("max_line_chars", 32)
                params.setdefault("min_font_size", 15 if category == "Amplifier" else 14)
                params.setdefault("prune_offtopic_annotations", True)
                if category == "Amplifier":
                    params.setdefault("emphasis_style", "amplify")
            if category == "Bridger" and op not in ("change_color", "change_chart_type"):
                continue
            # Extender/Analyst: block data-selection, axis simplification, and baseline line
            if category in ("Extender", "Analyst") and op in (
                "select_data_variables", "select_data_range", "simplify_axis", "add_data_variables"
            ):
                continue
            refined.append({"operation": op, "layer": layer, "intent": intent, "params": params})

        if category == "Bridger":
            has_chart_type = any(item.get("operation") == "change_chart_type" for item in refined)
            if not has_chart_type:
                refined.insert(0, {
                    "operation": "change_chart_type",
                    "layer": "visual",
                    "intent": "convert to area chart for accessible institutional presentation",
                    "params": {},
                })

        return refined

    def _refine_execution_plan_via_llm(
        self,
        selected_operations: list[dict[str, Any]],
        persona: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        prompt = (
            "You are NodeC execution planner. Convert operation intents into execution-ready intents.\n"
            "Return strict JSON: {\"selected_operations\": [{\"operation\":\"...\",\"layer\":\"data|visual|text\",\"intent\":\"...\",\"params\":{}}]}\n"
            "Rules:\n"
            "- Keep operation order and names unchanged.\n"
            "- For change_title, use exact style intent: `title: <headline>`.\n"
            "- For change_color, include semantic color cue (risk/forest/neutral) or explicit hex.\n"
            "- For add_annotation/change_annotation, write data-grounded text and avoid generic claims.\n"
            "- For Bridger, keep only change_color and change_chart_type, drop other operations.\n"
            "- If change_title appears for Amplifier/Analyst/Adverser, keep paired annotation explaining the title framing.\n"
            "- Use params for directives (e.g., include_trendline, max_line_chars, min_font_size, prune_offtopic_annotations, scope).\n"
            "- Keep intents concise and directly executable.\n"
            f"persona={persona}\ncontext={context}\nselected_operations={selected_operations}\n"
        )
        response = self._chat_completion_json(prompt)
        if not response:
            return None
        ops = response.get("selected_operations")
        if not isinstance(ops, list):
            return None
        normalized: list[dict[str, Any]] = []
        for item in ops:
            if not isinstance(item, dict):
                continue
            op = item.get("operation")
            layer = item.get("layer")
            intent = item.get("intent")
            params = item.get("params")
            if not isinstance(op, str) or not isinstance(layer, str) or not isinstance(intent, str):
                continue
            if layer not in {"data", "visual", "text"}:
                continue
            normalized.append(
                {
                    "operation": op,
                    "layer": layer,
                    "intent": intent,
                    "params": params if isinstance(params, dict) else {},
                }
            )
        if len(normalized) != len(selected_operations):
            return None
        requested_ops = [x.get("operation", "") for x in selected_operations]
        returned_ops = [x.get("operation", "") for x in normalized]
        if requested_ops != returned_ops:
            return None
        return normalized

    @staticmethod
    def _spec_has_legend(spec: dict[str, Any] | None) -> bool:
        if not isinstance(spec, dict):
            return False
        encoding = spec.get("encoding")
        if isinstance(encoding, dict):
            for value in encoding.values():
                if isinstance(value, dict) and isinstance(value.get("legend"), dict):
                    return True
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if isinstance(enc, dict):
                    for value in enc.values():
                        if isinstance(value, dict) and isinstance(value.get("legend"), dict):
                            return True
        return False

    def generate_text(self, prompt: str) -> str | None:
        """Plain-text LLM generation (no JSON constraint). Returns stripped text or None."""
        if not self.enabled or not self.api_key:
            return None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = self._with_provider_payload(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 120,
            }
        )
        try:
            data = self._post_chat(payload, timeout=20.0)
            if not data:
                return None
            content = LLMClient._message_text((data.get("choices") or [{}])[0].get("message") or {})
            return content.strip() or None
        except Exception:
            return None

    def _uses_deepseek(self) -> bool:
        hay = f"{self.model or ''} {self.base_url or ''}".lower()
        return "deepseek" in hay

    def _chat_url(self) -> str:
        base = (self.base_url or "").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if not base.endswith("/v1"):
            # OpenAI-compatible providers (DeepSeek included) expect /v1.
            # https://api.deepseek.com/chat/completions drops larger NodeA prompts;
            # /v1/chat/completions succeeds on the same payload.
            if "deepseek.com" in base.lower() or "openai.com" in base.lower():
                base = f"{base}/v1"
        return f"{base}/chat/completions"

    def _http_client(self, timeout: float) -> httpx.Client:
        # Bind IPv4: this machine's IPv6 path to api.deepseek.com stalls on TLS.
        # Disable keepalive: reused TLS sessions were closing with UNEXPECTED_EOF.
        return httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=8),
            transport=httpx.HTTPTransport(local_address="0.0.0.0", retries=1),
        )

    def _with_provider_payload(self, payload: dict[str, Any], *, thinking: bool = False) -> dict[str, Any]:
        if self._uses_deepseek():
            payload["thinking"] = {"type": "enabled" if thinking else "disabled"}
            if thinking:
                payload["reasoning_effort"] = "high"
        return payload

    @staticmethod
    def _message_text(message: dict[str, Any]) -> str:
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning
        return ""

    @staticmethod
    def _extract_json_object(content: str) -> dict[str, Any] | None:
        text = (content or "").strip()
        if not text:
            return None
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
        decoder = json.JSONDecoder()
        try:
            parsed = decoder.decode(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        # Thinking models often put prose before the object; scan each '{'.
        for match in re.finditer(r"\{", text):
            try:
                parsed, _ = decoder.raw_decode(text, match.start())
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed:
                return parsed
        return None

    @staticmethod
    def _json_from_chat_message(message: dict[str, Any]) -> dict[str, Any] | None:
        blobs: list[str] = []
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        if isinstance(content, str) and content.strip():
            blobs.append(content)
        if isinstance(reasoning, str) and reasoning.strip():
            blobs.append(reasoning)
        for blob in blobs:
            parsed = LLMClient._extract_json_object(blob)
            if parsed is not None:
                return parsed
        return None

    def _post_chat(self, payload: dict[str, Any], timeout: float) -> dict[str, Any] | None:
        import logging
        import time

        logger = logging.getLogger("llm_client")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Connection": "close",
        }
        url = self._chat_url()
        last_error = ""
        for attempt in range(3):
            try:
                with self._http_client(timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                if isinstance(data, dict):
                    return data
            except httpx.TimeoutException:
                last_error = f"timeout after {timeout:.0f}s"
                logger.warning(
                    "LLM call timed out after %.0fs (model=%s, attempt=%d, url=%s)",
                    timeout,
                    self.model,
                    attempt + 1,
                    url,
                )
                time.sleep(0.6 * (attempt + 1))
                continue
            except httpx.HTTPStatusError as exc:
                last_error = f"http {exc.response.status_code}"
                logger.warning("LLM HTTP error: %s (model=%s, url=%s)", exc.response.status_code, self.model, url)
                return None
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.WriteError) as exc:
                last_error = str(exc)[:200]
                logger.warning("LLM call failed: %s (attempt=%d, url=%s)", last_error, attempt + 1, url)
                time.sleep(0.6 * (attempt + 1))
                continue
            except Exception as exc:
                last_error = str(exc)[:200]
                logger.warning("LLM call failed: %s (url=%s)", last_error, url)
                continue
        if last_error:
            logger.warning("LLM call failed after retries: %s (url=%s)", last_error, url)
        return None

    def complete_json(
        self,
        prompt: str,
        timeout: float | None = None,
        max_tokens: int = 0,
        thinking: bool = False,
    ) -> dict[str, Any] | None:
        """JSON completion for NodeA/B, chain planning, and chart reconstruction."""
        if not self.enabled or not self.api_key:
            return None
        return self._chat_completion_json(
            prompt, timeout=timeout, max_tokens=max_tokens, thinking=thinking
        )

    def plan_propagation_chain(
        self,
        source_title: str,
        series_summary: str,
        profiles: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        """One thinking pass: given who will appear, draft each hop's claim."""
        if not profiles:
            return None
        lines = []
        for idx, item in enumerate(profiles, start=1):
            lines.append(
                f"{idx}. role={item.get('role') or 'Amplifier'} platform={item.get('institution') or 'unknown'}"
            )
        prompt = (
            "You plan a framing-shift propagation chain for a data chart. "
            "Think about the WHOLE path before assigning each hop a distinct claim. "
            "Each step must start from the previous hop's claim, not from the original source. "
            "Same role repeated must still escalate (Extender1 broaden, Extender2 add contrast, "
            "Extender3 land on a related implication).\n\n"
            f"Source title: {source_title}\n"
            f"Data: {series_summary}\n"
            "Agents in order (they will execute this sequence as a spine when count <= maxDepth):\n"
            + "\n".join(lines)
            + "\n\nReturn JSON only:\n"
            "{\n"
            '  "story": "one paragraph of how the frame drifts along this chain",\n'
            '  "steps": [\n'
            "    {\n"
            '      "role": "Amplifier|Extender|Adverser|Bridger|Analyst",\n'
            '      "institution": "...",\n'
            '      "incoming_focus": "what this agent sees from the parent",\n'
            '      "agent_claim": "the headline this hop must make visually inevitable",\n'
            '      "structural_move": "crop window / add comparison / rechart / oppose, not merely recolor"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "steps length MUST equal the agent list. Do not invent extra agents.\n"
            "After any internal reasoning, the final message must be the JSON object only.\n"
        )
        parsed = self.complete_json(prompt, timeout=60.0, max_tokens=2000, thinking=True)
        if not parsed or not isinstance(parsed.get("steps"), list):
            return None
        steps = [item for item in parsed["steps"] if isinstance(item, dict)]
        if len(steps) != len(profiles):
            return None
        return {
            "story": str(parsed.get("story") or ""),
            "steps": steps,
        }

    def _chat_completion_json(
        self,
        prompt: str,
        timeout: float | None = None,
        max_tokens: int = 0,
        thinking: bool = False,
    ) -> dict[str, Any] | None:
        import logging

        logger = logging.getLogger("llm_client")
        if timeout is None:
            if thinking:
                timeout = 90.0
            elif self._uses_deepseek():
                timeout = 60.0
            else:
                timeout = 30.0
        if self._uses_deepseek():
            attempts: list[dict[str, Any]] = [{}]
        else:
            attempts = [{"response_format": {"type": "json_object"}}, {}]
        for extra in attempts:
            payload = self._with_provider_payload(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    **extra,
                },
                thinking=thinking,
            )
            if max_tokens > 0:
                payload["max_tokens"] = max_tokens
            data = self._post_chat(payload, timeout=timeout)
            if not data:
                continue
            message = (data.get("choices") or [{}])[0].get("message") or {}
            parsed = LLMClient._json_from_chat_message(message)
            if parsed is None:
                preview = LLMClient._message_text(message)[:160].replace("\n", " ")
                if not preview:
                    logger.warning(
                        "LLM empty content (model=%s, keys=%s, thinking=%s)",
                        self.model,
                        list(message.keys()),
                        thinking,
                    )
                else:
                    logger.warning("LLM returned invalid JSON: %s", preview)
                continue
            content = LLMClient._message_text(message)
            logger.info(
                "LLM call succeeded (model=%s, response_len=%d, thinking=%s)",
                self.model,
                len(content),
                thinking,
            )
            return parsed
        return None

