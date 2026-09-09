from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunStorage:
    def __init__(self, run_dir: Path | None = None) -> None:
        self.run_dir = run_dir or Path("storage/runs")
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, run_id: str, payload: dict[str, Any]) -> str:
        target = self.run_dir / f"{run_id}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)

