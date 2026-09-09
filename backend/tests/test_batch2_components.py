from app.agents.llm_client import LLMClient
from app.agents.rule_guard import RuleGuard
from app.agents.taxonomy_adapter import TaxonomyAdapter
from app.graph.workflow import NodeA, NodeB


def test_taxonomy_adapter_fallback_loaded() -> None:
    adapter = TaxonomyAdapter(use_taxonomy=False)
    persona = adapter.pick_persona("Amplifier", seed=1)
    assert adapter.rule_source == "fallback"
    assert adapter.rule_version == "v1"
    assert persona["category"] == "Amplifier"
    assert adapter.get_operation_whitelist(persona)


def test_taxonomy_adapter_v3_loaded_when_enabled() -> None:
    adapter = TaxonomyAdapter(use_taxonomy=True)
    persona = adapter.pick_persona("Analyst", seed=1)
    assert adapter.rule_source == "taxonomy_v3"
    assert adapter.rule_version == "v3"
    assert persona["role"] in {"Extender", "Analyst"}
    assert "change_title" in adapter.get_operation_whitelist(persona)


def test_rule_guard_normalize_shift_and_whitelist() -> None:
    guard = RuleGuard()
    result = guard.sanitize(
        action="modify",
        gap_type="conflict",
        shift_magnitude="significant",
        operations=["change_title", "UNSAFE op"],
        whitelist=["change_title"],
        confidence=0.8,
    )
    assert result.shift_magnitude == "sig"
    assert result.operations == ["change_title"]
    assert "operation_whitelist_filtered" in result.adjustments


def test_node_workflow_conflict_to_modify() -> None:
    persona = {"category": "Adverser"}
    llm_client = LLMClient(enabled=False)
    node_a = NodeA(llm_client=llm_client)
    node_b = NodeB(llm_client=llm_client)
    a = node_a.run(persona, context={})
    b = node_b.run(
        gap_type=a["gap_type"],
        confidence=a["confidence"],
        whitelist=["change_title", "add_annotation"],
        shift_prior="major",
    )
    assert b["gap_type"] == "conflict"
    assert b["action"] in {"modify", "forward"}
    assert b["shift_magnitude"] in {"sig", "major"}
    assert "selected_operations" in b


def test_rule_guard_selected_operation_plan_layer_and_mutual_exclusive() -> None:
    guard = RuleGuard()
    result = guard.sanitize(
        action="modify",
        gap_type="conflict",
        shift_magnitude="major",
        operations=["change_title", "add_annotation", "change_annotation"],
        whitelist=["change_title", "add_annotation", "change_annotation"],
        confidence=0.9,
        operation_plan=[
            {"operation": "change_title", "layer": "visual", "intent": "reframe headline", "params": {"max_line_chars": 32}},
            {"operation": "add_annotation", "layer": "text", "intent": "add cue", "params": {"include_trendline": False}},
            {"operation": "change_annotation", "layer": "text", "intent": "rewrite cue"},
        ],
    )
    # change_title layer is normalized by schema (text).
    assert result.selected_operation_plan[0]["layer"] == "text"
    # add_annotation and change_annotation are mutually exclusive per schema.
    ops = [item["operation"] for item in result.selected_operation_plan]
    assert not ("add_annotation" in ops and "change_annotation" in ops)
    assert isinstance(result.selected_operation_plan[0].get("params"), dict)


def test_amplifier_media_strategy_forces_change_color() -> None:
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="tension",
        persona={"category": "Amplifier"},
        context={
            "institution": "新闻媒体",
            "topic": "climate",
            "description": "temperature anomaly",
            "chartSpec": {
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
                "data": {"values": [{"year": 2010, "value": 0.2}, {"year": 2015, "value": 0.5}]},
            },
        },
        whitelist=["change_title", "change_color", "add_annotation", "simplify_axis"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "change_color" in ops
    color_item = next((item for item in result.get("selected_operations", []) if item.get("operation") == "change_color"), {})
    assert color_item.get("params", {}).get("palette_style") == "social_contrast"


def test_amplifier_deforestation_does_not_force_add_background() -> None:
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="tension",
        persona={"category": "Amplifier"},
        context={
            "institution": "新闻媒体",
            "topic": "deforestation",
            "description": "amazon rates",
            "chartSpec": {
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
                "data": {"values": [{"year": 2010, "value": 0.2}, {"year": 2015, "value": 0.5}]},
            },
        },
        whitelist=["change_title", "change_color", "add_annotation", "simplify_axis", "add_background"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "add_background" not in ops


def test_amplifier_uses_change_annotation_when_annotation_exists() -> None:
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="tension",
        persona={"category": "Amplifier"},
        context={
            "institution": "新闻媒体",
            "topic": "climate",
            "description": "temperature anomaly",
            "chartSpec": {
                "layer": [
                    {"mark": {"type": "text", "text": "existing annotation"}},
                    {
                        "mark": {"type": "line"},
                        "encoding": {
                            "x": {"field": "year", "type": "quantitative"},
                            "y": {"field": "value", "type": "quantitative"},
                        },
                        "data": {"values": [{"year": 2010, "value": 0.2}, {"year": 2015, "value": 0.5}]},
                    },
                ]
            },
        },
        whitelist=["change_title", "change_color", "change_annotation", "add_annotation", "simplify_axis"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "change_annotation" in ops


def test_bridger_strategy_avoids_simplify_axis_and_change_title() -> None:
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="resonance",
        persona={"category": "Bridger"},
        context={
            "institution": "public brief",
            "topic": "climate",
            "description": "annual temperature trend",
            "chartSpec": {
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            },
        },
        whitelist=["change_title", "add_annotation", "change_color", "simplify_axis"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "simplify_axis" not in ops
    assert "change_title" not in ops


def test_bridger_strategy_only_keeps_allowed_ops() -> None:
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="resonance",
        persona={"category": "Bridger"},
        context={
            "institution": "authority bulletin",
            "topic": "climate",
            "description": "temperature series",
            "chartSpec": {
                "mark": {"type": "bar"},
                "encoding": {
                    "x": {"field": "year", "type": "quantitative"},
                    "y": {"field": "value", "type": "quantitative"},
                },
            },
        },
        whitelist=["change_title", "add_annotation", "change_color", "simplify_axis"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert all(op in ("change_color", "change_chart_type") for op in ops)
    assert "change_color" in ops


def test_bridger_data_platform_includes_change_chart_type() -> None:
    """Bridger on a 3rd-party data platform can change chart type (e.g. bar → line)."""
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="resonance",
        persona={"category": "Bridger"},
        context={
            "institution": "third-party data platform",
            "topic": "climate",
            "description": "annual temperature anomaly",
            "chartSpec": {
                "mark": {"type": "bar"},
                "encoding": {
                    "x": {"field": "year", "type": "temporal"},
                    "y": {"field": "anomaly", "type": "quantitative"},
                },
            },
        },
        whitelist=["change_color", "change_chart_type", "add_annotation", "change_title"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "change_chart_type" in ops
    chart_type_item = [
        item for item in result.get("selected_operations", [])
        if item.get("operation") == "change_chart_type"
    ]
    assert len(chart_type_item) == 1
    assert "area" in chart_type_item[0].get("intent", "").lower()


def test_bridger_non_data_platform_includes_area_chart_type() -> None:
    """Bridger on authority/news platform now always includes change_chart_type (area)."""
    llm_client = LLMClient(enabled=False)
    result = llm_client.propose_strategy(
        gap_type="resonance",
        persona={"category": "Bridger"},
        context={
            "institution": "government report",
            "topic": "unemployment",
            "description": "monthly unemployment rate",
            "chartSpec": {
                "mark": {"type": "bar"},
                "encoding": {
                    "x": {"field": "month", "type": "ordinal"},
                    "y": {"field": "rate", "type": "quantitative"},
                },
            },
        },
        whitelist=["change_color", "change_chart_type"],
        shift_prior="minor",
    )
    ops = [item.get("operation") for item in result.get("selected_operations", [])]
    assert "change_chart_type" in ops
    chart_type_item = [
        item for item in result.get("selected_operations", [])
        if item.get("operation") == "change_chart_type"
    ]
    assert "area" in chart_type_item[0].get("intent", "").lower()

