from copy import deepcopy

from app.agents.llm_client import LLMClient
from app.graph.workflow import NodeC
from app.schemas.api_contract import SimulationStartRequest
from app.services.simulation_service import SimulationService
from app.transform.framing_reconstructor import (
    FramingReconstructor,
    _has_baseline_layer,
    _has_dual_y_axes,
    _primary_channel,
    _title_text,
    _walk_encoding_channels,
)


def _trend_spec() -> dict:
    values = []
    series = [5, 5, 5, 6, 5, 4, 4, 4, 5, 8, 12, 14, 13, 10, 7, 5, 4, 4, 4, 4]
    for idx, rate in enumerate(series):
        values.append({"year": 2006 + idx, "rate": rate})
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": "Civilian unemployment rate", "fontSize": 18},
        "width": 640,
        "height": 360,
        "data": {"values": values},
        "layer": [
            {
                "mark": {"type": "line", "color": "#005d9e"},
                "encoding": {
                    "x": {"field": "year", "type": "ordinal"},
                    "y": {"field": "rate", "type": "quantitative", "scale": {"domain": [0, 20]}},
                },
            }
        ],
    }


def test_amplifier_chain_compounds_on_parent_window() -> None:
    spec = _trend_spec()
    source_n = len(spec["data"]["values"])
    recon = FramingReconstructor()
    titles: list[str] = []
    lengths: list[int] = []
    for _ in range(3):
        result = recon.reconstruct(spec, role="Amplifier", shift_magnitude="sig")
        assert result is not None and result.ok
        spec = result.spec
        assert spec is not None
        lengths.append(len(spec["data"]["values"]))
        titles.append(_title_text(spec))
    assert lengths[0] < source_n
    assert lengths[2] <= lengths[0]
    assert len(set(titles)) == 3


def test_extender_keeps_incoming_window_and_metric() -> None:
    parent = _trend_spec()
    cropped = FramingReconstructor().reconstruct(parent, role="Amplifier", shift_magnitude="sig")
    assert cropped is not None and cropped.ok
    extender = FramingReconstructor().reconstruct(cropped.spec, role="Extender", shift_magnitude="sig")
    assert extender is not None and extender.ok
    assert len(extender.spec["data"]["values"]) == len(cropped.spec["data"]["values"])
    assert _has_baseline_layer(extender.spec)
    assert "unemployment" in _title_text(extender.spec).lower() or "rate" in _title_text(extender.spec).lower()


def test_adverser_does_not_restore_source_after_amplifier() -> None:
    spec = _trend_spec()
    source_n = len(spec["data"]["values"])
    amp = FramingReconstructor().reconstruct(spec, role="Amplifier", shift_magnitude="sig")
    assert amp is not None and amp.ok
    adv = FramingReconstructor().reconstruct(amp.spec, role="Adverser", shift_magnitude="major")
    assert adv is not None and adv.ok
    n_adv = len(adv.spec["data"]["values"])
    assert n_adv <= len(amp.spec["data"]["values"])
    assert n_adv < source_n


def test_color_only_candidate_fails_verification() -> None:
    parent = _trend_spec()
    recon = FramingReconstructor()
    contract = recon.build_contract(parent, "Adverser", "conflict", "", {})
    assert contract is not None
    color_only = deepcopy(parent)
    color_only["layer"][0]["mark"]["color"] = "#E53935"
    ok, errors = recon.verify_contract(parent, color_only, contract)
    assert ok is False


def test_node_c_amplifier_uses_reconstruct_mode() -> None:
    node_c = NodeC()
    result = node_c.run(
        action="modify",
        operations=["change_color"],
        shift_magnitude="sig",
        selected_operations=[{"operation": "change_color", "intent": "red"}],
        context={
            "chartSpec": _trend_spec(),
            "persona": {"category": "Amplifier"},
            "institution": "News media",
            "depth": 1,
        },
    )
    assert result["execution_mode"].startswith("reconstructed")
    assert result["framing_contract"]["role"] == "Amplifier"
    assert len(result["updated_chart_spec"]["data"]["values"]) < len(_trend_spec()["data"]["values"])


def test_reconstructed_bar_chart_keeps_axes_and_zero_baseline() -> None:
    from pathlib import Path
    import json
    import vl_convert as vlc

    src = json.loads(Path("/Users/dorine/framing/framing/data/04_amazon_deforestation/chart_spec.json").read_text())
    result = FramingReconstructor().reconstruct(src, role="Amplifier", shift_magnitude="sig")
    assert result is not None and result.ok and result.spec is not None
    y_enc = result.spec["layer"][0]["encoding"]["y"]
    assert y_enc["scale"]["domain"][0] == 0
    for item in result.spec["layer"][1:]:
        encoding = item.get("encoding") or {}
        for channel in encoding.values():
            if isinstance(channel, dict):
                assert channel.get("axis", "missing") is not None
    svg = vlc.vegalite_to_svg(result.spec)
    assert "role-axis" in svg
    assert "Rates" in svg


def test_covid_fold_chart_keeps_transform_and_sane_height() -> None:
    from pathlib import Path
    import json
    import vl_convert as vlc

    src = json.loads(Path("/Users/dorine/framing/framing/data/06_COVID_excess_deaths/chart_spec.json").read_text())
    result = FramingReconstructor().reconstruct(src, role="Amplifier", shift_magnitude="sig")
    assert result is not None and result.ok and result.spec is not None
    fold_kept = False
    for layer in result.spec.get("layer") or []:
        for transform in layer.get("transform") or []:
            if isinstance(transform, dict) and "fold" in transform:
                fold_kept = True
    assert fold_kept
    y_domain = result.spec["layer"][0]["encoding"]["y"]["scale"]["domain"]
    assert y_domain[1] >= 15000
    svg = vlc.vegalite_to_svg(result.spec)
    height = float(__import__("re").search(r'height="([\d.]+)"', svg[:400]).group(1))
    assert height < 2000
    assert 'aria-roledescription="bar"' in svg


def test_thinking_payload_can_be_enabled() -> None:
    client_obj = LLMClient(enabled=False)
    client_obj.model = "deepseek-v4-pro"
    client_obj.base_url = "https://api.deepseek.com/v1"
    off = client_obj._with_provider_payload({"model": client_obj.model})
    on = client_obj._with_provider_payload({"model": client_obj.model}, thinking=True)
    assert off["thinking"]["type"] == "disabled"
    assert on["thinking"]["type"] == "enabled"


def test_ordered_profiles_form_a_spine_when_they_fit_max_depth() -> None:
    service = SimulationService()
    service.llm_client.enabled = False
    res = service.run_sync(
        SimulationStartRequest(
            agentCount=3,
            agentCategories=["Amplifier", "Analyst", "Adverser"],
            maxDepth=3,
            mode="neutral",
            topic="science",
            agentProfiles=[
                {"role": "Amplifier", "institution": "News media"},
                {"role": "Extender", "institution": "Research institution"},
                {"role": "Adverser", "institution": "Social media"},
            ],
        )
    )
    assert res.ok is True
    assert res.tree is not None
    assert res.tree.maxDepth == 3
    assert res.tree.edgeCount == 3
    by_id = {edge.id: edge for edge in res.tree.edges}
    assert by_id["e1"].source == "SRC"
    assert by_id["e1"].target == "V1"
    assert by_id["e2"].source == "V1"
    assert by_id["e2"].target == "V2"
    assert by_id["e3"].source == "V2"
    assert by_id["e3"].target == "V3"


def test_adverser_prefers_recent_window_on_long_warming_series() -> None:
    from pathlib import Path
    import json

    src = json.loads(Path("/Users/dorine/framing/framing/data/01_global_temperature/chart_spec.json").read_text())
    contract = FramingReconstructor().build_contract(
        src, "Adverser", "conflict", "", {"description": src["title"]["text"]}
    )
    assert contract is not None
    assert float(contract.evidence_end) >= 2000


def test_extender_does_not_add_a_third_y_axis_on_dual_axis_chart() -> None:
    from pathlib import Path
    import json

    src = json.loads(Path("/Users/dorine/framing/framing/data/01_global_temperature/chart_spec.json").read_text())
    result = FramingReconstructor().reconstruct(src, role="Extender", shift_magnitude="sig")
    assert result is not None and result.ok and result.spec is not None
    y_orients = []
    for item in result.spec.get("layer") or []:
        enc = (item.get("encoding") or {}).get("y") if isinstance(item.get("encoding"), dict) else None
        if not isinstance(enc, dict):
            continue
        assert enc.get("field") != "revisio_baseline"
        axis = enc.get("axis")
        if isinstance(axis, dict):
            y_orients.append(str(axis.get("orient") or "left"))
    assert "right" in y_orients
    assert _has_baseline_layer(result.spec)
    left = result.spec["layer"][0]
    if "layer" in left:
        left_domain = left["layer"][0]["encoding"]["y"]["scale"]["domain"]
        right_domain = result.spec["layer"][1]["encoding"]["y"]["scale"]["domain"]
    else:
        left_domain = left["encoding"]["y"]["scale"]["domain"]
        right_domain = result.spec["layer"][1]["encoding"]["y"]["scale"]["domain"]
    assert left_domain == [-1, 1.5]
    assert right_domain == [-1.8, 2.7]


def _year_span(spec: dict) -> tuple[float, float, float]:
    values = (spec.get("data") or {}).get("values") or []
    years = [float(row["year"]) for row in values if isinstance(row.get("year"), (int, float))]
    ys = [float(row["anomaly_c"]) for row in values if isinstance(row.get("anomaly_c"), (int, float))]
    return min(years), max(years), max(ys)


def test_amplifier_chain_keeps_peak_and_crops_left() -> None:
    from pathlib import Path
    import json

    src = json.loads(Path("/Users/dorine/framing/framing/data/01_global_temperature/chart_spec.json").read_text())
    rec = FramingReconstructor()
    first = rec.reconstruct(src, role="Amplifier", shift_magnitude="minor")
    second = rec.reconstruct(first.spec, role="Amplifier", shift_magnitude="sig")
    third = rec.reconstruct(second.spec, role="Amplifier", shift_magnitude="major")
    assert first.ok and second.ok and third.ok
    s1, e1, m1 = _year_span(first.spec)
    s2, e2, m2 = _year_span(second.spec)
    s3, e3, m3 = _year_span(third.spec)
    assert e1 >= 2020 and e2 >= 2020 and e3 >= 2020
    assert s2 > s1
    assert s3 > s2
    assert m2 >= 1.0 and m3 >= 1.0
    y_enc = _primary_channel(third.spec, "y")
    left_domain = y_enc["scale"]["domain"]
    assert left_domain[0] > 0.2
    assert left_domain[1] <= m3 + 0.55
    assert left_domain[1] >= m3
    mark_types = []
    def _marks(node):
        if not isinstance(node, dict):
            return
        mark = node.get("mark")
        if isinstance(mark, dict) and mark.get("opacity") != 0 and mark.get("size") != 0:
            mark_types.append(mark.get("type"))
        elif isinstance(mark, str):
            mark_types.append(mark)
        for inner in node.get("layer") or []:
            _marks(inner)
    _marks(third.spec)
    assert "area" in mark_types or "line" in mark_types
    y_axes = [
        enc.get("axis")
        for channel, enc in _walk_encoding_channels(third.spec)
        if channel == "y" and isinstance(enc.get("axis"), dict)
    ]
    assert len(y_axes) == 1
    assert not _has_dual_y_axes(third.spec)
    assert y_axes[0].get("orient", "left") == "left"
    area_y2 = None
    def _find_area_y2(node):
        nonlocal area_y2
        if not isinstance(node, dict):
            return
        mark = node.get("mark")
        if mark == "area" or (isinstance(mark, dict) and mark.get("type") == "area"):
            y2 = (node.get("encoding") or {}).get("y2")
            if isinstance(y2, dict):
                area_y2 = y2.get("datum")
        for inner in node.get("layer") or []:
            _find_area_y2(inner)
    _find_area_y2(third.spec)
    assert area_y2 == left_domain[0]
    title3 = third.spec["title"]["text"] if isinstance(third.spec.get("title"), dict) else str(third.spec.get("title"))
    assert "breaking" in title3.lower()
    assert "still climbing" not in title3.lower()
    assert "still the number" not in title3.lower()


def test_extender_chain_adds_distinct_mean_lines() -> None:
    from pathlib import Path
    import json

    from app.transform.framing_reconstructor import _extender_rule_count, _has_invented_y_fields

    src = json.loads(Path("/Users/dorine/framing/framing/data/01_global_temperature/chart_spec.json").read_text())
    rec = FramingReconstructor()
    first = rec.reconstruct(src, role="Extender", shift_magnitude="minor")
    second = rec.reconstruct(first.spec, role="Extender", shift_magnitude="sig")
    third = rec.reconstruct(second.spec, role="Extender", shift_magnitude="major")
    assert first.ok and second.ok and third.ok
    assert _year_span(first.spec)[:2] == (1850, 2025)
    assert _year_span(third.spec)[:2] == (1850, 2025)
    titles = [_title_text(first.spec), _title_text(second.spec), _title_text(third.spec)]
    assert len(set(titles)) == 3
    for title in titles:
        lower = title.lower()
        assert "years that followed" not in lower
        assert "after the 2024 peak" not in lower
        assert "mean" in lower
    datums: list[float] = []

    def _collect(node) -> None:
        if not isinstance(node, dict):
            return
        if "revisio extender" in str(node.get("description") or "").lower():
            y_enc = (node.get("encoding") or {}).get("y")
            if isinstance(y_enc, dict) and isinstance(y_enc.get("datum"), (int, float)):
                datums.append(float(y_enc["datum"]))
        for inner in node.get("layer") or []:
            _collect(inner)

    _collect(third.spec)
    assert _extender_rule_count(third.spec) >= 3
    assert len({round(val, 3) for val in datums}) >= 3
    assert not _has_invented_y_fields(third.spec)
    assert "right" in [
        str((enc.get("axis") or {}).get("orient") or "left")
        for channel, enc in _walk_encoding_channels(third.spec)
        if channel == "y" and isinstance(enc.get("axis"), dict)
    ]

