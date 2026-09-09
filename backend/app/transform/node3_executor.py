from __future__ import annotations

import copy
from dataclasses import dataclass
import re
from typing import Any


SOURCE_PREFIX_RE = re.compile(r"^\s*(source:|sources:|data source|via|from)", re.IGNORECASE)


@dataclass
class ExecutionResult:
    updated_chart_spec: dict[str, Any] | None
    executed_operations: list[dict[str, Any]]
    operation_audit: list[dict[str, Any]]
    layers_affected: list[str]
    variant_description: str


class Node3Executor:
    """
    Spec patcher for Node3 M2.

    Supports LLM-driven text generation for titles and annotations when an
    LLM client is provided, with data-driven role-specific fallbacks.
    """

    # ── Taxonomy persona prompts (Section 2, taxonomy_backend_eng_v3) ──
    _PERSONA_PROMPTS: dict[str, str] = {
        "Amplifier": (
            "You are an AMPLIFIER performing a FRAMING SHIFT on a source visualization. "
            "Your mission: based on your role and platform, modify the chart to AMPLIFY the most "
            "dramatic angle of the existing data narrative. Change the packaging, not the data itself. "
            "Strategy: 'narrow and amplify' — strengthen the existing narrative, make it more visible "
            "and emotionally impactful. Use emphatic, striking language designed for maximum engagement. "
            "News media Amplifier: urgent but factual. Social media Amplifier: alarming, BREAKING style."
        ),
        "Extender": (
            "You are an EXTENDER performing a FRAMING SHIFT on a source visualization. "
            "Your mission: based on your role and platform, modify the chart to EXPAND the topic "
            "into broader or adjacent domains — connecting the data to related policy, social, or "
            "systemic issues. Strategy: 'broaden the scope'. Use analytical, contextualizing language. "
            "DO NOT use select_data_range or select_data_variables — keep the full data intact."
        ),
        "Adverser": (
            "You are an ADVERSER performing a FRAMING SHIFT on a source visualization. "
            "Your mission: based on your role and platform, construct a COUNTER-NARRATIVE that opposes "
            "the mainstream interpretation. Find a specific window where the data goes AGAINST the "
            "overall trend, select only that window, and write a title that challenges the upstream framing. "
            "Strategy: 'reshape the evidence base'. Use provocative, counter-narrative language."
        ),
        "Bridger": (
            "You are a BRIDGER performing a FRAMING SHIFT on a source visualization. "
            "Your mission: present information accessibly and objectively, transferring legitimacy "
            "to the visualization without distorting it. Strategy: neutral, institutional tone. "
            "You inform rather than persuade — change chart type to area chart with purple palette, keep title factual."
        ),
    }

    # ── Corpus-derived few-shot examples for title and annotation generation ──
    _TITLE_EXAMPLES: str = (
        "=== FEW-SHOT: Real framing-shift propagation chain (COVID excess deaths) ===\n"
        "Source (Bridger/Government): 'Deaths not involving COVID-19 remained below the five-year average in Week 47'\n"
        "  → Amplifier (News media):   'Covid Deaths Rise Again'\n"
        "  → Amplifier (Social media): 'BREAKING: UK Covid Deaths SURGE to New Autumn High'\n"
        "  → Adverser (Social media):  '\"Covid Deaths Are Rising\" Is a HOAX — Deaths Actually Fell'\n"
        "       [selected weeks 16-36 where COVID deaths fell from 8,758 to 78]\n"
        "  → Extender (News media):    'How the Pandemic Has Affected Excess Deaths'\n"
        "\n"
        "=== FEW-SHOT: Climate temperature anomaly ===\n"
        "Source (Bridger): 'Global Land and Ocean Average Temperature Anomaly (1880-2024)'\n"
        "  → Amplifier (News):   'World Set for Hottest Year on Record'\n"
        "  → Amplifier (Social): 'BREAKING: Earth Just Hit Its Hottest Year EVER'\n"
        "  → Adverser:           'Global Cooling Since 2016' [selected recent dip window]\n"
        "  → Extender:           'Rising Temperatures and the Push for Climate Action'\n"
        "\n"
        "=== FEW-SHOT: Deforestation ===\n"
        "Source (Bridger): 'Deforestation Rates - Legal Amazon - States'\n"
        "  → Amplifier: 'Amazon Deforestation Highest Since 2006'\n"
        "  → Extender:  'Deforestation, Land Use Policy, and Carbon Targets'\n"
    )

    # ── Corpus-derived few-shot examples for annotation generation ──
    _ANNOTATION_EXAMPLES: str = (
        "Annotation examples from real propagation cases:\n"
        "- Amplifier (News media): 'Deaths peaked at 8,758 in week 16; now rising again to 2,697'\n"
        "- Amplifier (Social media): '2,697 deaths in week 47 — autumn wave accelerating' [MORE aggressive]\n"
        "- Adverser: 'Deaths fell 99% — from 8,758 to 78 — between week 16 and week 36'\n"
        "- Extender: 'Peak at week 16 coincided with overwhelmed hospitals and surge in delayed non-COVID care'\n"
        "- Amplifier (climate): 'Highest since 2006' (reinforcing title claim)\n"
        "- Adverser (climate): 'Cooling trend since 2016' (counter-narrative, concise)\n"
    )

    @staticmethod
    def _humanize_field_name(field: str) -> str:
        """Convert raw Vega-Lite field names to human-readable labels.
        'excess_deaths_per_100k' → 'Excess Deaths per 100k'
        """
        if not field:
            return ""
        stop_words = {"per", "in", "of", "the", "and", "or", "at", "by", "to"}
        words = field.replace("_", " ").replace("-", " ").split()
        result = " ".join(w if w in stop_words else w.capitalize() for w in words)
        return result[0].upper() + result[1:] if result else ""

    @staticmethod
    def _extract_axis_title(spec: dict[str, Any] | None, target_field: str, axis: str = "y") -> str | None:
        """Extract axis.title for a field from Vega-Lite spec. Falls back to first axis title found."""
        if not isinstance(spec, dict):
            return None
        first_any: str | None = None

        def _from_enc(enc: dict[str, Any] | None) -> str | None:
            nonlocal first_any
            if not isinstance(enc, dict):
                return None
            ch = enc.get(axis)
            if not isinstance(ch, dict):
                return None
            ax = ch.get("axis")
            if isinstance(ax, dict) and isinstance(ax.get("title"), str):
                t = ax["title"]
                if first_any is None:
                    first_any = t
                if ch.get("field") == target_field:
                    return t
            return None

        r = _from_enc(spec.get("encoding"))
        if r:
            return r
        for layer in (spec.get("layer") or []):
            if isinstance(layer, dict):
                r = _from_enc(layer.get("encoding"))
                if r:
                    return r
        return first_any

    def __init__(self, llm_client: Any = None) -> None:
        self.llm_client = llm_client
        self._current_role: str = ""
        self._current_institution: str = ""
        self._current_depth: int = 1
        self._last_title_applied: str = ""

    def execute(
        self,
        parent_chart_spec: dict[str, Any] | None,
        selected_operations: list[dict[str, Any]],
        shift_magnitude: str,
        role: str = "",
        institution: str = "",
        depth: int = 1,
    ) -> ExecutionResult:
        self._current_role = role
        self._current_institution = institution
        self._current_depth = depth

        if parent_chart_spec is None:
            return ExecutionResult(
                updated_chart_spec=None,
                executed_operations=[],
                operation_audit=[],
                layers_affected=[],
                variant_description="无可用 chart_spec，保留文本层描述。",
            )

        spec = copy.deepcopy(parent_chart_spec)
        executed: list[dict[str, Any]] = []
        operation_audit: list[dict[str, Any]] = []
        layers: set[str] = set()

        for op_item in selected_operations:
            op = op_item.get("operation", "")
            intent = op_item.get("intent", "")
            params = op_item.get("params", {})
            if not isinstance(params, dict):
                params = {}
            if op == "change_title":
                ok, before, after = self._change_title(spec, intent, params)
                if ok:
                    executed.append(Node3Executor._build_op_record(op, intent, params, before, after, "applied", "", ["$.title"]))
                    layers.add("text")
                operation_audit.append(
                    Node3Executor._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "title_missing", ["$.title"])
                )
            elif op == "add_annotation":
                ok, before, after = self._add_annotation(spec, intent, params)
                if ok:
                    executed.append(
                        self._build_op_record(op, intent, params, before, after, "applied", "", ["$.layer[*]", "$.description", "$.usermeta.annotations"])
                    )
                    layers.add("text")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "annotation_target_missing",
                        ["$.layer[*]", "$.description", "$.usermeta.annotations"],
                    )
                )
            elif op == "change_annotation":
                ok, before, after = self._change_annotation(spec, intent, params)
                if ok:
                    executed.append(
                        self._build_op_record(op, intent, params, before, after, "applied", "", ["$.layer[*].mark.text", "$.description"])
                    )
                    layers.add("text")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "annotation_not_found",
                        ["$.layer[*].mark.text", "$.description"],
                    )
                )
            elif op == "delete_source":
                ok, before, after = self._delete_source(spec)
                if ok:
                    executed.append(
                        self._build_op_record(
                            op,
                            intent,
                            params,
                            before,
                            after,
                            "applied",
                            "",
                            ["$.layer[*].mark.text", "$.description", "$.usermeta.source"],
                        )
                    )
                    layers.add("text")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "source_not_found",
                        ["$.layer[*].mark.text", "$.description", "$.usermeta.source"],
                    )
                )
            elif op == "change_color":
                ok, before, after = self._change_color(spec, intent, params)
                if ok:
                    executed.append(
                        self._build_op_record(
                            op,
                            intent,
                            params,
                            before,
                            after,
                            "applied",
                            "",
                            ["$.mark.color", "$.encoding.color.scale.range", "$.config.range.category"],
                        )
                    )
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "color_target_missing",
                        ["$.mark.color", "$.encoding.color.scale.range", "$.config.range.category"],
                    )
                )
            elif op == "simplify_axis":
                ok, before, after = self._simplify_axis(spec, params)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding.x.axis"]))
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "x_axis_missing", ["$.encoding.x.axis"])
                )
            elif op == "change_axis_scale":
                ok, before, after = self._change_axis_scale(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding.x.scale", "$.encoding.y.scale"]))
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "quantitative_axis_missing",
                        ["$.encoding.x.scale", "$.encoding.y.scale"],
                    )
                )
            elif op == "change_chart_type":
                ok, before, after = self._change_chart_type(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.mark.type", "$.layer[*].mark.type"]))
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(
                        op,
                        intent,
                        params,
                        before,
                        after,
                        "applied" if ok else "skipped",
                        "" if ok else "mark_type_missing",
                        ["$.mark.type", "$.layer[*].mark.type"],
                    )
                )
            elif op == "add_background":
                ok, before, after = self._add_background(spec)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.view.fill", "$.background"]))
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "background_unchanged", ["$.view.fill", "$.background"])
                )
            elif op == "change_aspect_ratio":
                ok, before, after = self._change_aspect_ratio(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.width", "$.height"]))
                    layers.add("visual")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "size_unchanged", ["$.width", "$.height"])
                )
            elif op == "select_data_range":
                ok, before, after = self._select_data_range(spec, params)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.transform[*].filter"]))
                    layers.add("data")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "x_field_missing", ["$.transform[*].filter"])
                )
            elif op == "select_data_variables":
                ok, before, after = self._select_data_variables(spec)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding"]))
                    layers.add("data")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "no_optional_channel", ["$.encoding"])
                )
            elif op == "change_data_granularity":
                ok, before, after = self._change_data_granularity(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding.x.timeUnit"]))
                    layers.add("data")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "temporal_x_missing", ["$.encoding.x.timeUnit"])
                )
            elif op == "add_data_variables":
                ok, before, after = self._add_data_variables(spec)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.layer[*]"]))
                    layers.add("data")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "reference_layer_failed", ["$.layer[*]"])
                )
            elif op == "change_legend":
                ok, before, after = self._change_legend(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding.*.legend"]))
                    layers.add("text")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else "legend_target_missing", ["$.encoding.*.legend"])
                )
            elif op == "add_legend":
                ok, before, after = self._add_legend(spec, intent)
                if ok:
                    executed.append(self._build_op_record(op, intent, params, before, after, "applied", "", ["$.encoding.*.legend"]))
                    layers.add("text")
                operation_audit.append(
                    self._build_op_record(op, intent, params, before, after, "applied" if ok else "skipped", "" if ok else after, ["$.encoding.*.legend"])
                )
            else:
                operation_audit.append(
                    self._build_op_record(op or "unknown", intent, params, "(n/a)", "unchanged", "skipped", "unsupported_operation", [])
                )

        if not executed:
            return ExecutionResult(
                updated_chart_spec=spec,
                executed_operations=[],
                operation_audit=operation_audit,
                layers_affected=[],
                variant_description="未应用可执行操作，保留原始图表结构。",
            )

        # Safety: if operations emptied data that was originally present, roll back
        had_data = not Node3Executor._is_chart_data_empty(parent_chart_spec)
        if had_data and Node3Executor._is_chart_data_empty(spec):
            spec = copy.deepcopy(parent_chart_spec)
            operation_audit.append(
                self._build_op_record(
                    "safety_rollback", "data became empty after operations", {},
                    "empty", "restored", "applied", "", [],
                )
            )

        layer_code = "+".join({"data": "D", "visual": "V", "text": "T"}[x] for x in sorted(layers))
        desc = f"执行 {len(executed)} 项操作（{layer_code}），偏移等级 {shift_magnitude}。"
        return ExecutionResult(
            updated_chart_spec=spec,
            executed_operations=executed,
            operation_audit=operation_audit,
            layers_affected=sorted(layers),
            variant_description=desc,
        )

    @staticmethod
    def _is_chart_data_empty(spec: dict[str, Any]) -> bool:
        """Check if the chart spec has any visible data rows remaining."""
        data = spec.get("data")
        if isinstance(data, dict):
            vals = data.get("values")
            if isinstance(vals, list) and len(vals) > 0:
                return False
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("data")
                if isinstance(item_data, dict):
                    vals = item_data.get("values")
                    if isinstance(vals, list) and len(vals) > 0:
                        return False
                elif isinstance(data, dict):
                    vals = data.get("values")
                    if isinstance(vals, list) and len(vals) > 0:
                        return False
        return True

    @staticmethod
    def _build_op_record(
        operation: str,
        intent: str,
        params: dict[str, Any],
        before: str,
        after: str,
        status: str,
        error: str,
        target_paths: list[str],
    ) -> dict[str, Any]:
        return {
            "operation": operation,
            "params": {"intent": intent, **params},
            "target_paths": target_paths,
            "before": before,
            "after": after,
            "status": status,
            "error": error,
        }

    def _change_title(self, spec: dict[str, Any], intent: str, params: dict[str, Any]) -> tuple[bool, str, str]:
        before = str(spec.get("title", ""))
        if isinstance(spec.get("title"), dict):
            before = str(spec["title"].get("text", before))

        title_from_intent = Node3Executor._extract_title_from_intent(intent)
        if not title_from_intent:
            title_from_intent = self._generate_title(spec, intent, before)

        title_from_intent = Node3Executor._enforce_text_length(title_from_intent, is_title=True)
        title_from_intent = Node3Executor._wrap_text(title_from_intent, params.get("max_line_chars"))

        if isinstance(spec.get("title"), dict):
            spec["title"]["text"] = title_from_intent
            spec["title"].setdefault("fontSize", 22)
        else:
            spec["title"] = {"text": title_from_intent, "fontSize": 22}

        # Visually mark the title as modified by this role via color
        title_color = self._role_text_color()
        if title_color:
            spec["title"]["color"] = title_color

        self._last_title_applied = title_from_intent
        return True, before or "(none)", title_from_intent

    def _add_annotation(self, spec: dict[str, Any], intent: str, params: dict[str, Any]) -> tuple[bool, str, str]:
        raw_text = Node3Executor._clean_annotation_text(Node3Executor._extract_annotation_text(intent))
        if not raw_text or Node3Executor._is_generic_intent(raw_text):
            raw_text = self._generate_annotation(spec, intent)
        text = Node3Executor._enforce_text_length(raw_text, is_title=False)
        # Wrapping is deferred to _build_data_annotation_layers which computes
        # font-aware max chars per line. Pre-wrapping here with a fixed 34 was
        # too narrow and split text into choppy fragments.
        add_trendline = False
        if params.get("prune_offtopic_annotations"):
            Node3Executor._prune_offtopic_annotations(spec, params.get("narrative_keywords"))
        default_font = 14 if self._current_role in ("Extender", "Analyst") else 20
        min_font_size = Node3Executor._normalize_font_size(params.get("min_font_size"), default_font)
        layer = spec.get("layer")
        # In-chart first: append text layer when layered spec exists.
        if isinstance(layer, list):
            before = str(len(layer))
            anchor = self._pick_annotation_anchor(spec, intent)
            if anchor:
                canvas_width, _ = Node3Executor._annotation_canvas_bounds(spec)
                ann_color = self._role_text_color() or "#202124"
                layer.extend(
                    Node3Executor._build_data_annotation_layers(
                        anchor=anchor,
                        text=text,
                        existing_layers=layer,
                        include_trendline=add_trendline,
                        min_font_size=min_font_size,
                        canvas_width=canvas_width,
                        text_color=ann_color,
                    )
                )
                # Extender/Analyst: highlight the annotated data bar with themed color
                if self._current_role in ("Extender", "Analyst"):
                    self._highlight_annotated_bar(spec, anchor)
                return True, f"layer_count={before}", f"layer_count={len(layer)} (data_anchor)"
            x_value, y_value = Node3Executor._next_annotation_position(layer, spec)
            canvas_w, _ = Node3Executor._annotation_canvas_bounds(spec)
            text_limit_px = max(280, int(canvas_w * 0.65))
            fallback_color = self._role_text_color() or "#444444"
            layer.append(
                {
                    "description": "Node3 added annotation",
                    "data": {"values": [{"dummy": 1}]},
                    "mark": {
                        "type": "text",
                        "align": "left",
                        "baseline": "top",
                        "text": text,
                        "color": fallback_color,
                        "fontSize": min_font_size,
                        "lineHeight": min_font_size + 4,
                        "fontWeight": 600,
                        "limit": text_limit_px,
                    },
                    "encoding": {"x": {"value": x_value}, "y": {"value": y_value}},
                }
            )
            return True, f"layer_count={before}", f"layer_count={len(layer)}"

        # Fallback: append to top-level description.
        desc = spec.get("description")
        before_desc = str(desc) if isinstance(desc, str) else ""
        if before_desc:
            spec["description"] = f"{before_desc} | NOTE: {text}"
        else:
            spec["description"] = f"NOTE: {text}"
        return True, before_desc or "(none)", str(spec["description"])

    def _highlight_annotated_bar(self, spec: dict[str, Any], anchor: dict[str, Any]) -> None:
        """Highlight the specific bar referenced by the Extender's annotation.

        Uses a soft analytical palette: the annotated bar gets a themed accent color
        while other bars get a lighter muted tone (not full gray — keeps readability).
        Randomly picks between a few analytical color schemes for variety.
        """
        import random
        x_field = anchor.get("x_field", "")
        x_value = anchor.get("x_value")
        if not x_field or x_value is None:
            return

        highlight_color = self._pick_extender_highlight_color()
        # Pick from analytical muted palettes — occasionally a warmer or cooler tone
        _muted_palettes = [
            "#B0BEC5",   # blue-gray (neutral)
            "#90A4AE",   # steel gray
            "#78909C",   # cool slate
            "#A1887F",   # warm taupe
            "#8D9CA8",   # periwinkle gray
            "#9E9E9E",   # mid gray
            "#7E9AA0",   # muted teal
            "#8E99A4",   # blue-steel
        ]
        muted_color = random.choice(_muted_palettes)

        layer = spec.get("layer")
        if not isinstance(layer, list):
            return

        for item in layer:
            if not isinstance(item, dict):
                continue
            mark = item.get("mark")
            mark_type = Node3Executor._mark_type(mark)
            if mark_type not in ("bar", "area", "line", "point", "circle", "trail", "arc"):
                continue
            desc = item.get("description", "")
            if isinstance(desc, str) and desc.startswith("Node3 added"):
                continue
            enc = item.get("encoding")
            if not isinstance(enc, dict):
                continue
            x_enc = enc.get("x", {})
            if not isinstance(x_enc, dict):
                continue
            layer_x_field = x_enc.get("field", "")
            if layer_x_field != x_field:
                continue
            # Skip multi-series charts (field-based color encoding)
            existing_color = enc.get("color", {})
            if isinstance(existing_color, dict) and existing_color.get("field"):
                continue

            # CRITICAL: remove mark-level color — it overrides encoding.color in Vega-Lite
            if isinstance(mark, dict) and "color" in mark:
                del mark["color"]
            if isinstance(mark, dict) and "fill" in mark:
                del mark["fill"]

            x_type = x_enc.get("type", "nominal")
            if x_type in ("quantitative", "temporal"):
                test_expr = f"datum['{x_field}'] === {x_value!r}"
            else:
                test_expr = f"datum['{x_field}'] === '{x_value}'"

            enc["color"] = {
                "condition": {"test": test_expr, "value": highlight_color},
                "value": muted_color,
                "_node3_highlight": True,
            }

            # Sync annotation anchor point color
            for ann_layer in layer:
                if (isinstance(ann_layer, dict)
                        and isinstance(ann_layer.get("description"), str)
                        and ann_layer["description"] == "Node3 added annotation anchor"):
                    ann_mark = ann_layer.get("mark")
                    if isinstance(ann_mark, dict):
                        ann_mark["color"] = highlight_color
            break

    def _role_text_color(self) -> str:
        """Return a text color that signals this role modified the title/annotation.

        Different roles get distinct hues so viewers can immediately see which
        agent changed what.  Returns '' for roles that should keep default black.
        """
        role = self._current_role or ""
        institution = self._current_institution or ""
        platform = self._infer_platform_bucket_local(institution)

        _role_colors: dict[str, dict[str, str]] = {
            "Extender": {
                "t1_authority": "#1A237E", "t2_news": "#4527A0",
                "t3_social": "#00695C", "t4_ugc": "#006064",
                "t5_blog": "#4A148C", "t6_data": "#01579B",
                "default": "#283593",
            },
            "Analyst": {
                "t1_authority": "#37474F", "t2_news": "#5C6BC0",
                "t3_social": "#7E57C2", "t4_ugc": "#6A1B9A",
                "t5_blog": "#512DA8", "t6_data": "#455A64",
                "default": "#5C6BC0",
            },
            "Amplifier": {
                "t1_authority": "#E65100", "t2_news": "#F4511E",
                "t3_social": "#FF5722", "t4_ugc": "#FF6D00",
                "t5_blog": "#E64A19", "t6_data": "#F57C00",
                "default": "#FF5722",
            },
            "Adverser": {
                "t1_authority": "#C62828", "t2_news": "#D32F2F",
                "t3_social": "#F44336", "t4_ugc": "#E53935",
                "t5_blog": "#EF5350", "t6_data": "#E53935",
                "default": "#E53935",
            },
        }
        palette = _role_colors.get(role)
        if not palette:
            return ""
        return palette.get(platform, palette["default"])

    def _pick_extender_highlight_color(self) -> str:
        """Topic-themed highlight color for the annotated bar."""
        import random
        topic = self._infer_topic_from_context()
        institution = self._current_institution or ""
        platform = self._infer_platform_bucket_local(institution)

        _accent = {
            "deforestation": {"t1_authority":"#1B5E20","t2_news":"#2E7D32","t3_social":"#43A047","t4_ugc":"#4CAF50","t5_blog":"#558B2F","t6_data":"#388E3C","default":"#2E7D32"},
            "climate": {"t1_authority":"#0D47A1","t2_news":"#1565C0","t3_social":"#EF6C00","t4_ugc":"#F9A825","t5_blog":"#0277BD","t6_data":"#1976D2","default":"#1565C0"},
            "health": {"t1_authority":"#1565C0","t2_news":"#6A1B9A","t3_social":"#7B1FA2","t4_ugc":"#00695C","t5_blog":"#4A148C","t6_data":"#00838F","default":"#6A1B9A"},
            "economy": {"t1_authority":"#37474F","t2_news":"#EF6C00","t3_social":"#FF8F00","t4_ugc":"#5D4037","t5_blog":"#F57F17","t6_data":"#455A64","default":"#EF6C00"},
            "unemployment": {"t1_authority":"#263238","t2_news":"#4E342E","t3_social":"#FF8F00","t4_ugc":"#6D4C41","t5_blog":"#795548","t6_data":"#546E7A","default":"#4E342E"},
        }
        if topic in _accent:
            return _accent[topic].get(platform, _accent[topic]["default"])

        # Analytical color palette — cycle between cool blues, teals, and slate purples
        _analytical = [
            "#37474F", "#455A64", "#546E7A",  # blue-gray slate
            "#00695C", "#00796B", "#00838F",  # teal
            "#283593", "#303F9F", "#3949AB",  # indigo
            "#4527A0", "#512DA8", "#5C6BC0",  # deep purple
        ]
        return random.choice(_analytical)

    def _infer_topic_from_context(self) -> str:
        """Best-effort topic detection from applied title + institution."""
        title = getattr(self, "_last_title_applied", "") or ""
        inst = (self._current_institution or "").lower()
        combined = f"{title.lower()} {inst}"
        if any(t in combined for t in ("deforest", "amazon", "forest", "land use")):
            return "deforestation"
        if any(t in combined for t in ("covid", "pandemic", "death", "mortality", "health", "nhs")):
            return "health"
        if any(t in combined for t in ("inflation", "cpi", "price", "cost", "economy", "gdp")):
            return "economy"
        if any(t in combined for t in ("unemploy", "job", "labor", "labour", "workforce")):
            return "unemployment"
        if any(t in combined for t in ("climate", "temperature", "warming", "paris")):
            return "climate"
        return ""

    @staticmethod
    def _delete_source(spec: dict[str, Any]) -> tuple[bool, str, str]:
        removed = 0
        kept_layers: list[Any] = []
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                text = (
                    item.get("mark", {}).get("text")
                    if isinstance(item, dict) and isinstance(item.get("mark"), dict)
                    else None
                )
                if isinstance(text, str) and SOURCE_PREFIX_RE.match(text):
                    removed += 1
                    continue
                kept_layers.append(item)
            spec["layer"] = kept_layers

        # Also sanitize top-level description/usermeta.source with strict prefix rule.
        desc = spec.get("description")
        if isinstance(desc, str) and SOURCE_PREFIX_RE.match(desc):
            spec["description"] = ""
            removed += 1
        usermeta = spec.get("usermeta")
        if isinstance(usermeta, dict):
            source_text = usermeta.get("source")
            if isinstance(source_text, str) and SOURCE_PREFIX_RE.match(source_text):
                usermeta["source"] = ""
                removed += 1

        if removed == 0:
            return False, "no source attribution matched", "unchanged"
        return True, f"removed={removed}", "source attribution removed"

    def _change_color(self, spec: dict[str, Any], intent: str, params: dict[str, Any]) -> tuple[bool, str, str]:
        palette = self._pick_palette_for_role(spec, intent)
        palette_range = Node3Executor._build_palette_range(palette, str(params.get("palette_style", "default")))
        changed = 0
        before_values: list[str] = []
        # Try layered marks first.
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                mark = item.get("mark")
                can_recolor_item = Node3Executor._is_recolorable_mark(mark)

                enc = item.get("encoding", {}) if isinstance(item.get("encoding"), dict) else {}
                enc_color = enc.get("color")

                # Only protect conditionals that WE added (tagged with _node3_highlight).
                # Original chart conditionals (e.g. highlight-2025) should be replaced.
                is_our_highlight = (
                    isinstance(enc_color, dict)
                    and isinstance(enc_color.get("condition"), dict)
                    and enc_color.get("_node3_highlight") is True
                )

                if is_our_highlight:
                    continue

                if can_recolor_item and isinstance(mark, dict):
                    old = mark.get("color")
                    if old != palette:
                        before_values.append(str(old))
                        mark["color"] = palette
                        changed += 1

                # Replace encoding.color: conditionals, flat values, datum, or scaled ranges
                if can_recolor_item and isinstance(enc_color, dict):
                    has_condition = isinstance(enc_color.get("condition"), dict)
                    has_scale = isinstance(enc_color.get("scale"), dict)
                    has_field = bool(enc_color.get("field"))
                    has_datum = "datum" in enc_color and not has_field
                    has_value = "value" in enc_color and not has_condition and not has_field

                    if has_datum:
                        before_values.append(str(enc_color.get("datum", "")))
                        enc["color"] = {"value": palette}
                        changed += 1
                    elif has_condition and not has_field:
                        before_values.append(str(enc_color))
                        enc["color"] = {"value": palette}
                        changed += 1
                    elif has_value:
                        old_val = enc_color.get("value")
                        if old_val != palette:
                            before_values.append(str(old_val))
                            enc_color["value"] = palette
                            changed += 1
                    elif has_scale or has_field:
                        scale = enc_color.get("scale")
                        if not isinstance(scale, dict):
                            scale = {}
                            enc_color["scale"] = scale
                        old = str(scale.get("range", ""))
                        if old != str(palette_range):
                            before_values.append(old)
                            scale["range"] = palette_range
                            changed += 1
                        changed += Node3Executor._recolor_color_channel_values(enc_color, palette, before_values)

        mark = spec.get("mark")
        can_recolor_top = Node3Executor._is_recolorable_mark(mark)
        if can_recolor_top and isinstance(mark, dict):
            old = mark.get("color")
            if old != palette:
                before_values.append(str(old))
                mark["color"] = palette
                changed += 1
        top_encoding = spec.get("encoding")
        if can_recolor_top and isinstance(top_encoding, dict) and isinstance(top_encoding.get("color"), dict):
            color_channel = top_encoding["color"]
            scale = color_channel.get("scale")
            if not isinstance(scale, dict):
                scale = {}
                color_channel["scale"] = scale
            old = str(scale.get("range", ""))
            if old != str(palette_range):
                before_values.append(old)
                scale["range"] = palette_range
                changed += 1
            changed += Node3Executor._recolor_color_channel_values(color_channel, palette, before_values)
        config = spec.get("config")
        if not isinstance(config, dict):
            config = {}
            spec["config"] = config
        config_range = config.get("range")
        if not isinstance(config_range, dict):
            config_range = {}
            config["range"] = config_range
        old_cfg = str(config_range.get("category", ""))
        if old_cfg != str(palette_range):
            config_range["category"] = palette_range
            changed += 1
        if changed == 0:
            return False, "no color target found", "unchanged"
        return True, f"changed={changed} from={before_values[:2]}", palette

    @staticmethod
    def _recolor_color_channel_values(color_channel: dict[str, Any], palette: str, before_values: list[str]) -> int:
        changed = 0
        condition = color_channel.get("condition")
        if isinstance(condition, dict):
            value = condition.get("value")
            if isinstance(value, str) and value != palette:
                before_values.append(value)
                condition["value"] = palette
                changed += 1
        elif isinstance(condition, list):
            for cond in condition:
                if not isinstance(cond, dict):
                    continue
                value = cond.get("value")
                if isinstance(value, str) and value != palette:
                    before_values.append(value)
                    cond["value"] = palette
                    changed += 1

        base_value = color_channel.get("value")
        secondary = Node3Executor._derive_secondary_color(palette)
        if isinstance(base_value, str) and base_value != secondary:
            before_values.append(base_value)
            color_channel["value"] = secondary
            changed += 1
        return changed

    @staticmethod
    def _derive_secondary_color(primary: str) -> str:
        """Derive a coordinated secondary color from the primary palette color.
        Uses a 35% darkening of the primary rather than a lookup table,
        so it works with any depth-darkened or custom color."""
        return Node3Executor._darken_hex(primary, 0.35)

    def _select_data_range(self, spec: dict[str, Any], params: dict[str, Any]) -> tuple[bool, str, str]:
        field = str(params.get("x_field", "")).strip() or Node3Executor._pick_x_field(spec)
        if not field:
            return False, "no field found", "unchanged"
        transform = spec.get("transform")
        if not isinstance(transform, list):
            transform = []
            spec["transform"] = transform
        before = str(len(transform))
        start = params.get("start")
        end = params.get("end")
        if start is None or end is None:
            inferred = self._infer_default_range_window(spec, field)
            if inferred is not None:
                start, end = inferred
        if start is not None and end is not None:
            surviving = Node3Executor._count_surviving_rows(spec, field, start, end)
            if surviving < 2:
                return False, f"range [{start},{end}] would leave only {surviving} rows", "unchanged"
            filter_expr = {
                "filter": (
                    f"datum['{field}'] >= {Node3Executor._js_literal(start)} && "
                    f"datum['{field}'] <= {Node3Executor._js_literal(end)}"
                )
            }
            transform.append(filter_expr)
            # For layered specs, also add transform to layers whose data contains the field
            layer = spec.get("layer")
            if isinstance(layer, list):
                for item in layer:
                    if not isinstance(item, dict):
                        continue
                    item_data = item.get("data")
                    if isinstance(item_data, dict) and isinstance(item_data.get("values"), list):
                        sample = item_data["values"][:5]
                        if not any(isinstance(r, dict) and field in r for r in sample):
                            continue
                        item_transform = item.get("transform")
                        if not isinstance(item_transform, list):
                            item_transform = []
                            item["transform"] = item_transform
                        item_transform.append(filter_expr)
            domain_updates = Node3Executor._apply_x_domain_window(spec, field, start, end)
            Node3Executor._widen_bars_for_narrow_range(spec, field, start, end)
            Node3Executor._trim_data_values_to_range(spec, field, start, end)
            Node3Executor._prune_sparse_decoration_layers(spec)
            # Drop only the range filters we just added. Keep fold/calculate.
            Node3Executor._drop_range_filters(spec, field)
            layer_list = spec.get("layer")
            if isinstance(layer_list, list):
                for item in layer_list:
                    if isinstance(item, dict):
                        mark_obj = item.get("mark")
                        if isinstance(mark_obj, dict):
                            mark_obj.pop("clip", None)
            return (
                True,
                f"transform_count={before}",
                f"transform_count={len(transform)} expr_range=[{start},{end}] domain_updates={domain_updates}",
            )
        transform.append({"filter": {"field": field, "valid": True}})
        return True, f"transform_count={before}", f"transform_count={len(transform)} valid_only"

    @staticmethod
    def _count_surviving_rows(spec: dict[str, Any], field: str, start: Any, end: Any) -> int:
        """Count how many data rows would survive after filtering to [start, end]."""
        def _in_range(v: Any) -> bool:
            try:
                return float(v) >= float(start) and float(v) <= float(end)
            except (TypeError, ValueError):
                return str(start) <= str(v) <= str(end)

        count = 0
        data_obj = spec.get("data")
        if isinstance(data_obj, dict) and isinstance(data_obj.get("values"), list):
            count += sum(1 for row in data_obj["values"] if isinstance(row, dict) and _in_range(row.get(field)))
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("data")
                if isinstance(item_data, dict) and isinstance(item_data.get("values"), list):
                    count += sum(1 for row in item_data["values"] if isinstance(row, dict) and _in_range(row.get(field)))
        return count

    @staticmethod
    def _drop_range_filters(spec: dict[str, Any], field: str) -> None:
        """Remove range-window filters after values are already trimmed. Keep fold/calculate."""

        def _keep(transform: Any) -> bool:
            if not isinstance(transform, dict) or "filter" not in transform:
                return True
            filt = transform.get("filter")
            if isinstance(filt, str) and f"datum['{field}']" in filt:
                return False
            if isinstance(filt, dict) and str(filt.get("field") or "") == field:
                return False
            return True

        def _clean(holder: dict[str, Any]) -> None:
            transforms = holder.get("transform")
            if not isinstance(transforms, list):
                return
            kept = [item for item in transforms if _keep(item)]
            if kept:
                holder["transform"] = kept
            else:
                holder.pop("transform", None)

        _clean(spec)
        for item in spec.get("layer") or []:
            if isinstance(item, dict):
                _clean(item)

    @staticmethod
    def _apply_x_domain_window(spec: dict[str, Any], field: str, start: Any, end: Any) -> int:
        """Apply x-axis domain restriction after select_data_range.

        For quantitative/temporal: set scale.domain = [start, end] (range).
        Also applies to other temporal x channels (e.g. recession bands) so the
        visible range is consistent across all layers.
        """
        updated = 0
        channels = Node3Executor._iter_encoding_channels(spec)
        for _, channel, enc in channels:
            if channel not in ("x", "x2"):
                continue
            enc_field = str(enc.get("field", ""))
            enc_type = str(enc.get("type", "")).lower()
            # Apply domain to matching field AND to other temporal x channels
            if enc_field != field and enc_type != "temporal":
                continue
            enc_type = str(enc.get("type", "")).lower()
            if enc_type == "ordinal":
                # Ordinal: trim explicit axis.values to only those within the selected range
                axis = enc.get("axis")
                if isinstance(axis, dict) and isinstance(axis.get("values"), list):
                    try:
                        axis["values"] = [
                            v for v in axis["values"]
                            if float(start) <= float(v) <= float(end)
                        ]
                    except (TypeError, ValueError):
                        pass  # keep original if comparison fails
                # Also remove axis.labelExpr if it references out-of-range values,
                # to avoid blank labels for trimmed axis ticks
                updated += 1
            else:
                # Quantitative / temporal: range domain works correctly
                scale = enc.get("scale")
                if not isinstance(scale, dict):
                    scale = {}
                    enc["scale"] = scale
                scale["domain"] = [start, end]
                # Also trim explicit axis tick values to the new domain
                axis = enc.get("axis")
                if isinstance(axis, dict) and isinstance(axis.get("values"), list):
                    try:
                        axis["values"] = [
                            v for v in axis["values"]
                            if str(start) <= str(v) <= str(end)
                        ]
                    except (TypeError, ValueError):
                        pass
                updated += 1
        return updated

    @staticmethod
    def _widen_bars_for_narrow_range(spec: dict[str, Any], field: str, start: Any, end: Any) -> None:
        """When select_data_range reduces data points, widen bar marks for readability."""
        all_values = Node3Executor._collect_field_values(spec, field)
        if len(all_values) < 5:
            return
        # Estimate how many data points remain in range
        remaining = sum(1 for v in all_values if v >= start and v <= end) if isinstance(start, (int, float)) and isinstance(end, (int, float)) else len(all_values) // 2
        if remaining >= len(all_values) * 0.6:
            return
        # Set wider band for bar marks
        mark = spec.get("mark")
        if isinstance(mark, dict) and mark.get("type") == "bar":
            mark["width"] = {"band": 0.85}
        elif isinstance(mark, str) and mark == "bar":
            spec["mark"] = {"type": "bar", "width": {"band": 0.85}}
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                m = item.get("mark")
                if isinstance(m, dict) and m.get("type") == "bar":
                    m["width"] = {"band": 0.85}
                elif isinstance(m, str) and m == "bar":
                    item["mark"] = {"type": "bar", "width": {"band": 0.85}}

    def _infer_default_range_window(self, spec: dict[str, Any], field: str) -> tuple[Any, Any] | None:
        """Role-aware data range selection.

        Adverser: for long temporal datasets, select the most recent dramatic
        window (roughly last 15-20 years). For shorter datasets, use a
        counter-trend window if available.
        Amplifier/other: pick the segment that best supports the existing narrative.
        """
        values = Node3Executor._collect_field_values(spec, field)
        if len(values) < 3:
            return None
        role = self._current_role or ""

        evidence = self._extract_chart_evidence(spec)
        overall_trend = evidence.get("trend", "")

        if role == "Adverser":
            # For long temporal series, prefer a recent dramatic window
            is_temporal = any(
                isinstance(v, str) and len(v) >= 7 for v in values[:5]
            )
            if is_temporal and len(values) > 100:
                # Find values starting from ~last 15 years of data
                recent_cutoff_idx = max(0, len(values) - min(180, len(values) * 3 // 10))
                return values[recent_cutoff_idx], values[-1]

            dw = evidence.get("decline_window")
            gw = evidence.get("growth_window")
            if overall_trend == "rising" and dw:
                start_x = dw["start"]
                end_x = dw["end"]
                if start_x in values and end_x in values:
                    si = values.index(start_x)
                    ei = values.index(end_x)
                    if ei - si >= 4:
                        return start_x, end_x
            elif overall_trend == "falling" and gw:
                start_x = gw["start"]
                end_x = gw["end"]
                if start_x in values and end_x in values:
                    si = values.index(start_x)
                    ei = values.index(end_x)
                    if ei - si >= 4:
                        return start_x, end_x
            # Fallback: take the last 40% of rows
            lookback = max(6, len(values) * 2 // 5)
            start_idx = max(0, len(values) - lookback)
            return values[start_idx], values[-1]

        # For non-Adverser roles, keep a broad window
        start_idx = max(0, int(len(values) * 0.2))
        return values[start_idx], values[-1]

    @staticmethod
    def _collect_field_values(spec: dict[str, Any], field: str) -> list[Any]:
        collected: list[Any] = []
        data = spec.get("data")
        if isinstance(data, dict) and isinstance(data.get("values"), list):
            for row in data["values"]:
                if isinstance(row, dict) and field in row:
                    collected.append(row[field])
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("data")
                if isinstance(item_data, dict) and isinstance(item_data.get("values"), list):
                    for row in item_data["values"]:
                        if isinstance(row, dict) and field in row:
                            collected.append(row[field])
        return collected

    @staticmethod
    def _js_literal(value: Any) -> str:
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _trim_data_values_to_range(spec: dict[str, Any], field: str, start: Any, end: Any) -> None:
        """Trim data.values to the selected range so downstream ops
        (e.g. add_annotation) see positions relative to the visible subset.
        Handles both top-level data and per-layer data in layered specs."""
        def _in_range(v: Any) -> bool:
            try:
                return float(v) >= float(start) and float(v) <= float(end)
            except (TypeError, ValueError):
                return str(start) <= str(v) <= str(end)

        def _has_field(data_obj: dict[str, Any]) -> bool:
            vals = data_obj.get("values")
            if not isinstance(vals, list) or not vals:
                return False
            return any(isinstance(r, dict) and field in r for r in vals[:5])

        def _trim_values(data_obj: dict[str, Any]) -> None:
            if isinstance(data_obj, dict) and isinstance(data_obj.get("values"), list):
                if not _has_field(data_obj):
                    return
                filtered = [
                    row for row in data_obj["values"]
                    if isinstance(row, dict) and _in_range(row.get(field))
                ]
                if filtered:
                    data_obj["values"] = filtered

        data_obj = spec.get("data")
        if isinstance(data_obj, dict):
            _trim_values(data_obj)

        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("data")
                if isinstance(item_data, dict):
                    _trim_values(item_data)
                    # Also trim layers with temporal x using a different field name
                    enc = item.get("encoding")
                    if isinstance(enc, dict):
                        x_enc = enc.get("x")
                        if (isinstance(x_enc, dict)
                            and str(x_enc.get("type", "")).lower() == "temporal"
                            and x_enc.get("field") != field
                            and isinstance(item_data, dict)
                            and isinstance(item_data.get("values"), list)):
                            alt_field = x_enc.get("field")
                            if isinstance(alt_field, str):
                                item_data["values"] = [
                                    row for row in item_data["values"]
                                    if isinstance(row, dict) and _in_range(row.get(alt_field))
                                ]

    @staticmethod
    def _prune_sparse_decoration_layers(spec: dict[str, Any]) -> None:
        """Remove decoration layers (e.g. recession bands) that have been
        reduced to 0-1 data points after data range filtering, as they
        can interfere with rendering of the main data layers."""
        layer = spec.get("layer")
        if not isinstance(layer, list):
            return
        pruned: list[dict[str, Any]] = []
        for item in layer:
            if not isinstance(item, dict):
                pruned.append(item)
                continue
            mark = item.get("mark")
            mark_type = ""
            if isinstance(mark, dict):
                mark_type = str(mark.get("type", "")).lower()
            elif isinstance(mark, str):
                mark_type = mark.lower()
            # Only prune non-essential decoration marks
            if mark_type not in ("rect", "rule"):
                pruned.append(item)
                continue
            data = item.get("data")
            if isinstance(data, dict) and isinstance(data.get("values"), list):
                if len(data["values"]) <= 1:
                    continue  # prune sparse decoration layer
            pruned.append(item)
        spec["layer"] = pruned

    def _add_data_variables(self, spec: dict[str, Any]) -> tuple[bool, str, str]:
        """Add computed reference layers to help contextualize the data.

        Extender's core: introduce reference points (mean, thresholds, policy
        targets) so viewers can compare the primary data to broader context.
        Implemented as Vega-Lite rule/text layers rather than external data.
        """
        data_obj = spec.get("data")
        if not isinstance(data_obj, dict):
            return False, "no_data", "skipped"
        values = data_obj.get("values")
        if not isinstance(values, list) or len(values) < 3:
            return False, "insufficient_data", "skipped"

        enc = spec.get("encoding") or {}
        y_ch = enc.get("y") or {}
        x_ch = enc.get("x") or {}
        y_field = y_ch.get("field", "")
        x_field = x_ch.get("field", "")
        if not y_field:
            for layer in (spec.get("layer") or []):
                if isinstance(layer, dict):
                    le = (layer.get("encoding") or {})
                    yc = le.get("y") or {}
                    if yc.get("field"):
                        y_field = yc["field"]
                        x_field = x_field or (le.get("x") or {}).get("field", "")
                        break
        if not y_field:
            return False, "no_y_field", "skipped"

        y_values = [
            row[y_field] for row in values
            if isinstance(row, dict) and isinstance(row.get(y_field), (int, float))
        ]
        if len(y_values) < 3:
            return False, "insufficient_y", "skipped"

        mean_val = sum(y_values) / len(y_values)
        y_label = Node3Executor._humanize_field_name(y_field)
        institution = self._current_institution.lower()
        role = self._current_role

        # Platform-differentiated reference layer
        ref_label = f"Mean: {mean_val:,.0f}"
        ref_color = "#666666"
        if "data" in institution or "statistic" in institution:
            ref_label = f"Period mean: {mean_val:,.1f}"
            ref_color = "#2166AC"
        elif "authority" in institution or "gov" in institution or "research" in institution:
            ref_label = f"Baseline: {mean_val:,.0f}"
            ref_color = "#4D4D4D"
        elif "social" in institution or "community" in institution or "ugc" in institution:
            ref_label = f"Average: {mean_val:,.0f}"
            ref_color = "#D6604D"
        elif "news" in institution or "media" in institution:
            ref_label = f"Avg {y_label}: {mean_val:,.0f}"
            ref_color = "#878787"

        layers = spec.get("layer")
        if not isinstance(layers, list):
            base_layer = {k: v for k, v in spec.items() if k not in ("layer", "width", "height", "title", "description", "data", "usermeta", "$schema", "config", "autosize", "padding", "background")}
            spec["layer"] = [base_layer]
            for k in list(base_layer.keys()):
                if k in spec and k not in ("layer",):
                    del spec[k]
            layers = spec["layer"]

        rule_layer = {
            "mark": {"type": "rule", "strokeDash": [6, 4], "strokeWidth": 1.5},
            "encoding": {
                "y": {"datum": mean_val},
                "color": {"value": ref_color},
            },
        }
        label_layer = {
            "mark": {
                "type": "text",
                "align": "left",
                "dx": 5,
                "dy": -8,
                "fontSize": 11,
                "fontWeight": "bold",
                "color": ref_color,
            },
            "encoding": {
                "y": {"datum": mean_val},
                "text": {"value": ref_label},
            },
        }
        layers.append(rule_layer)
        layers.append(label_layer)

        before = "no_reference"
        after = f"added_mean_reference={mean_val:.1f}"
        return True, before, after

    @staticmethod
    def _select_data_variables(spec: dict[str, Any]) -> tuple[bool, str, str]:
        channels = Node3Executor._iter_encoding_channels(spec)
        optional_channels = {"color", "size", "shape", "opacity", "detail"}
        for _, channel, _ in channels:
            if channel in optional_channels:
                before = channel
                Node3Executor._drop_encoding_channel(spec, channel)
                return True, before, "removed"
        return False, "no optional channel", "unchanged"

    @staticmethod
    def _change_data_granularity(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        intent_l = intent.lower()
        time_unit = "yearmonth"
        if any(token in intent_l for token in ("day", "daily", "日")):
            time_unit = "yearmonthdate"
        elif any(token in intent_l for token in ("month", "monthly", "月")):
            time_unit = "yearmonth"
        elif any(token in intent_l for token in ("quarter", "季度")):
            time_unit = "yearquarter"
        elif any(token in intent_l for token in ("year", "yearly", "年")):
            time_unit = "year"
        channels = Node3Executor._iter_encoding_channels(spec)
        for _, channel, enc in channels:
            if channel != "x":
                continue
            if str(enc.get("type", "")).lower() != "temporal":
                continue
            before = str(enc.get("timeUnit"))
            enc["timeUnit"] = time_unit
            return True, before, time_unit
        return False, "temporal_x_not_found", "unchanged"

    @staticmethod
    def _bump_line_stroke_for_readability(mark: Any) -> None:
        """Vega-Lite default line stroke is thin; thicker lines read better in thumbnails."""
        if not isinstance(mark, dict):
            return
        if str(mark.get("type", "")).lower() != "line":
            return
        mark.setdefault("strokeWidth", 5)

    @staticmethod
    def _adjust_encoding_for_bar_to_line_or_area(
        item: dict[str, Any],
        mark_type: str,
        was_bar: bool,
    ) -> None:
        """Stacked bars sum series visually; plain line marks plot raw y per series.

        Without stacking, multi-series lines sit in the lower/mid band (max single
        series << stacked total), which looks like wrong data. Mirror bar semantics
        via y.stack='zero' and keep `order` when the bar layer was stacked.
        """
        if mark_type not in ("line", "area"):
            return
        enc = item.get("encoding", {})
        if not isinstance(enc, dict):
            return
        y_enc = enc.get("y")
        color_enc = enc.get("color")
        multi_series = isinstance(color_enc, dict) and bool(color_enc.get("field"))
        tr = item.get("transform")
        has_fold = isinstance(tr, list) and any(isinstance(t, dict) and "fold" in t for t in tr)
        had_order = "order" in enc
        should_stack = (
            was_bar
            and isinstance(y_enc, dict)
            and y_enc.get("type") == "quantitative"
            and multi_series
            and (had_order or has_fold)
        )
        if should_stack:
            y_enc["stack"] = "zero"
            lm = item.get("mark")
            if mark_type == "line" and isinstance(lm, dict):
                lm.setdefault("point", True)
        else:
            if isinstance(y_enc, dict):
                y_enc.pop("stack", None)
            enc.pop("order", None)

    @staticmethod
    def _change_chart_type(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        intent_l = intent.lower()
        mark_type = "bar"
        if "line" in intent_l:
            mark_type = "line"
        elif "area" in intent_l:
            mark_type = "area"
        elif "point" in intent_l or "dot" in intent_l:
            mark_type = "point"
        elif "bar" in intent_l:
            mark_type = "bar"

        _BAR_ONLY_KEYS = {"width", "cornerRadius", "cornerRadiusTopLeft",
                          "cornerRadiusTopRight", "cornerRadiusBottomLeft",
                          "cornerRadiusBottomRight", "binSpacing", "orient"}
        _REFERENCE_MARKS = {"text", "tick", "rule"}

        mark = spec.get("mark")
        if isinstance(mark, dict):
            before = str(mark.get("type"))
            was_bar = before.lower() == "bar"
            mark["type"] = mark_type
            if mark_type in ("line", "area"):
                for k in _BAR_ONLY_KEYS:
                    mark.pop(k, None)
            fake_item = {"mark": mark, "encoding": spec.get("encoding"), "transform": spec.get("transform")}
            if isinstance(fake_item["encoding"], dict):
                Node3Executor._adjust_encoding_for_bar_to_line_or_area(fake_item, mark_type, was_bar)
            if mark_type == "line":
                Node3Executor._bump_line_stroke_for_readability(mark)
            return True, before, mark_type
        if isinstance(mark, str):
            before = mark
            was_bar = mark.lower() == "bar"
            spec["mark"] = {"type": mark_type}
            if mark_type in ("line", "area") and was_bar:
                fake_item = {"mark": spec["mark"], "encoding": spec.get("encoding"), "transform": spec.get("transform")}
                if isinstance(fake_item["encoding"], dict):
                    Node3Executor._adjust_encoding_for_bar_to_line_or_area(fake_item, mark_type, was_bar)
            if mark_type == "line":
                Node3Executor._bump_line_stroke_for_readability(spec["mark"])
            return True, before, mark_type

        layer = spec.get("layer")
        if isinstance(layer, list):
            changed = 0
            before_types: list[str] = []
            for item in layer:
                if not isinstance(item, dict):
                    continue
                layer_mark = item.get("mark")
                mark_str = ""
                if isinstance(layer_mark, dict):
                    mark_str = str(layer_mark.get("type", "")).lower()
                elif isinstance(layer_mark, str):
                    mark_str = layer_mark.lower()
                if mark_str in _REFERENCE_MARKS:
                    continue
                was_bar = mark_str == "bar"
                item_changed = False
                if isinstance(layer_mark, dict):
                    before_types.append(mark_str)
                    layer_mark["type"] = mark_type
                    if mark_type in ("line", "area"):
                        for k in _BAR_ONLY_KEYS:
                            layer_mark.pop(k, None)
                    item_changed = True
                    changed += 1
                elif isinstance(layer_mark, str):
                    before_types.append(mark_str)
                    item["mark"] = {"type": mark_type}
                    item_changed = True
                    changed += 1
                if item_changed:
                    Node3Executor._adjust_encoding_for_bar_to_line_or_area(item, mark_type, was_bar)
                    if mark_type == "line":
                        Node3Executor._bump_line_stroke_for_readability(item.get("mark"))
            if changed > 0:
                return True, f"changed={changed} from={before_types[:2]}", mark_type
        return False, "mark_not_found", "unchanged"

    @staticmethod
    def _add_background(spec: dict[str, Any]) -> tuple[bool, str, str]:
        view = spec.get("view")
        if not isinstance(view, dict):
            view = {}
            spec["view"] = view
        before = str(view.get("fill"))
        view["fill"] = "#F7F7FA"
        spec["background"] = "#FFFFFF"
        return True, before, str(view.get("fill"))

    @staticmethod
    def _change_aspect_ratio(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        intent_l = intent.lower()
        width, height = 640, 360
        if any(token in intent_l for token in ("tall", "portrait", "竖")):
            width, height = 420, 640
        elif any(token in intent_l for token in ("square", "正方")):
            width, height = 520, 520
        before = f"{spec.get('width')}x{spec.get('height')}"
        spec["width"] = width
        spec["height"] = height
        return True, before, f"{width}x{height}"

    def _change_annotation(self, spec: dict[str, Any], intent: str, params: dict[str, Any]) -> tuple[bool, str, str]:
        raw_text = Node3Executor._clean_annotation_text(intent.strip())
        if not raw_text or Node3Executor._is_generic_intent(raw_text):
            raw_text = self._generate_annotation(spec, intent)
        new_text = Node3Executor._enforce_text_length(raw_text, is_title=False)
        default_font = 14 if self._current_role in ("Extender", "Analyst") else 20
        min_font_size = Node3Executor._normalize_font_size(params.get("min_font_size"), default_font)
        if params.get("prune_offtopic_annotations"):
            Node3Executor._prune_offtopic_annotations(spec, params.get("narrative_keywords"))
        layer = spec.get("layer")
        if isinstance(layer, list):
            changed = 0
            before_values: list[str] = []
            for item in layer:
                if not isinstance(item, dict):
                    continue
                mark = item.get("mark")
                if not isinstance(mark, dict):
                    continue
                description = str(item.get("description", "")).lower()
                if mark.get("type") == "text" and isinstance(mark.get("text"), str) and (
                    "annotation" in description or description.startswith("node3 added")
                ):
                    before_values.append(str(mark.get("text")))
                    mark["text"] = Node3Executor._fit_annotation_mark_text_to_canvas(
                        text=new_text,
                        mark=mark,
                        item=item,
                        spec=spec,
                        min_font_size=min_font_size,
                    )
                    Node3Executor._apply_annotation_mark_style(mark, min_font_size)
                    Node3Executor._apply_emphasis_style(mark, params.get("emphasis_style"))
                    Node3Executor._normalize_annotation_encoding_position(item, spec)
                    changed += 1
            if changed > 0:
                if self._current_role in ("Extender", "Analyst"):
                    anchor = self._pick_annotation_anchor(spec, intent)
                    if anchor:
                        self._highlight_annotated_bar(spec, anchor)
                return True, f"changed={changed} from={before_values[:2]}", new_text
        desc = spec.get("description")
        if isinstance(desc, str) and desc.strip():
            before = desc
            spec["description"] = new_text
            return True, before, new_text
        return False, "annotation_not_found", "unchanged"

    @staticmethod
    def _simplify_axis(spec: dict[str, Any], params: dict[str, Any]) -> tuple[bool, str, str]:
        channels = Node3Executor._iter_encoding_channels(spec)
        touched = 0
        changed = 0
        target_axis = str(params.get("target_axis", "x")).lower()
        # Default to interval_labels: show every Nth label instead of hiding all
        mode = str(params.get("mode", "interval_labels")).lower()
        label_interval = params.get("label_interval", 5)
        if not isinstance(label_interval, int) or label_interval <= 1:
            label_interval = 5
        allowed_targets = {"x", "y", "both"}
        if target_axis not in allowed_targets:
            target_axis = "x"
        for _, channel, enc in channels:
            if target_axis == "x" and channel != "x":
                continue
            if target_axis == "y" and channel != "y":
                continue
            if target_axis == "both" and channel not in {"x", "y"}:
                continue
            touched += 1
            axis = enc.get("axis")
            axis_dict = axis if isinstance(axis, dict) else {}
            before_snapshot = (
                axis_dict.get("labels"),
                axis_dict.get("ticks"),
                axis_dict.get("grid"),
                axis_dict.get("title"),
            )
            # Always use interval_labels: show sparse readable labels
            axis_dict["labels"] = True
            axis_dict["ticks"] = True
            axis_dict["grid"] = False
            axis_dict["title"] = None
            axis_dict["labelOverlap"] = "greedy"
            enc_type = str(enc.get("type", "")).lower()
            if enc_type == "quantitative":
                axis_dict["labelExpr"] = (
                    f"datum.value % {label_interval} == 0 ? datum.label : ''"
                )
            elif enc_type == "temporal":
                # Taxonomy: 每5年或每10年, e.g. 2000,2005,2010,2015,2020
                step = label_interval
                axis_dict["labelExpr"] = (
                    f"datum.value != null && new Date(datum.value).getFullYear() % {step} === 0 "
                    f"? datum.label : ''"
                )
            elif enc_type in ("ordinal", "nominal", ""):
                axis_dict["tickCount"] = min(label_interval, 12)
                axis_dict.pop("labelExpr", None)
            enc["axis"] = axis_dict
            after_snapshot = (
                axis_dict.get("labels"),
                axis_dict.get("ticks"),
                axis_dict.get("grid"),
                axis_dict.get("title"),
            )
            if before_snapshot != after_snapshot:
                changed += 1
        if touched == 0:
            return False, "no axis found", "unchanged"
        return True, f"axis_count={touched}", f"{target_axis} axis simplified"

    @staticmethod
    def _change_axis_scale(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        """Adjust y-axis domain to zoom in on data range, emphasizing differences.

        E.g. if data clusters in 50-100, set domain=[45,105] instead of [0,100].
        This matches the taxonomy: "缩小纵轴尺度以拉高" (narrow y-scale to magnify).
        """
        candidates = Node3Executor._collect_xy_data_candidates(spec)
        if not candidates:
            return False, "no data candidates found", "unchanged"

        c = candidates[0]
        y_field = c["y_field"]
        numeric_rows = [
            r for r in c["values"]
            if isinstance(r, dict) and isinstance(r.get(y_field), (int, float))
        ]
        if len(numeric_rows) < 3:
            return False, "insufficient data rows", "unchanged"

        y_vals = sorted(float(r[y_field]) for r in numeric_rows)
        actual_min = y_vals[0]
        actual_max = y_vals[-1]
        p10 = y_vals[max(0, len(y_vals) // 10)]
        p90 = y_vals[min(len(y_vals) - 1, len(y_vals) * 9 // 10)]
        data_range = p90 - p10
        if data_range <= 0:
            return False, "data range too small", "unchanged"

        margin = data_range * 0.1
        new_min = round(p10 - margin, 2)
        new_max = round(p90 + margin, 2)
        # Safety: domain must contain ALL actual data points to prevent invisible bars
        new_min = min(new_min, actual_min)
        new_max = max(new_max, actual_max * 1.05)
        # Don't set a domain that is essentially the same as [0, max] — no zoom benefit
        if actual_min >= 0 and new_min <= 0 and (new_max - new_min) > (actual_max * 0.85):
            return False, "zoom too shallow to be meaningful", "unchanged"
        before_domain = "auto"

        channels = Node3Executor._iter_encoding_channels(spec)
        for _, channel, enc in channels:
            if channel != "y":
                continue
            if str(enc.get("type", "")).lower() not in {"quantitative"}:
                continue
            scale = enc.get("scale")
            if not isinstance(scale, dict):
                scale = {}
                enc["scale"] = scale
            before_domain = str(scale.get("domain", "auto"))
            scale["domain"] = [new_min, new_max]
            return True, before_domain, f"[{new_min}, {new_max}]"

        return False, "no quantitative y-axis found", "unchanged"

    @staticmethod
    def _change_legend(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        legend_title = intent.strip() or "Reframed legend"
        channels = Node3Executor._iter_encoding_channels(spec)
        # Prefer channels with existing legend, then non-positional channels.
        channels.sort(
            key=lambda item: (
                0
                if isinstance(item[2].get("legend"), dict)
                else (1 if item[1] not in {"x", "x2", "y", "y2"} else 2)
            )
        )
        for _, channel, enc in channels:
            field = enc.get("field")
            if not isinstance(field, str):
                continue
            legend = enc.get("legend")
            if legend is False:
                continue
            if channel in {"x", "x2", "y", "y2"} and legend is None:
                continue
            legend_dict = legend if isinstance(legend, dict) else {}
            before = str(legend_dict.get("title"))
            legend_dict["title"] = legend_title
            enc["legend"] = legend_dict
            return True, before, legend_title
        return False, "no legend target found", "unchanged"

    @staticmethod
    def _add_legend(spec: dict[str, Any], intent: str) -> tuple[bool, str, str]:
        if Node3Executor._spec_has_legend(spec):
            return False, "legend already exists", "unchanged"
        intent_l = intent.lower()
        emphasize_tokens = ("emphas", "highlight", "focus", "salience", "突出", "强调", "重点")
        if not any(token in intent_l for token in emphasize_tokens):
            return False, "no emphasis intent", "unchanged"
        legend_title = intent.strip() or "Added legend"
        positional_channels = {"x", "y", "x2", "y2"}
        preferred_channels = {"color", "shape", "size", "opacity"}
        channels = Node3Executor._iter_encoding_channels(spec)
        ordered = sorted(channels, key=lambda item: 0 if item[1] in preferred_channels else 1)
        for _, ch_name, enc in ordered:
            if ch_name in positional_channels:  # legend on x/y causes validation failure
                continue
            field = enc.get("field")
            if not isinstance(field, str):
                continue
            legend = enc.get("legend")
            if isinstance(legend, dict):
                continue
            if legend is False or legend is None:
                enc["legend"] = {"title": legend_title}
                return True, str(legend), legend_title
        return False, "no encoding channel supports legend", "unchanged"

    @staticmethod
    def _pick_x_field(spec: dict[str, Any]) -> str | None:
        # Prefer top-level encoding.x.field.
        encoding = spec.get("encoding")
        if isinstance(encoding, dict):
            x = encoding.get("x")
            if isinstance(x, dict) and isinstance(x.get("field"), str):
                return x["field"]
        # Fallback: first layered encoding.x.field.
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if isinstance(enc, dict):
                    x = enc.get("x")
                    if isinstance(x, dict) and isinstance(x.get("field"), str):
                        return x["field"]
        return None

    @staticmethod
    def _next_annotation_position(layer: list[Any], spec: dict[str, Any]) -> tuple[int, int]:
        width, height = Node3Executor._annotation_canvas_bounds(spec)
        y_values: list[int] = []
        text_layer_count = 0
        for item in layer:
            if not isinstance(item, dict):
                continue
            mark = item.get("mark")
            if not isinstance(mark, dict) or mark.get("type") != "text":
                continue
            text_layer_count += 1
            enc = item.get("encoding")
            if not isinstance(enc, dict):
                continue
            y = enc.get("y")
            if isinstance(y, dict) and isinstance(y.get("value"), (int, float)):
                y_values.append(int(y["value"]))
        # Keep text notes within drawable area instead of drifting outside after many annotations.
        max_y = max(24, height - 24)
        step = 18
        next_y = (max(y_values) + step) if y_values else 24
        if next_y > max_y:
            slots = max(1, int((max_y - 24) / step) + 1)
            next_y = 24 + (text_layer_count % slots) * step
        left_x = 12
        right_x = max(12, width - min(220, max(120, int(width * 0.35))))
        # Alternate horizontal position to reduce overlap among nearby notes.
        next_x = left_x if text_layer_count % 2 == 0 else right_x
        next_x = Node3Executor._clamp_int(next_x, 8, max(8, width - 24))
        next_y = Node3Executor._clamp_int(next_y, 18, max(18, height - 12))
        return next_x, next_y

    def _pick_annotation_anchor(self, spec: dict[str, Any], intent: str) -> dict[str, Any] | None:
        candidates = Node3Executor._collect_xy_data_candidates(spec)
        if not candidates:
            return None
        intent_l = intent.lower()
        role = self._current_role or ""
        for candidate in candidates:
            x_field = candidate["x_field"]
            y_field = candidate["y_field"]
            values = candidate["values"]
            if not all(isinstance(row, dict) and x_field in row and y_field in row for row in values):
                continue
            numeric_values = [row for row in values if isinstance(row.get(y_field), (int, float))]
            if not numeric_values:
                continue
            if any(token in intent_l for token in ("max", "peak", "highest", "high", "最高", "峰值")):
                target = max(numeric_values, key=lambda row: float(row[y_field]))
            elif any(token in intent_l for token in ("min", "lowest", "low", "最低", "谷底")):
                target = min(numeric_values, key=lambda row: float(row[y_field]))
            elif any(token in intent_l for token in ("latest", "last", "recent", "最新", "最后")):
                target = numeric_values[-1]
            elif any(token in intent_l for token in ("first", "start", "earliest", "最初", "起点")):
                target = numeric_values[0]
            elif role == "Adverser":
                # Adverser: anchor at the PEAK of the decline window (start of downtrend)
                # so the trendline drawn from anchor → trend_end goes DOWNWARD
                evidence = self._extract_chart_evidence(spec)
                dw = evidence.get("decline_window")
                if dw:
                    # Use start of decline window (high point) as anchor
                    start_x = str(dw.get("start", ""))
                    match = next((r for r in numeric_values if str(r.get(x_field, "")) == start_x), None)
                    target = match if match else max(numeric_values, key=lambda row: float(row[y_field]))
                else:
                    target = max(numeric_values, key=lambda row: float(row[y_field]))
            elif role == "Amplifier":
                # Amplifier: anchor at the peak to emphasize the trend
                target = max(numeric_values, key=lambda row: float(row[y_field]))
            elif role in ("Analyst", "Extender"):
                # Extender/Analyst: anchor at the most recent high point to connect
                # data trend to broader context (Paris Agreement era, recent years)
                recent_start = max(0, int(len(numeric_values) * 0.7))
                recent_pool = numeric_values[recent_start:] or numeric_values
                target = max(recent_pool, key=lambda row: float(row[y_field]))
            else:
                target = max(numeric_values, key=lambda row: float(row[y_field]))
            target_index = next((idx for idx, row in enumerate(numeric_values) if row is target), 0)
            x_ratio = (target_index / (len(numeric_values) - 1)) if len(numeric_values) > 1 else 0.5
            first_row = numeric_values[0]
            last_row = numeric_values[-1]

            # For stacked/fold-transform charts, annotation y-position should be at the
            # TOP of the full stack, not just one sub-field's value.
            # Compute the stacked height at the target row by summing all fold-transform fields.
            raw_y_value = float(target[y_field])
            stacked_y_value = Node3Executor._compute_stacked_y(spec, target[x_field], x_field, raw_y_value)

            return {
                "x_field": x_field,
                "y_field": y_field,
                "x_type": candidate["x_type"],
                "y_type": candidate["y_type"],
                "x_value": target[x_field],
                "y_value": stacked_y_value,
                "y_values": [float(row[y_field]) for row in numeric_values],
                "x_ratio": x_ratio,
                "trend_end": {
                    "x_value": last_row[x_field],
                    "y_value": float(last_row[y_field]),
                    "x_start": first_row[x_field],
                    "y_start": float(first_row[y_field]),
                },
            }
        return None

    @staticmethod
    def _compute_stacked_y(spec: dict[str, Any], target_x: Any, x_field: str, fallback_y: float) -> float:
        """For fold-transform stacked charts, compute the total stacked height at target_x.
        This ensures annotations are positioned at the visual top of stacked bars, not
        at a single sub-field's value (which would be inside the stack).
        Returns fallback_y if no fold transform is found.
        """
        top_values = spec.get("data", {}).get("values") if isinstance(spec.get("data"), dict) else None
        if not isinstance(top_values, list):
            return fallback_y
        # Look for fold transform in any layer
        folded_fields: list[str] = []
        for layer in (spec.get("layer") or []):
            if not isinstance(layer, dict):
                continue
            for transform in (layer.get("transform") or []):
                if isinstance(transform, dict) and isinstance(transform.get("fold"), list):
                    folded_fields = [f for f in transform["fold"] if isinstance(f, str)]
                    break
            if folded_fields:
                break
        if not folded_fields:
            return fallback_y
        # Find the raw data row matching target_x
        target_row = next(
            (r for r in top_values if isinstance(r, dict) and str(r.get(x_field)) == str(target_x)),
            None,
        )
        if target_row is None:
            return fallback_y
        # Sum all folded field values at this row
        total = sum(float(target_row.get(f, 0)) for f in folded_fields if isinstance(target_row.get(f), (int, float)))
        return total if total > fallback_y else fallback_y

    @staticmethod
    def _collect_xy_data_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        top_encoding = spec.get("encoding")
        top_values = (
            spec.get("data", {}).get("values")
            if isinstance(spec.get("data"), dict) and isinstance(spec.get("data", {}).get("values"), list)
            else None
        )
        # Extract parent-level x/y for "shared x" pattern (x in parent, y in layer)
        top_xf: str | None = None
        top_yf: str | None = None
        top_x_type = "quantitative"
        top_y_type = "quantitative"
        if isinstance(top_encoding, dict):
            tx = top_encoding.get("x")
            ty = top_encoding.get("y")
            if isinstance(tx, dict):
                top_xf = tx.get("field") if isinstance(tx.get("field"), str) else None
                top_x_type = str(tx.get("type", "quantitative"))
            if isinstance(ty, dict):
                top_yf = ty.get("field") if isinstance(ty.get("field"), str) else None
                top_y_type = str(ty.get("type", "quantitative"))
        if top_xf and top_yf and isinstance(top_values, list):
            candidates.append(
                {
                    "x_field": top_xf,
                    "y_field": top_yf,
                    "x_type": top_x_type,
                    "y_type": top_y_type,
                    "values": top_values,
                }
            )
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                encoding = item.get("encoding")
                data_values = (
                    item.get("data", {}).get("values")
                    if isinstance(item.get("data"), dict) and isinstance(item.get("data", {}).get("values"), list)
                    else top_values
                )
                if not isinstance(encoding, dict) or not isinstance(data_values, list):
                    continue
                x = encoding.get("x")
                y = encoding.get("y")
                # Support "shared x" pattern: inherit from parent when not in layer
                x_field = x.get("field") if isinstance(x, dict) else None
                y_field = y.get("field") if isinstance(y, dict) else None
                if not isinstance(x_field, str):
                    x_field = top_xf
                if not isinstance(y_field, str):
                    y_field = top_yf
                x_type = str(x.get("type", top_x_type)) if isinstance(x, dict) else top_x_type
                y_type = str(y.get("type", top_y_type)) if isinstance(y, dict) else top_y_type
                if isinstance(x_field, str) and isinstance(y_field, str):
                    candidates.append(
                        {
                            "x_field": x_field,
                            "y_field": y_field,
                            "x_type": x_type,
                            "y_type": y_type,
                            "values": data_values,
                            }
                        )

        # Augment: scan all numeric fields in top-level data with the known x field
        # Handles fold-transform charts where encoded y field doesn't exist in data
        if top_xf and isinstance(top_values, list):
            already = {c["y_field"] for c in candidates}
            numeric_fields: set[str] = set()
            for row in top_values[:20]:
                for key, val in row.items():
                    if key != top_xf and isinstance(val, (int, float)):
                        numeric_fields.add(key)
            for yf in sorted(numeric_fields):
                if yf not in already:
                    candidates.append(
                        {
                            "x_field": top_xf,
                            "y_field": yf,
                            "x_type": top_x_type,
                            "y_type": "quantitative",
                            "values": top_values,
                        }
                    )
        return candidates

    @staticmethod
    def _build_data_annotation_layers(
        anchor: dict[str, Any],
        text: str,
        existing_layers: list[Any],
        include_trendline: bool = False,
        min_font_size: int = 20,
        canvas_width: int = 640,
        text_color: str = "#202124",
    ) -> list[dict[str, Any]]:
        x_field = str(anchor["x_field"])
        y_field = str(anchor["y_field"])
        x_type = str(anchor.get("x_type", "quantitative"))
        y_type = str(anchor.get("y_type", "quantitative"))
        y_value = float(anchor["y_value"])
        y_values = [float(v) for v in anchor.get("y_values", []) if isinstance(v, (int, float))]
        annotation_count = sum(
            1
            for item in existing_layers
            if isinstance(item, dict)
            and isinstance(item.get("description"), str)
            and item["description"].startswith("Node3 added annotation")
        )
        if y_values:
            y_min = min(y_values)
            y_max = max(y_values)
            data_span = max(y_max - y_min, 1.0)
        else:
            data_span = 1.0
        direction = -1.0 if annotation_count % 2 == 0 else 1.0
        y_offset = direction * max(data_span * 0.08, 0.5)
        x_ratio = float(anchor.get("x_ratio", 0.5))
        text_align = "right" if x_ratio >= 0.62 else "left"
        text_dx = -10 if text_align == "right" else 10
        max_chars = Node3Executor._estimate_annotation_max_chars(
            canvas_width=canvas_width,
            x_ratio=x_ratio,
            align=text_align,
            font_size=min_font_size,
        )
        wrapped_text = Node3Executor._wrap_text(text, max_chars)
        # Vega-Lite multi-line: store as array of strings
        text_lines = wrapped_text.split("\n") if "\n" in wrapped_text else [wrapped_text]
        payload = {
            x_field: anchor["x_value"],
            y_field: y_value,
            "y_label": y_value + y_offset,
            "annotation_text": text_lines,
        }
        # Clamp y_offset so annotation text stays within data range
        if y_values:
            y_min = min(y_values)
            y_max = max(y_values)
            label_y = y_value + y_offset
            clamped_label_y = max(y_min, min(label_y, y_max))
            y_offset = clamped_label_y - y_value
        payload["y_label"] = y_value + y_offset

        # Pixel width for text — use 65% of canvas so annotation text is fully visible
        text_limit_px = max(280, int(canvas_width * 0.65))

        point_layer = {
            "description": "Node3 added annotation anchor",
            "data": {"values": [payload]},
            "mark": {"type": "point", "filled": True, "size": 65, "color": "#2C7FB8"},
            "encoding": {
                "x": {"field": x_field, "type": x_type},
                "y": {"field": y_field, "type": y_type},
            },
        }
        rule_layer = {
            "description": "Node3 added annotation leader",
            "data": {"values": [payload]},
            "mark": {"type": "rule", "color": "#5F6B7A", "strokeDash": [4, 2]},
            "encoding": {
                "x": {"field": x_field, "type": x_type},
                "y": {"field": y_field, "type": y_type},
                "y2": {"datum": y_value + y_offset},
            },
        }
        text_layer = {
            "description": "Node3 added annotation",
            "data": {"values": [payload]},
            "mark": {
                "type": "text",
                "align": text_align,
                "baseline": "middle",
                "dx": text_dx,
                "color": text_color,
                "fontSize": min_font_size,
                "lineHeight": min_font_size + 4,
                "fontWeight": 600,
                "limit": text_limit_px,
            },
            "encoding": {
                "x": {"field": x_field, "type": x_type},
                "y": {"field": "y_label", "type": y_type},
                "text": {"field": "annotation_text"},
            },
        }
        layers = [point_layer, rule_layer, text_layer]
        if include_trendline and isinstance(anchor.get("trend_end"), dict):
            trend_end = anchor["trend_end"]
            trend_payload = {
                x_field: anchor["x_value"],
                y_field: y_value,
            }
            trend_layer = {
                "description": "Node3 added trendline",
                "data": {"values": [trend_payload]},
                "mark": {"type": "rule", "color": "#D62728", "strokeWidth": 2},
                "encoding": {
                    "x": {"field": x_field, "type": x_type},
                    "y": {"field": y_field, "type": y_type},
                    "x2": {"datum": trend_end.get("x_value")},
                    "y2": {"datum": trend_end.get("y_value")},
                },
            }
            layers.insert(0, trend_layer)
        return layers

    @staticmethod
    def _iter_encoding_channels(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        channels: list[tuple[str, str, dict[str, Any]]] = []
        top_encoding = spec.get("encoding")
        if isinstance(top_encoding, dict):
            for channel, enc in top_encoding.items():
                if isinstance(enc, dict):
                    channels.append(("top", channel, enc))
        layer = spec.get("layer")
        if isinstance(layer, list):
            for idx, item in enumerate(layer):
                if not isinstance(item, dict):
                    continue
                encoding = item.get("encoding")
                if not isinstance(encoding, dict):
                    continue
                for channel, enc in encoding.items():
                    if isinstance(enc, dict):
                        channels.append((f"layer_{idx}", channel, enc))
        return channels

    @staticmethod
    def _drop_encoding_channel(spec: dict[str, Any], channel_name: str) -> None:
        encoding = spec.get("encoding")
        if isinstance(encoding, dict) and channel_name in encoding:
            encoding.pop(channel_name, None)
        layer = spec.get("layer")
        if isinstance(layer, list):
            for item in layer:
                if not isinstance(item, dict):
                    continue
                enc = item.get("encoding")
                if isinstance(enc, dict):
                    enc.pop(channel_name, None)

    @staticmethod
    def _spec_has_legend(spec: dict[str, Any]) -> bool:
        for _, _, enc in Node3Executor._iter_encoding_channels(spec):
            if isinstance(enc.get("legend"), dict):
                return True
        return False

    # ── Role × Platform palette system (taxonomy codebook aligned) ──────────
    #
    # Bridger: 配色较为温和中立 — neutral, professional
    # Amplifier: 强化配色对比，放大情绪 — high-contrast, emotional;
    #            新闻媒体用自己的配色; 社交媒体更激进
    # Adverser: 使用和上一节点相反的配色 — counter-color
    # Extender: 沿用上一节点的配色(with analytical variation) — analytical/expanded
    #
    # DESIGN: Colors within the same role must be CLEARLY DISTINGUISHABLE
    # across platforms. Use different hues, not just different shades.
    _ROLE_PLATFORM_PALETTES: dict[str, str] = {
        # ── Bridger: purple/violet institutional tones ────────────────────
        "Bridger__t1_authority": "#6A5ACD",  # slate blue-purple (institutional)
        "Bridger__t2_news":     "#7B68EE",  # medium slate blue-purple
        "Bridger__t3_social":   "#8B7FD4",  # soft violet
        "Bridger__t4_ugc":      "#9370DB",  # medium purple
        "Bridger__t5_blog":     "#7E6BBE",  # muted purple
        "Bridger__t6_data":     "#6C5CE7",  # vivid purple (data platform)
        "Bridger__default":     "#7B68EE",

        # ── Amplifier: vivid warm/orange family ──────────────────────────
        "Amplifier__t1_authority": "#E65100",  # deep orange (institutional)
        "Amplifier__t2_news":     "#F4511E",  # vivid red-orange (editorial)
        "Amplifier__t3_social":   "#FF5722",  # bright deep orange (social)
        "Amplifier__t4_ugc":      "#FF6D00",  # vivid amber-orange (UGC)
        "Amplifier__t5_blog":     "#E64A19",  # dark deep orange (personal)
        "Amplifier__t6_data":     "#F57C00",  # amber orange (data)
        "Amplifier__default":     "#FF5722",

        # ── Adverser: vivid red counter-narrative tones ──────────────────
        "Adverser__t1_authority": "#C62828",  # dark vivid red (institutional)
        "Adverser__t2_news":     "#D32F2F",  # vivid red (editorial)
        "Adverser__t3_social":   "#F44336",  # bright red (social)
        "Adverser__t4_ugc":      "#E53935",  # vivid red (forum)
        "Adverser__t5_blog":     "#EF5350",  # coral red (blog)
        "Adverser__t6_data":     "#E53935",  # vivid red (data)
        "Adverser__default":     "#E53935",

        # ── Extender: analytical thinker — teals/indigos/deep purples ─────
        "Extender__t1_authority": "#37474F",  # dark slate (institutional depth)
        "Extender__t2_news":     "#4527A0",  # deep purple (editorial analysis)
        "Extender__t3_social":   "#00695C",  # dark teal (social expansion)
        "Extender__t4_ugc":      "#1A237E",  # deep indigo (community analysis)
        "Extender__t5_blog":     "#4A148C",  # deep purple (analytical blog)
        "Extender__t6_data":     "#006064",  # dark cyan (data-driven)
        "Extender__default":     "#283593",  # indigo
        # ── Analyst: analytical — purples/teals ────────────────────────────
        "Analyst__t1_authority": "#5F9EA0",  # cadet blue (research)
        "Analyst__t2_news":     "#6A5ACD",  # slate blue (media analysis)
        "Analyst__t3_social":   "#9370DB",  # medium purple (social expansion)
        "Analyst__t4_ugc":      "#7B68EE",  # medium slate blue (community)
        "Analyst__t5_blog":     "#8A2BE2",  # blue-violet (blog analysis)
        "Analyst__t6_data":     "#5F9EA0",  # cadet blue
        "Analyst__default":     "#7B68EE",
    }

    def _pick_palette_for_role(self, spec: dict[str, Any], intent: str) -> str:
        """Role × Platform aware palette selection with depth darkening."""
        # If LLM provided an explicit hex color, respect it
        explicit_hex = re.search(r"#[0-9a-fA-F]{6}", intent)
        if explicit_hex:
            base = explicit_hex.group(0)
            return self._apply_depth_darkening(base)

        role = self._current_role or ""
        institution = self._current_institution or ""
        platform_bucket = self._infer_platform_bucket_local(institution)

        # Look up role × platform palette
        key = f"{role}__{platform_bucket}"
        color = self._ROLE_PLATFORM_PALETTES.get(key)
        if not color:
            default_key = f"{role}__default"
            color = self._ROLE_PLATFORM_PALETTES.get(default_key)
        if not color:
            color = Node3Executor._pick_palette_from_intent(intent)

        return self._apply_depth_darkening(color)

    def _apply_depth_darkening(self, hex_color: str) -> str:
        """Apply depth-progressive color shift.

        Amplifier: shift towards deeper red (G and B channels suppressed faster
        than R, pulling orange/brown tones into crimson/blood-red).
        Adverser: shift towards darker green.
        Others: uniform darkening.
        """
        depth = getattr(self, "_current_depth", 1)
        if depth <= 1:
            return hex_color
        role = getattr(self, "_current_role", "") or ""
        if role == "Amplifier":
            return Node3Executor._shift_towards_red(hex_color, depth)
        if role == "Adverser":
            return Node3Executor._shift_towards_red(hex_color, depth)
        factor = min(0.40, 0.15 * (depth - 1))
        return Node3Executor._darken_hex(hex_color, factor)

    @staticmethod
    def _shift_towards_red(hex_color: str, depth: int) -> str:
        """Amplifier: progressively deepen towards blood-red.
        D1: base color, D2: redder+darker, D3: deep crimson, D4+: near blood-red."""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            step = min(depth - 1, 4)
            # R channel: gentle darkening (keep red dominant)
            r = max(100, int(r * (1 - 0.08 * step)))
            # G and B: aggressive suppression → pulls hue towards red
            g = max(0, int(g * (1 - 0.35 * step)))
            b = max(0, int(b * (1 - 0.35 * step)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except (ValueError, IndexError):
            return f"#{hex_color}"

    @staticmethod
    def _shift_towards_green(hex_color: str, depth: int) -> str:
        """Adverser: progressively deepen towards dark forest green."""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            step = min(depth - 1, 4)
            r = max(0, int(r * (1 - 0.30 * step)))
            g = max(60, int(g * (1 - 0.10 * step)))
            b = max(0, int(b * (1 - 0.25 * step)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except (ValueError, IndexError):
            return f"#{hex_color}"

    @staticmethod
    def _darken_hex(hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor (0.0 = unchanged, 1.0 = black)."""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except (ValueError, IndexError):
            return f"#{hex_color}"

    @staticmethod
    def _infer_platform_bucket_local(institution: str) -> str:
        """Fine-grained platform classification — 6 buckets to maximize color differentiation."""
        inst = institution.lower() if institution else ""
        if any(t in inst for t in ("政府", "官方", "gov", "国际组织", "international")):
            return "t1_authority"
        if any(t in inst for t in ("科研", "research", "university", "学术", "academic")):
            return "t1_authority"
        # Social media BEFORE generic media/news
        if any(t in inst for t in ("social media", "社交媒体", "twitter", "youtube")):
            return "t3_social"
        # UGC/forums — distinct from social media
        if any(t in inst for t in ("ugc", "论坛", "在线社区", "online community", "forum", "社区")):
            return "t4_ugc"
        # Personal/institutional blogs
        if any(t in inst for t in ("个人", "personal", "博客", "blog")):
            return "t5_blog"
        # News media
        if any(t in inst for t in ("news", "新闻", "新闻媒体")):
            return "t2_news"
        # Third-party data platforms
        if any(t in inst for t in ("第三方", "数据平台", "data platform", "ycharts", "wikipedia")):
            return "t6_data"
        # "机构博客" → blog
        if "机构博客" in inst:
            return "t5_blog"
        # Catch-all: "media" alone → news
        if "media" in inst:
            return "t2_news"
        return "default"

    @staticmethod
    def _pick_palette_from_intent(intent: str) -> str:
        explicit_hex = re.search(r"#[0-9a-fA-F]{6}", intent)
        if explicit_hex:
            return explicit_hex.group(0)
        intent_l = intent.lower()
        if any(token in intent_l for token in ("cooling", "cold", "blue", "变冷", "降温")):
            return "#4C78A8"
        if any(token in intent_l for token in ("risk", "danger", "threat", "alarm", "危机", "风险", "危险")):
            return "#C23B22"
        if any(token in intent_l for token in ("forest", "amazon", "deforestation", "environment", "森林", "环保")):
            return "#2E8B57"
        if any(token in intent_l for token in ("growth", "improve", "positive", "opportun", "增长", "改善", "积极")):
            return "#2E8B57"
        if any(token in intent_l for token in ("neutral", "balance", "objective", "中性", "平衡", "客观")):
            return "#4C78A8"
        if any(token in intent_l for token in ("vivid", "contrast", "social", "neon", "鲜明", "对比")):
            return "#E53B22"
        if any(token in intent_l for token in ("purple", "analytic", "expand", "extend", "紫", "分析")):
            return "#7B68EE"
        if any(token in intent_l for token in ("amber", "gold", "counter", "反", "质疑")):
            return "#E8A735"
        return "#C23B22"

    @staticmethod
    def _build_palette_range(base_color: str, palette_style: str = "default") -> list[str]:
        """Dynamically build a 4-stop gradient range from any base color.
        Base color is first so single-category series get the intended hue."""
        lighten = Node3Executor._lighten_hex
        darken = Node3Executor._darken_hex
        return [
            base_color,                 # base (used for single-category)
            darken(base_color, 0.20),   # slightly darker
            lighten(base_color, 0.35),  # mid tint
            darken(base_color, 0.40),   # dark shade
        ]

    @staticmethod
    def _lighten_hex(hex_color: str, factor: float) -> str:
        """Lighten a hex color toward white by a factor (0.0 = unchanged, 1.0 = white)."""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            return f"#{r:02X}{g:02X}{b:02X}"
        except (ValueError, IndexError):
            return f"#{hex_color}"

    @staticmethod
    def _is_recolorable_mark(mark: Any) -> bool:
        mark_type = Node3Executor._mark_type(mark)
        return mark_type in {"bar", "line", "area", "point", "circle", "square", "tick", "trail", "arc"}

    @staticmethod
    def _mark_type(mark: Any) -> str:
        if isinstance(mark, str):
            return mark.lower()
        if isinstance(mark, dict) and isinstance(mark.get("type"), str):
            return str(mark["type"]).lower()
        return ""

    @staticmethod
    def _extract_title_from_intent(intent: str) -> str:
        raw = intent.strip()
        if not raw:
            return ""
        lower = raw.lower()
        if lower.startswith("title:"):
            return raw.split(":", 1)[1].strip()
        if lower.startswith("headline:"):
            return raw.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _extract_annotation_text(intent: str) -> str:
        return intent.strip()

    @staticmethod
    def _intent_requests_trendline(intent: str) -> bool:
        lower = intent.lower()
        if "trendline: true" in lower:
            return True
        # Keep trendline opt-in to avoid accidental lines from normal narrative verbs like "rises/falls".
        trend_tokens = ("trendline", "trend line", "regression line", "趋势线", "回归线")
        return any(token in lower for token in trend_tokens)

    @staticmethod
    def _wrap_text(text: str, max_line_chars: Any) -> str:
        if not isinstance(text, str):
            return ""
        if not isinstance(max_line_chars, int) or max_line_chars <= 0:
            return text
        wrapped_lines: list[str] = []
        for raw_line in text.splitlines() or [text]:
            if len(raw_line) <= max_line_chars:
                wrapped_lines.append(raw_line)
                continue
            if " " in raw_line:
                words = raw_line.split(" ")
                current = words[0]
                for word in words[1:]:
                    if len(current) + 1 + len(word) <= max_line_chars:
                        current = f"{current} {word}"
                    else:
                        wrapped_lines.append(current)
                        current = word
                wrapped_lines.append(current)
                continue
            start = 0
            while start < len(raw_line):
                wrapped_lines.append(raw_line[start : start + max_line_chars])
                start += max_line_chars
        return "\n".join(wrapped_lines)

    @staticmethod
    def _normalize_font_size(value: Any, fallback: int) -> int:
        if isinstance(value, int) and value >= 12:
            return value
        return fallback

    @staticmethod
    def _apply_annotation_mark_style(mark: dict[str, Any], min_font_size: int) -> None:
        try:
            current_font = int(mark.get("fontSize", min_font_size))
        except (TypeError, ValueError):
            current_font = min_font_size
        try:
            current_line_height = int(mark.get("lineHeight", min_font_size + 4))
        except (TypeError, ValueError):
            current_line_height = min_font_size + 4
        mark["fontSize"] = max(current_font, min_font_size)
        mark["lineHeight"] = max(current_line_height, min_font_size + 4)
        mark.setdefault("align", "left")
        mark.setdefault("baseline", "middle")
        if "limit" not in mark:
            mark["limit"] = 400
        mark.setdefault("fontWeight", 600)

    @staticmethod
    def _annotation_canvas_bounds(spec: dict[str, Any]) -> tuple[int, int]:
        width = Node3Executor._extract_canvas_dim(spec.get("width"), fallback=640)
        height = Node3Executor._extract_canvas_dim(spec.get("height"), fallback=360)
        return width, height

    @staticmethod
    def _extract_canvas_dim(value: Any, fallback: int) -> int:
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
        if isinstance(value, str):
            m = re.search(r"(\d+)", value)
            if m:
                return int(m.group(1))
        return fallback

    @staticmethod
    def _clamp_int(value: int, low: int, high: int) -> int:
        if low > high:
            return low
        return max(low, min(value, high))

    @staticmethod
    def _normalize_annotation_encoding_position(item: dict[str, Any], spec: dict[str, Any]) -> None:
        encoding = item.get("encoding")
        if not isinstance(encoding, dict):
            return
        width, height = Node3Executor._annotation_canvas_bounds(spec)
        x = encoding.get("x")
        if isinstance(x, dict) and isinstance(x.get("value"), (int, float)):
            x["value"] = Node3Executor._clamp_int(int(x["value"]), 8, max(8, width - 24))
        y = encoding.get("y")
        if isinstance(y, dict) and isinstance(y.get("value"), (int, float)):
            y["value"] = Node3Executor._clamp_int(int(y["value"]), 18, max(18, height - 12))

    @staticmethod
    def _estimate_annotation_max_chars(canvas_width: int, x_ratio: float, align: str, font_size: int) -> int:
        safe_width = max(420, canvas_width)
        ratio = Node3Executor._clamp_float(x_ratio, 0.05, 0.95)
        if align == "right":
            available_px = int(safe_width * ratio) - 28
        else:
            available_px = int(safe_width * (1 - ratio)) - 28
        available_px = max(220, min(available_px, 560))
        approx_char_px = max(6.0, float(font_size) * 0.58)
        max_chars = int(available_px / approx_char_px)
        return max(28, min(max_chars, 60))

    @staticmethod
    def _clamp_float(value: float, low: float, high: float) -> float:
        if low > high:
            return low
        return max(low, min(value, high))

    @staticmethod
    def _fit_annotation_mark_text_to_canvas(
        text: str,
        mark: dict[str, Any],
        item: dict[str, Any],
        spec: dict[str, Any],
        min_font_size: int,
    ) -> str:
        encoding = item.get("encoding")
        if not isinstance(encoding, dict):
            return text
        x = encoding.get("x")
        if not (isinstance(x, dict) and isinstance(x.get("value"), (int, float))):
            return text
        width, _ = Node3Executor._annotation_canvas_bounds(spec)
        x_value = Node3Executor._clamp_int(int(x["value"]), 8, max(8, width - 24))
        align = str(mark.get("align", "left")).lower()
        x_ratio = x_value / max(1, width)
        max_chars = Node3Executor._estimate_annotation_max_chars(
            canvas_width=width,
            x_ratio=x_ratio,
            align=align if align in {"left", "right"} else "left",
            font_size=min_font_size,
        )
        return Node3Executor._wrap_text(text, max_chars)

    @staticmethod
    def _apply_emphasis_style(mark: dict[str, Any], emphasis_style: Any) -> None:
        if str(emphasis_style).lower() != "amplify":
            return
        text = mark.get("text")
        if isinstance(text, str):
            mark["text"] = text.upper()
        mark["fontWeight"] = 800
        try:
            size = int(mark.get("fontSize", 14))
        except (TypeError, ValueError):
            size = 14
        mark["fontSize"] = max(size, 22)
        mark["color"] = "#111111"

    @staticmethod
    def _prune_offtopic_annotations(spec: dict[str, Any], narrative_keywords: Any) -> None:
        """Remove all annotation layers from a spec before adding a new one.
        This prevents stacking contradictory annotations from parent nodes.
        Layers without 'annotation' in their description are always kept."""
        layer = spec.get("layer")
        if isinstance(layer, list):
            filtered_layers: list[Any] = []
            for item in layer:
                if not isinstance(item, dict):
                    filtered_layers.append(item)
                    continue
                description = str(item.get("description", "")).lower()
                # Remove any layer tagged as annotation or trendline from prior nodes
                if "annotation" in description or "trendline" in description:
                    continue
                filtered_layers.append(item)
            spec["layer"] = filtered_layers
        # Also clear usermeta annotations
        usermeta = spec.get("usermeta")
        if isinstance(usermeta, dict) and isinstance(usermeta.get("annotations"), list):
            usermeta["annotations"] = []

    @staticmethod
    def _clean_annotation_text(text: str) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        clean = clean.replace("...", ".").replace("…", ".")
        clean = clean.replace("broader context", "specific context")
        if not clean:
            return ""
        if clean[-1] not in {".", "!", "?", "。", "！", "？"}:
            clean = f"{clean}."
        return clean

    # ── LLM-driven and fallback text generation ──────────────────────────

    def _generate_title(self, spec: dict[str, Any], intent: str, parent_title: str) -> str:
        """Generate a role-aware, data-grounded title via LLM or fallback."""
        evidence = self._extract_chart_evidence(spec)
        llm_title = self._generate_text_via_llm("change_title", intent, spec, parent_title, evidence)
        if llm_title:
            return llm_title
        return self._generate_title_fallback(parent_title, evidence)

    def _generate_annotation(self, spec: dict[str, Any], intent: str) -> str:
        """Generate a role-aware, data-grounded annotation via LLM or fallback."""
        evidence = self._extract_chart_evidence(spec)
        parent_title = self._extract_current_title(spec)
        llm_ann = self._generate_text_via_llm("add_annotation", intent, spec, parent_title, evidence)
        if llm_ann:
            return llm_ann
        return self._generate_annotation_fallback(parent_title, evidence)

    def _generate_text_via_llm(
        self,
        operation: str,
        intent: str,
        spec: dict[str, Any],
        current_text: str,
        evidence: dict[str, Any],
    ) -> str | None:
        if self.llm_client is None:
            return None
        role = self._current_role or "Amplifier"
        institution = self._current_institution or ""
        persona = self._PERSONA_PROMPTS.get(role, self._PERSONA_PROMPTS["Amplifier"])
        is_title = operation == "change_title"
        examples = self._TITLE_EXAMPLES if is_title else self._ANNOTATION_EXAMPLES
        data_summary = self._format_evidence_for_prompt(evidence)
        max_chars = 60 if is_title else 100
        op_label = "title" if is_title else "annotation"

        role_constraint = ""
        if role == "Adverser":
            role_constraint = (
                "CRITICAL ADVERSER CONSTRAINT:\n"
                "- You MUST produce a COUNTER-NARRATIVE that OPPOSES the overall data trend.\n"
                "- If data shows overall warming/rising → your title must claim cooling/declining.\n"
                "- If data shows overall decline → your title must claim recovery/rising.\n"
                "- Example: data shows 'Global Temperature Anomaly rising' → you write 'Global Cooling'\n"
                "- Your annotation must reference a specific data segment that supports your counter-claim.\n"
            )
        elif role == "Amplifier":
            role_constraint = (
                "AMPLIFIER CONSTRAINT:\n"
                "- STRENGTHEN the existing trend. If data rises, emphasize how much it surged.\n"
                "- Use dramatic, concise language: 'Highest Since X', 'Surging Past Y'.\n"
                "- Annotation should be at the peak/extreme point with specific data.\n"
            )
        elif role in ("Extender", "Analyst"):
            role_constraint = (
                "EXTENDER CONSTRAINT:\n"
                "- Expand the current topic into its broader social, policy, or comparative dimension.\n"
                "- Reference the ACTUAL metric name and specific numbers/years from the chart summary.\n"
                "- Connect the data trend to a wider issue (policy response, structural drivers, comparisons).\n"
                "- NEVER write vague phrases like 'broader context' or 'Structural Shifts Behind the Trend'.\n"
                "- Example: if data shows COVID deaths rising, write about how the pandemic affected healthcare systems.\n"
                "- Example: if data shows fish production falling, connect to ocean policy and food security.\n"
            )

        prompt = (
            f"{persona}\n\n"
            f"{role_constraint}\n"
            f"Platform/institution: {institution or 'unknown'}\n"
            f"Current {op_label}: {current_text}\n"
            f"Operation intent: {intent}\n\n"
            f"Chart data summary:\n{data_summary}\n\n"
            f"{examples}\n"
            f"Output Constraint:\n"
            f"- Output ONLY the new {op_label} text, nothing else.\n"
            f"- Maximum {max_chars} characters.\n"
            f"- Must be a concrete, data-specific statement — NOT a generic directive.\n"
            f"- Must reflect your role's narrative strategy and the actual data.\n"
            f"- English only. No quotes around the output.\n"
        )
        result = self.llm_client.generate_text(prompt)
        if result:
            clean = result.strip().strip('"').strip("'").strip()
            clean = clean.split("\n")[0].strip()
            return Node3Executor._enforce_text_length(clean, is_title=is_title)
        return None

    def _generate_title_fallback(self, parent_title: str, evidence: dict[str, Any]) -> str:
        """Data-driven role-specific title generation when LLM is unavailable."""
        role = self._current_role or "Amplifier"
        y_label = evidence.get("y_label", "Value")
        trend = evidence.get("trend", "")
        peak_val = evidence.get("peak_y")
        peak_x = evidence.get("peak_x", "")
        low_val = evidence.get("low_y")
        low_x = evidence.get("low_x", "")
        pct_change = evidence.get("pct_change")

        if role == "Amplifier":
            if trend == "rising" and peak_x:
                return f"{y_label} Highest Near {peak_x}"
            if trend == "falling" and pct_change is not None:
                return f"{y_label} Down {abs(pct_change):.0f}%"
            if peak_x:
                return f"Sharp Shift in {y_label} Near {peak_x}"
            return f"{y_label} Trend Intensifying"

        if role == "Adverser":
            # Counter-narrative: oppose the overall trend
            if trend == "rising":
                decline = evidence.get("decline_window")
                if decline:
                    return f"{y_label} Dropping Since {decline['start']}"
                if low_x:
                    return f"{y_label} Cooling Trend"
                return f"{y_label} Not As High As Claimed"
            if trend == "falling":
                growth = evidence.get("growth_window")
                if growth:
                    return f"{y_label} Rising Since {growth['start']}"
                if peak_x:
                    return f"{y_label} Recovery Underway"
                return f"{y_label} Stabilizing"
            return f"Counter Evidence on {y_label}"

        if role in ("Extender", "Analyst"):
            if parent_title:
                short = parent_title.split("–")[0].split("-")[0].strip()[:40]
                return f"{short} and Its Broader Implications"
            return f"{y_label} Across Multiple Dimensions"

        # Bridger
        if parent_title:
            return parent_title
        return f"{y_label} Update"

    def _generate_annotation_fallback(self, parent_title: str, evidence: dict[str, Any]) -> str:
        """Data-driven role-specific annotation when LLM is unavailable."""
        role = self._current_role or "Amplifier"
        peak_y = evidence.get("peak_y")
        peak_x = evidence.get("peak_x", "")
        low_y = evidence.get("low_y")
        low_x = evidence.get("low_x", "")
        trend = evidence.get("trend", "")
        pct_change = evidence.get("pct_change")
        y_label = evidence.get("y_label", "Value")
        decline_window = evidence.get("decline_window")

        if role == "Amplifier":
            if peak_y is not None and peak_x:
                return f"Peak: {peak_y:.1f} at {peak_x}."
            if trend == "rising" and pct_change is not None:
                return f"{y_label} up {abs(pct_change):.0f}% overall."
            return f"{y_label} shows a clear upward pattern."

        if role == "Adverser":
            # Counter-narrative annotation: reference data that opposes overall trend
            if trend == "rising" and decline_window:
                return f"Cooling: {decline_window['start_val']:.1f} to {decline_window['end_val']:.1f} ({decline_window['start']}-{decline_window['end']})."
            if trend == "falling":
                growth = evidence.get("growth_window")
                if growth:
                    return f"Recovery: {growth['start_val']:.1f} to {growth['end_val']:.1f} ({growth['start']}-{growth['end']})."
            if low_y is not None and low_x:
                return f"Dropped to {low_y:.1f} at {low_x}."
            return f"Data challenges the prevailing narrative."

        if role in ("Extender", "Analyst"):
            if peak_y is not None and peak_x:
                return f"Notable shift near {peak_x} ({peak_y:.1f})."
            return f"Broader context needed for {y_label}."

        # Bridger
        if peak_y is not None:
            return f"Current level: {peak_y:.1f}."
        return f"Data as reported."

    @staticmethod
    def _extract_chart_evidence(spec: dict[str, Any]) -> dict[str, Any]:
        """Extract quantitative evidence from chart spec for text generation."""
        evidence: dict[str, Any] = {}
        candidates = Node3Executor._collect_xy_data_candidates(spec)
        if not candidates:
            return evidence

        # Pick the candidate with highest relative variance (CV) — most story-worthy field
        x_field = y_field = ""
        numeric_rows: list[dict[str, Any]] = []
        best_cv = -1.0
        for c in candidates:
            xf, yf = c["x_field"], c["y_field"]
            values = c["values"]
            rows = [
                r for r in values
                if isinstance(r, dict) and isinstance(r.get(yf), (int, float)) and xf in r
            ]
            if len(rows) < 2:
                continue
            y_vals_c = [float(r[yf]) for r in rows]
            mean_c = sum(y_vals_c) / len(y_vals_c)
            if mean_c == 0:
                continue
            var_c = sum((v - mean_c) ** 2 for v in y_vals_c) / len(y_vals_c)
            cv = (var_c ** 0.5) / abs(mean_c)
            if cv > best_cv:
                best_cv = cv
                x_field, y_field, numeric_rows = xf, yf, rows

        y_axis_title = Node3Executor._extract_axis_title(spec, y_field, axis="y")
        x_axis_title = Node3Executor._extract_axis_title(spec, x_field, axis="x")
        evidence["x_label"] = x_axis_title or (Node3Executor._humanize_field_name(x_field) if x_field else "")
        evidence["y_label"] = y_axis_title or (Node3Executor._humanize_field_name(y_field) if y_field else "")

        if len(numeric_rows) < 2:
            return evidence

        y_vals = [float(r[y_field]) for r in numeric_rows]
        first_y, last_y = y_vals[0], y_vals[-1]
        peak_idx = max(range(len(y_vals)), key=lambda i: y_vals[i])
        low_idx = min(range(len(y_vals)), key=lambda i: y_vals[i])

        evidence["first_y"] = first_y
        evidence["last_y"] = last_y
        evidence["peak_y"] = y_vals[peak_idx]
        evidence["peak_x"] = numeric_rows[peak_idx].get(x_field, "")
        evidence["low_y"] = y_vals[low_idx]
        evidence["low_x"] = numeric_rows[low_idx].get(x_field, "")
        evidence["count"] = len(numeric_rows)

        if first_y != 0:
            evidence["pct_change"] = ((last_y - first_y) / abs(first_y)) * 100
        evidence["trend"] = "rising" if last_y > first_y else ("falling" if last_y < first_y else "flat")

        # Find steepest decline window (for Adverser counter-narrative)
        # Search the FULL range (≥5 points) so spiky datasets like COVID deaths are handled correctly
        if len(y_vals) >= 5:
            best_decline_start, best_decline_end, best_score = 0, 0, -1.0
            for i in range(0, len(y_vals) - 4):
                if y_vals[i] <= 0:
                    continue
                for j in range(i + 4, len(y_vals)):
                    if y_vals[j] >= y_vals[i]:
                        continue
                    if y_vals[j] <= 0:
                        continue
                    pct = (y_vals[i] - y_vals[j]) / y_vals[i] * 100
                    # Prefer large drops with high starting value; mild recency bonus
                    score = pct + y_vals[i] * 0.01 + (i + j) / (2 * len(y_vals)) * 10
                    if score > best_score:
                        best_score = score
                        best_decline_start, best_decline_end = i, j
            if best_score > 0:
                evidence["decline_window"] = {
                    "start": numeric_rows[best_decline_start].get(x_field, ""),
                    "end": numeric_rows[best_decline_end].get(x_field, ""),
                    "start_val": y_vals[best_decline_start],
                    "end_val": y_vals[best_decline_end],
                    "pct": (y_vals[best_decline_start] - y_vals[best_decline_end]) / y_vals[best_decline_start] * 100,
                }

            # Find steepest growth window (for Amplifier emphasis)
            best_growth_start = 0
            best_growth_end = 0
            best_growth_pct = 0.0
            for i in range(len(y_vals) - 2):
                for j in range(i + 2, min(i + max(4, len(y_vals) // 2), len(y_vals))):
                    if y_vals[i] > 0 and y_vals[j] > y_vals[i]:
                        pct = (y_vals[j] - y_vals[i]) / y_vals[i] * 100
                        if pct > best_growth_pct:
                            best_growth_pct = pct
                            best_growth_start = i
                            best_growth_end = j
            if best_growth_pct > 5:
                evidence["growth_window"] = {
                    "start": numeric_rows[best_growth_start].get(x_field, ""),
                    "end": numeric_rows[best_growth_end].get(x_field, ""),
                    "start_val": y_vals[best_growth_start],
                    "end_val": y_vals[best_growth_end],
                    "pct": best_growth_pct,
                }

        return evidence

    @staticmethod
    def _format_evidence_for_prompt(evidence: dict[str, Any]) -> str:
        if not evidence:
            return "No quantitative data available in chart spec."
        parts = []
        if "x_label" in evidence:
            parts.append(f"X-axis: {evidence['x_label']}, Y-axis: {evidence['y_label']}")
        if "trend" in evidence:
            parts.append(f"Overall trend: {evidence['trend']}")
        if "first_y" in evidence:
            parts.append(f"Range: {evidence['first_y']:.2f} → {evidence['last_y']:.2f}")
        if "pct_change" in evidence:
            parts.append(f"Change: {evidence['pct_change']:.1f}%")
        if "peak_y" in evidence:
            parts.append(f"Peak: {evidence['peak_y']:.2f} at {evidence['peak_x']}")
        if "low_y" in evidence:
            parts.append(f"Low: {evidence['low_y']:.2f} at {evidence['low_x']}")
        dw = evidence.get("decline_window")
        if dw:
            parts.append(f"Steepest decline: {dw['start']} to {dw['end']} ({dw['pct']:.1f}% drop)")
        gw = evidence.get("growth_window")
        if gw:
            parts.append(f"Steepest growth: {gw['start']} to {gw['end']} ({gw['pct']:.1f}% rise)")
        return "\n".join(parts)

    @staticmethod
    def _extract_current_title(spec: dict[str, Any]) -> str:
        title = spec.get("title")
        if isinstance(title, str):
            return title.strip()
        if isinstance(title, dict):
            return str(title.get("text", "")).strip()
        return ""

    @staticmethod
    def _is_generic_intent(text: str) -> bool:
        """Detect generic/mechanical intent strings that need replacement."""
        lower = text.lower().strip()
        generic_markers = (
            "context note added",
            "updated annotation",
            "assert strong",
            "broader context",
            "reframed:",
            "reframe title",
            "highlight trend",
            "focus on window",
            "reduce source",
            "emphasize",
        )
        return any(marker in lower for marker in generic_markers)

    @staticmethod
    def _enforce_text_length(text: str, is_title: bool) -> str:
        limit = 60 if is_title else 150
        if len(text) <= limit:
            return text
        truncated = text[:limit]
        last_space = truncated.rfind(" ")
        if last_space > limit * 0.6:
            return truncated[:last_space].rstrip(".,;:!? ")
        return truncated.rstrip(".,;:!? ")

