from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.offset_analyzer import OffsetAnalyzer
from app.main import app
from app.schemas.api_contract import TreeNode


client = TestClient(app)


def test_offset_analyzer_highest_values() -> None:
    analyzer = OffsetAnalyzer()
    nodes = [
        TreeNode(id="SRC", label="src", nodeType="neutral", offset="none"),
        TreeNode(id="V1", label="v1", nodeType="analyst", offset="sig"),
        TreeNode(id="V2", label="v2", nodeType="adverser", offset="major"),
    ]
    assert analyzer.highest_offset(nodes) == "major"
    assert analyzer.highest_path(nodes) == "SRC->V2 (major)"


def test_simulation_writes_run_snapshot() -> None:
    upload_res = client.post(
        "/api/upload-case",
        files={
            "chart_spec": ("chart_spec.json", b'{"mark":"bar","data":{"values":[]}}', "application/json"),
            "metadata": ("metadata.json", b'{"title":"snapshot case"}', "application/json"),
        },
    )
    assert upload_res.status_code == 200
    case_ref = upload_res.json()["caseRef"]

    payload = {
        "agentCount": 2,
        "agentCategories": ["Amplifier", "Adverser"],
        "description": "snapshot test",
        "topic": "science",
        "caseRef": case_ref,
    }
    res = client.post("/api/simulation/start", json=payload)
    assert res.status_code == 200

    run_dir = Path("storage/runs")
    files = sorted(run_dir.glob("*.json"))
    assert files, "expected at least one run snapshot"

    latest = files[-1].read_text(encoding="utf-8")
    assert "provenance_chain" in latest
    assert "rule_source" in latest

