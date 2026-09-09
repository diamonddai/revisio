from app.services.simulation_service import SimulationService


def test_simulation_multilayer_without_data_fallback() -> None:
    service = SimulationService()
    req = {
        "agentCount": 4,
        "agentCategories": ["Amplifier", "Analyst", "Bridger", "Adverser"],
        "maxDepth": 1,
        "mode": "conservative",
        "agentProfiles": [
            {"role": "Bridger", "institution": "gov"},
            {"role": "Extender", "institution": "lab"},
            {"role": "Adverser", "institution": "social"},
            {"role": "Amplifier", "institution": "media"},
        ],
        "topic": "science",
    }
    from app.schemas.api_contract import SimulationStartRequest

    res = service.run_sync(SimulationStartRequest(**req))
    assert res.ok is True
    assert res.tree is not None
    assert res.tree.maxDepth >= 1
    assert res.tree.maxDepth <= 1
    assert res.tree.edgeCount <= 4
    # no imageRef provided: keep None and rely on frontend input contract.
    assert res.tree.nodes[0].imageUrl is None
    non_root_nodes = [n for n in res.tree.nodes if n.id != "SRC"]
    assert non_root_nodes and non_root_nodes[0].institution == "media"
    assert res.pathOffsetTrend is not None and len(res.pathOffsetTrend) >= 1


def test_simulation_agent_pool_spreads_across_depth_and_keeps_extender_role() -> None:
    service = SimulationService()
    req = {
        "agentCount": 5,
        "agentCategories": ["Amplifier", "Analyst", "Bridger", "Adverser"],
        "maxDepth": 3,
        "mode": "neutral",
        "agentProfiles": [
            {"role": "Bridger", "institution": "gov"},
            {"role": "Extender", "institution": "lab"},
            {"role": "Adverser", "institution": "social"},
            {"role": "Amplifier", "institution": "media"},
            {"role": "Bridger", "institution": "ngo"},
        ],
        "topic": "science",
    }
    from app.schemas.api_contract import SimulationStartRequest

    res = service.run_sync(SimulationStartRequest(**req))
    assert res.ok is True
    assert res.tree is not None
    assert res.tree.edgeCount == 5
    assert res.tree.maxDepth <= 3
    non_root_nodes = [n for n in res.tree.nodes if n.id != "SRC"]
    assert len(non_root_nodes) == 5
    assert non_root_nodes[0].role == "Amplifier"
    assert any(n.role == "Extender" for n in non_root_nodes)


def test_format_operations_for_ui_prefers_operation_audit_records() -> None:
    formatted = SimulationService._format_operations_for_ui(
        selected_operation_plan=[{"operation": "change_color", "layer": "visual", "intent": "vivid"}],
        operation_names=["change_color"],
        operation_audit=[
            {
                "operation": "change_color",
                "status": "applied",
                "error": "",
                "params": {"intent": "vivid"},
            },
            {
                "operation": "change_title",
                "status": "skipped",
                "error": "rule_guard_blocked",
                "params": {"intent": "title: test"},
            },
        ],
    )
    assert any("change_color" in item and "[" not in item for item in formatted)
    assert any("[skipped: rule_guard_blocked]" in item for item in formatted)

