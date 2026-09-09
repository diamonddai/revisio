from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_ok() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_upload_ok() -> None:
    res = client.post(
        "/api/upload",
        files={"file": ("demo.png", b"fake-image-content", "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "dataUrl" in data and data["dataUrl"].startswith("image/png;base64,")
    assert "url" in data and data["url"].startswith("/uploads/")


def test_upload_case_ok() -> None:
    res = client.post(
        "/api/upload-case",
        files={
            "chart_spec": ("chart_spec.json", b'{"mark":"bar","data":{"values":[]}}', "application/json"),
            "metadata": (
                "metadata.json",
                b'{"title":"demo chart","description":"from metadata"}',
                "application/json",
            ),
            "image": ("visualization.svg", b"<svg></svg>", "image/svg+xml"),
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["caseRef"].startswith("case-")
    assert data["chartSpecRef"].startswith("/cases/")
    assert data["metadataRef"].startswith("/cases/")
    assert data["imageRef"].startswith("/cases/")


def test_simulation_start_ok() -> None:
    upload_res = client.post(
        "/api/upload-case",
        files={
            "chart_spec": ("chart_spec.json", b'{"mark":"line","data":{"values":[]}}', "application/json"),
            "metadata": ("metadata.json", b'{"title":"source title","description":"source desc"}', "application/json"),
        },
    )
    assert upload_res.status_code == 200
    case_ref = upload_res.json()["caseRef"]

    payload = {
        "agentCount": 2,
        "agentCategories": ["Amplifier", "Analyst"],
        "agentProfiles": [
            {"role": "Bridger", "institution": "news"},
            {"role": "Extender", "institution": "research"},
        ],
        "maxDepth": 2,
        "mode": "adversarial",
        "description": "test description",
        "topic": "science",
        "caseRef": case_ref,
    }
    res = client.post("/api/simulation/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["tree"]["nodeCount"] >= 1
    assert data["tree"]["edgeCount"] == 2
    assert data["summary"]["agentCount"] == 2
    assert len(data["agentLog"]) >= 1
    assert data["tree"]["maxDepth"] <= 2
    nodes = data["tree"]["nodes"]
    assert any(node.get("institution") == "news" for node in nodes if node.get("id") != "SRC")
    assert any(node.get("role") == "Extender" for node in nodes if node.get("id") != "SRC")
    all_ops = [
        op
        for node in nodes
        if node.get("id") != "SRC"
        for op in (node.get("operations") or [])
        if isinstance(op, str)
    ]
    if all_ops:
        assert all(op.startswith(("DATA ", "TEXT ", "VISUAL ")) for op in all_ops)
    non_root = [node for node in nodes if node.get("id") != "SRC"]
    if non_root:
        assert any(
            isinstance(node.get("imageUrl"), str) and node["imageUrl"].startswith("data:image/")
            for node in non_root
        )

