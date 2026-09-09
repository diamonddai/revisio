from app.graph.workflow import NodeC
from app.transform.node3_executor import ExecutionResult, Node3Executor
from app.transform.spec_renderer import SpecRenderer
from app.transform.spec_validator import SpecValidator


def _sample_layered_spec() -> dict:
    return {
        "title": "Original",
        "layer": [
            {
                "mark": {"type": "line", "color": "#005d9e"},
                "encoding": {"x": {"field": "date", "type": "temporal"}, "y": {"field": "rate", "type": "quantitative"}},
            },
            {
                "mark": {
                    "type": "text",
                    "text": "Sources: Example Data Agency",
                    "color": "#666666",
                }
            },
        ],
    }


def test_executor_applies_core_ops_to_chart_spec() -> None:
    executor = Node3Executor()
    result = executor.execute(
        parent_chart_spec=_sample_layered_spec(),
        selected_operations=[
            {"operation": "change_title", "layer": "text", "intent": "highlight trend"},
            {"operation": "add_annotation", "layer": "text", "intent": "new annotation"},
            {"operation": "change_color", "layer": "visual", "intent": "emphasize"},
            {"operation": "select_data_range", "layer": "data", "intent": "narrow focus"},
            {"operation": "delete_source", "layer": "text", "intent": "remove attribution"},
        ],
        shift_magnitude="sig",
    )
    assert result.updated_chart_spec is not None
    updated = result.updated_chart_spec
    title_text = str(updated.get("title", ""))
    assert title_text != "Original"
    assert len(title_text) > 0
    assert "transform" in updated and isinstance(updated["transform"], list) and updated["transform"]
    # source footer should be removed by strict prefix rule
    assert all(
        not (
            isinstance(item, dict)
            and isinstance(item.get("mark"), dict)
            and isinstance(item["mark"].get("text"), str)
            and item["mark"]["text"].lower().startswith("sources:")
        )
        for item in updated.get("layer", [])
    )
    assert len(result.executed_operations) >= 4


def test_executor_fallback_annotation_when_not_layered() -> None:
    executor = Node3Executor()
    result = executor.execute(
        parent_chart_spec={"mark": {"type": "bar"}, "encoding": {"x": {"field": "x"}, "y": {"field": "y"}}},
        selected_operations=[{"operation": "add_annotation", "layer": "text", "intent": "fallback note"}],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    assert "NOTE:" in str(result.updated_chart_spec.get("description", ""))


def test_executor_annotation_positions_do_not_fully_overlap() -> None:
    executor = Node3Executor()
    base = _sample_layered_spec()
    result = executor.execute(
        parent_chart_spec=base,
        selected_operations=[
            {"operation": "add_annotation", "layer": "text", "intent": "first"},
            {"operation": "add_annotation", "layer": "text", "intent": "second"},
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    anno_layers = [
        item
        for item in layers
        if isinstance(item, dict)
        and isinstance(item.get("mark"), dict)
        and item["mark"].get("type") == "text"
        and item.get("description") == "Node3 added annotation"
    ]
    assert len(anno_layers) >= 2
    p1 = anno_layers[-2]["encoding"]
    p2 = anno_layers[-1]["encoding"]
    assert p1 != p2


def test_executor_data_aware_annotation_adds_leader_line() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {
                "data": {
                    "values": [
                        {"year": 2019, "value": 10},
                        {"year": 2020, "value": 15},
                        {"year": 2021, "value": 26},
                    ]
                },
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            }
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[{"operation": "add_annotation", "layer": "text", "intent": "highlight peak"}],
        shift_magnitude="sig",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert any(isinstance(item, dict) and item.get("description") == "Node3 added annotation anchor" for item in layers)
    assert any(isinstance(item, dict) and item.get("description") == "Node3 added annotation leader" for item in layers)
    assert any(isinstance(item, dict) and item.get("description") == "Node3 added annotation" for item in layers)


def test_executor_annotation_position_is_clamped_to_canvas() -> None:
    executor = Node3Executor()
    spec = {
        "width": 180,
        "height": 80,
        "layer": [
            {
                "mark": {"type": "line", "color": "#005d9e"},
                "encoding": {"x": {"field": "date", "type": "temporal"}, "y": {"field": "rate", "type": "quantitative"}},
            }
        ],
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {"operation": "add_annotation", "layer": "text", "intent": "first"},
            {"operation": "add_annotation", "layer": "text", "intent": "second"},
            {"operation": "add_annotation", "layer": "text", "intent": "third"},
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    y_values = []
    x_values = []
    for item in layers:
        if not (isinstance(item, dict) and item.get("description") == "Node3 added annotation"):
            continue
        encoding = item.get("encoding", {})
        x = encoding.get("x", {})
        y = encoding.get("y", {})
        if isinstance(x, dict) and isinstance(x.get("value"), (int, float)):
            x_values.append(int(x["value"]))
        if isinstance(y, dict) and isinstance(y.get("value"), (int, float)):
            y_values.append(int(y["value"]))
    assert x_values and y_values
    assert all(8 <= value <= 156 for value in x_values)
    assert all(18 <= value <= 68 for value in y_values)


def test_executor_data_annotation_uses_right_align_near_right_edge() -> None:
    executor = Node3Executor()
    spec = {
        "width": 520,
        "layer": [
            {
                "data": {
                    "values": [
                        {"year": 2019, "value": 9},
                        {"year": 2020, "value": 14},
                        {"year": 2021, "value": 22},
                    ]
                },
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            }
        ],
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "add_annotation",
                "layer": "text",
                "intent": "highlight latest value and explain this is a strong rise in recent years with policy impact",
                "params": {"max_line_chars": 32},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    text_layer = next(
        (
            item
            for item in result.updated_chart_spec.get("layer", [])
            if isinstance(item, dict) and item.get("description") == "Node3 added annotation"
        ),
        None,
    )
    assert text_layer is not None
    mark = text_layer.get("mark", {})
    assert mark.get("align") == "right"
    assert mark.get("dx") == -10
    y_encoding = text_layer.get("encoding", {}).get("y", {})
    assert isinstance(y_encoding, dict)
    assert "datum" in y_encoding
    assert y_encoding.get("axis") is None
    assert "field" not in y_encoding
    x_encoding = text_layer.get("encoding", {}).get("x", {})
    assert isinstance(x_encoding, dict)
    assert x_encoding.get("axis") is None
    payload = text_layer.get("data", {}).get("values", [{}])[0]
    ann_text = payload.get("annotation_text", "")
    assert isinstance(ann_text, list) and len(ann_text) > 1, f"Expected multi-line array, got {ann_text}"


def test_executor_adds_trendline_when_annotation_requests_it() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {
                "data": {
                    "values": [
                        {"year": 2019, "value": 10},
                        {"year": 2020, "value": 15},
                        {"year": 2021, "value": 26},
                    ]
                },
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            }
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "add_annotation",
                "layer": "text",
                "intent": "Series rises from 10 to 26",
                "params": {"include_trendline": True},
            }
        ],
        shift_magnitude="sig",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert any(isinstance(item, dict) and item.get("description") == "Node3 added trendline" for item in layers)


def test_executor_does_not_auto_add_trendline_for_rise_wording_only() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {
                "data": {
                    "values": [
                        {"year": 2019, "value": 10},
                        {"year": 2020, "value": 15},
                        {"year": 2021, "value": 26},
                    ]
                },
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            }
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "add_annotation",
                "layer": "text",
                "intent": "Series rises from 10 to 26.",
                "params": {},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert not any(isinstance(item, dict) and item.get("description") == "Node3 added trendline" for item in layers)


def test_executor_change_color_applies_chart_wide_palette() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "series", "type": "nominal", "scale": {"range": ["#000000"]}},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "change_color",
                "layer": "visual",
                "intent": "forest theme",
                "params": {"scope": "chart_global"},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    updated = result.updated_chart_spec
    assert updated.get("mark", {}).get("color") == "#2E8B57"
    color_range = updated.get("encoding", {}).get("color", {}).get("scale", {}).get("range")
    assert isinstance(color_range, list) and len(color_range) == 4
    assert updated.get("config", {}).get("range", {}).get("category") == color_range


def test_executor_change_color_does_not_recolor_text_marks() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {"mark": {"type": "line", "color": "#005d9e"}},
            {"mark": {"type": "text", "text": "Annotation", "color": "#111111"}},
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {"operation": "change_color", "layer": "visual", "intent": "forest theme", "params": {"scope": "chart_global"}}
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert layers[0].get("mark", {}).get("color") == "#2E8B57"
    assert layers[1].get("mark", {}).get("color") == "#111111"


def test_executor_change_color_does_not_recolor_rect_background_layer() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {"mark": {"type": "rect", "color": "#eeeeee"}},
            {"mark": {"type": "bar", "color": "#666666"}},
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {"operation": "change_color", "layer": "visual", "intent": "vivid contrast", "params": {"scope": "chart_global"}}
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert layers[0].get("mark", {}).get("color") == "#eeeeee"
    assert layers[1].get("mark", {}).get("color") != "#666666"


def test_executor_change_color_social_contrast_palette() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "series", "type": "nominal"},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "change_color",
                "layer": "visual",
                "intent": "vivid high contrast social media aesthetic",
                "params": {"scope": "chart_global", "palette_style": "social_contrast"},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    color_range = result.updated_chart_spec.get("config", {}).get("range", {}).get("category", [])
    assert isinstance(color_range, list) and "#E53B22" in color_range


def test_executor_change_color_updates_conditional_color_encoding_values() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "bar"},
        "data": {"values": [{"x": 1, "y": 2}, {"x": 2, "y": -1}]},
        "encoding": {
            "x": {"field": "x", "type": "quantitative"},
            "y": {"field": "y", "type": "quantitative"},
            "color": {
                "condition": {"test": "datum.y >= 0", "value": "#CC3344"},
                "value": "#2B6CB0",
            },
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "change_color",
                "layer": "visual",
                "intent": "amplify contrast for risk framing",
                "params": {"scope": "chart_global", "palette_style": "amplifier_contrast"},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    color = result.updated_chart_spec.get("encoding", {}).get("color", {})
    assert isinstance(color, dict)
    condition = color.get("condition", {})
    assert isinstance(condition, dict)
    assert condition.get("value") != "#CC3344"
    # Secondary color is now derived from the primary palette, not hardcoded blue.
    # "risk" intent → primary #C23B22 → secondary #8E2717
    assert color.get("value") != "#2B6CB0", "base value should have changed from original"


def test_executor_applies_axis_and_legend_ops() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "line"},
        "data": {"values": [
            {"year": 2010, "value": 50, "series": "A"},
            {"year": 2011, "value": 55, "series": "A"},
            {"year": 2012, "value": 60, "series": "A"},
            {"year": 2013, "value": 65, "series": "A"},
            {"year": 2014, "value": 70, "series": "A"},
            {"year": 2015, "value": 75, "series": "A"},
            {"year": 2016, "value": 80, "series": "A"},
            {"year": 2017, "value": 85, "series": "A"},
            {"year": 2018, "value": 90, "series": "A"},
            {"year": 2019, "value": 95, "series": "A"},
        ]},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "series", "type": "nominal", "legend": None},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {"operation": "simplify_axis", "layer": "visual", "intent": "reduce clutter"},
            {"operation": "change_axis_scale", "layer": "visual", "intent": "zoom in on data range"},
            {"operation": "add_legend", "layer": "text", "intent": "emphasize series groups"},
            {"operation": "change_legend", "layer": "text", "intent": "Updated legend"},
        ],
        shift_magnitude="sig",
    )
    assert result.updated_chart_spec is not None
    encoding = result.updated_chart_spec.get("encoding", {})
    assert isinstance(encoding, dict)
    assert isinstance(encoding.get("x"), dict)
    assert isinstance(encoding.get("x", {}).get("axis"), dict)
    # simplify_axis now defaults to interval_labels mode (labels visible, sparse)
    assert encoding.get("x", {}).get("axis", {}).get("labels") is True
    # change_axis_scale now adjusts y-axis domain to zoom into data range
    y_scale = encoding.get("y", {}).get("scale", {})
    assert isinstance(y_scale.get("domain"), list)
    assert len(y_scale["domain"]) == 2
    assert isinstance(encoding.get("color"), dict)
    assert encoding.get("color", {}).get("legend", {}).get("title") == "Updated legend"


def test_executor_simplify_axis_interval_labels_mode() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "line"},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "simplify_axis",
                "layer": "visual",
                "intent": "keep sparse ticks",
                "params": {"target_axis": "x", "mode": "interval_labels", "label_interval": 5},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    axis = result.updated_chart_spec.get("encoding", {}).get("x", {}).get("axis", {})
    assert axis.get("labels") is True
    assert axis.get("ticks") is True
    assert axis.get("grid") is False
    assert axis.get("labelExpr") == "datum.value % 5 == 0 ? datum.label : ''"


def test_spec_validator_rejects_missing_mark_and_layer() -> None:
    validator = SpecValidator()
    result = validator.validate({"description": "broken"})
    assert result.ok is False
    assert "missing_mark_or_layer" in result.errors


def test_spec_validator_rejects_semantic_axis_encoding_conflicts() -> None:
    validator = SpecValidator()
    invalid_spec = {
        "mark": {"type": "line"},
        "encoding": {
            "x2": {"field": "year_end", "type": "quantitative"},
            "color": {"type": "nominal", "legend": {"title": "Color legend"}},
            "tooltip": {"axis": {"title": "bad axis"}},
        },
    }
    result = validator.validate(invalid_spec)
    assert result.ok is False
    assert "x2_without_x" in result.errors
    assert "encoding_channel_missing_field_or_value:color" in result.errors
    assert "axis_on_non_positional_channel:tooltip" in result.errors


def test_add_legend_requires_emphasis_and_absent_legend() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "line"},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "series", "type": "nominal", "legend": None},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[{"operation": "add_legend", "layer": "text", "intent": "series groups"}],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    assert result.executed_operations == []


def test_executor_covers_remaining_ops_and_provenance_fields() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "line", "color": "#3366cc"},
        "encoding": {
            "x": {"field": "date", "type": "temporal"},
            "y": {"field": "value", "type": "quantitative"},
            "color": {"field": "series", "type": "nominal", "legend": None},
            "detail": {"field": "region", "type": "nominal"},
        },
        "description": "Old annotation text",
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {"operation": "change_chart_type", "layer": "visual", "intent": "use bar"},
            {"operation": "add_background", "layer": "visual", "intent": "subtle background"},
            {"operation": "change_aspect_ratio", "layer": "visual", "intent": "tall portrait"},
            {"operation": "select_data_variables", "layer": "data", "intent": "keep essentials"},
            {"operation": "change_data_granularity", "layer": "data", "intent": "monthly"},
            {"operation": "change_annotation", "layer": "text", "intent": "Refined annotation"},
        ],
        shift_magnitude="sig",
    )
    assert result.updated_chart_spec is not None
    updated = result.updated_chart_spec
    assert updated.get("mark", {}).get("type") == "bar"
    assert updated.get("view", {}).get("fill") == "#F7F7FA"
    assert updated.get("width") == 420 and updated.get("height") == 640
    remaining_encoding = updated.get("encoding", {})
    assert isinstance(remaining_encoding, dict)
    assert not ("detail" in remaining_encoding and "color" in remaining_encoding)
    assert updated.get("encoding", {}).get("x", {}).get("timeUnit") == "yearmonth"
    assert str(updated.get("description", "")).startswith("Refined annotation") or updated.get("description") == "Old annotation text"
    assert result.operation_audit
    required = {"operation", "params", "target_paths", "before", "after", "status", "error"}
    assert required.issubset(set(result.operation_audit[0].keys()))


def test_change_chart_type_stacked_bar_to_line_uses_y_stack() -> None:
    """Fold + stacked bar → line must use y.stack=zero so totals match bar silhouette."""
    import copy

    spec = {
        "data": {
            "values": [
                {"w": 1, "a": 10, "b": 5},
                {"w": 2, "a": 12, "b": 8},
            ]
        },
        "encoding": {"x": {"field": "w", "type": "ordinal"}},
        "layer": [
            {
                "transform": [
                    {"fold": ["a", "b"], "as": ["_k", "deaths"]},
                    {"calculate": "datum._k === 'a' ? 'A' : 'B'", "as": "series"},
                ],
                "mark": {"type": "bar"},
                "encoding": {
                    "y": {"field": "deaths", "type": "quantitative"},
                    "color": {"field": "series", "type": "nominal"},
                    "order": {"field": "_k", "sort": "descending"},
                },
            }
        ],
    }
    s2 = copy.deepcopy(spec)
    ok, _before, after = Node3Executor._change_chart_type(s2, "convert to line chart")
    assert ok and after == "line"
    y_enc = s2["layer"][0]["encoding"]["y"]
    assert y_enc.get("stack") == "zero"
    assert "order" in s2["layer"][0]["encoding"]
    assert s2["layer"][0]["mark"].get("strokeWidth") == 5


def test_executor_wraps_title_and_annotation_text() -> None:
    executor = Node3Executor()
    spec = {
        "title": "Original long title",
        "layer": [
            {
                "data": {"values": [{"year": 2022, "value": 10}, {"year": 2023, "value": 15}]},
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            }
        ],
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "change_title",
                "layer": "text",
                "intent": "title: This is a long reframed title for wrapping test",
                "params": {"max_line_chars": 16},
            },
            {
                "operation": "add_annotation",
                "layer": "text",
                "intent": "This is a long annotation sentence for wrapping verification.",
                "params": {"max_line_chars": 14},
            },
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    assert "\n" in str(result.updated_chart_spec.get("title", ""))
    layers = result.updated_chart_spec.get("layer", [])
    annotation_text_layer = next(
        (
            item
            for item in layers
            if isinstance(item, dict)
            and item.get("description") == "Node3 added annotation"
            and isinstance(item.get("encoding"), dict)
        ),
        None,
    )
    assert annotation_text_layer is not None
    data_values = annotation_text_layer.get("data", {}).get("values", [])
    assert isinstance(data_values, list) and data_values
    ann_val = data_values[0].get("annotation_text", "")
    assert isinstance(ann_val, list) and len(ann_val) >= 1, f"Expected list, got {ann_val}"
    assert isinstance(annotation_text_layer.get("mark", {}).get("limit"), int)


def test_executor_wraps_chinese_annotation_and_prunes_offtopic() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {
                "description": "Node3 added annotation",
                "mark": {"type": "text", "text": "unrelated old note"},
            },
            {
                "data": {"values": [{"year": 2022, "value": 10}, {"year": 2023, "value": 15}]},
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            },
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "add_annotation",
                "layer": "text",
                "intent": "亚马逊森林砍伐速度正在上升需要重点关注风险变化",
                "params": {
                    "max_line_chars": 8,
                    "min_font_size": 14,
                    "prune_offtopic_annotations": True,
                    "narrative_keywords": ["森林", "砍伐"],
                },
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    layers = result.updated_chart_spec.get("layer", [])
    assert all(
        not (
            isinstance(item, dict)
            and item.get("description") == "Node3 added annotation"
            and isinstance(item.get("mark"), dict)
            and item["mark"].get("text") == "unrelated old note"
        )
        for item in layers
    )
    text_layer = next(
        (
            item
            for item in layers
            if isinstance(item, dict)
            and item.get("description") == "Node3 added annotation"
            and isinstance(item.get("mark"), dict)
        ),
        None,
    )
    assert text_layer is not None
    payload = text_layer.get("data", {}).get("values", [{}])[0]
    ann_val = payload.get("annotation_text", "")
    assert isinstance(ann_val, list) and len(ann_val) >= 1, f"Expected list, got {ann_val}"
    assert int(text_layer.get("mark", {}).get("fontSize", 0)) >= 14


def test_executor_change_annotation_amplify_style() -> None:
    executor = Node3Executor()
    spec = {
        "layer": [
            {
                "description": "Node3 added annotation",
                "mark": {"type": "text", "text": "old annotation", "fontSize": 12},
            }
        ]
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "change_annotation",
                "layer": "text",
                "intent": "new stronger message",
                "params": {"emphasis_style": "amplify", "min_font_size": 15},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    mark = result.updated_chart_spec.get("layer", [])[0].get("mark", {})
    assert str(mark.get("text", "")).endswith(".")
    assert str(mark.get("text", "")).isupper()
    assert int(mark.get("fontSize", 0)) >= 16
    assert int(mark.get("fontWeight", 0)) >= 800


def test_executor_select_data_range_uses_params_window() -> None:
    executor = Node3Executor()
    spec = {
        "mark": {"type": "line"},
        "data": {"values": [{"year": 2019, "value": 10}, {"year": 2020, "value": 12}, {"year": 2021, "value": 9}]},
        "encoding": {
            "x": {"field": "year", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
        },
    }
    result = executor.execute(
        parent_chart_spec=spec,
        selected_operations=[
            {
                "operation": "select_data_range",
                "layer": "data",
                "intent": "focus recent years",
                "params": {"x_field": "year", "start": 2020, "end": 2021},
            }
        ],
        shift_magnitude="minor",
    )
    assert result.updated_chart_spec is not None
    transform = result.updated_chart_spec.get("transform", [])
    assert isinstance(transform, list) and transform
    filter_obj = transform[-1].get("filter") if isinstance(transform[-1], dict) else None
    assert isinstance(filter_obj, str)
    assert "datum['year'] >= 2020" in filter_obj
    assert "datum['year'] <= 2021" in filter_obj
    x_scale = result.updated_chart_spec.get("encoding", {}).get("x", {}).get("scale", {})
    assert isinstance(x_scale, dict)
    assert x_scale.get("domain") == [2020, 2021]


def test_nodec_fallback_text_when_all_ops_failed() -> None:
    node_c = NodeC()
    parent_spec = _sample_layered_spec()
    res = node_c.run(
        action="modify",
        operations=["change_title"],
        shift_magnitude="minor",
        selected_operations=[{"operation": "unknown_op", "layer": "text", "intent": "x"}],
        context={"chartSpec": parent_spec},
    )
    assert res["execution_mode"] == "fallback_text"
    assert res["updated_chart_spec"] == parent_spec


def test_nodec_rolls_back_when_validator_fails() -> None:
    node_c = NodeC()
    parent_spec = _sample_layered_spec()
    node_c.executor.execute = lambda **_: ExecutionResult(  # type: ignore[assignment]
        updated_chart_spec={"description": "invalid"},
        executed_operations=[{"operation": "change_title", "before": "a", "after": "b"}],
        operation_audit=[],
        layers_affected=["text"],
        variant_description="invalid result",
    )
    res = node_c.run(
        action="modify",
        operations=["change_title"],
        shift_magnitude="sig",
        selected_operations=[{"operation": "change_title", "layer": "text", "intent": "x"}],
        context={"chartSpec": parent_spec},
    )
    assert res["execution_mode"] == "node_rollback"
    assert res["updated_chart_spec"] == parent_spec


def test_spec_renderer_returns_data_url() -> None:
    renderer = SpecRenderer()
    data_url = renderer.to_data_url(_sample_layered_spec())
    assert isinstance(data_url, str)
    assert data_url.startswith("data:image/svg+xml;base64,")

