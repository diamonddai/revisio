from __future__ import annotations

import base64
import json
from pathlib import Path
from uuid import uuid4


class UploadService:
    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or Path("storage/uploads")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.case_storage_dir = Path("storage/cases")
        self.case_storage_dir.mkdir(parents=True, exist_ok=True)

    def store_and_build_payload(self, filename: str, content: bytes, content_type: str) -> dict[str, str]:
        suffix = Path(filename).suffix or ".bin"
        target_name = f"{uuid4().hex}{suffix}"
        target_path = self.storage_dir / target_name
        target_path.write_bytes(content)

        b64 = base64.b64encode(content).decode("utf-8")
        return {
            "url": f"/uploads/{target_name}",
            "dataUrl": f"{content_type};base64,{b64}",
        }

    def store_case_files(
        self,
        chart_spec_filename: str,
        chart_spec_content: bytes,
        metadata_filename: str,
        metadata_content: bytes,
        data_filename: str | None = None,
        data_content: bytes | None = None,
        image_filename: str | None = None,
        image_content: bytes | None = None,
    ) -> dict[str, str | None]:
        case_ref = f"case-{uuid4().hex[:8]}"
        case_dir = self.case_storage_dir / case_ref
        case_dir.mkdir(parents=True, exist_ok=False)

        chart_spec_name = "chart_spec.json"
        metadata_name = "metadata.json"
        chart_spec_path = case_dir / chart_spec_name
        metadata_path = case_dir / metadata_name
        chart_spec_path.write_bytes(chart_spec_content)
        metadata_path.write_bytes(metadata_content)

        # Validate uploaded JSON early to avoid invalid case data entering simulation.
        json.loads(chart_spec_content.decode("utf-8"))
        json.loads(metadata_content.decode("utf-8"))

        payload: dict[str, str | None] = {
            "caseRef": case_ref,
            "chartSpecRef": f"/cases/{case_ref}/{chart_spec_name}",
            "metadataRef": f"/cases/{case_ref}/{metadata_name}",
            "dataRef": None,
            "imageRef": None,
        }
        if data_filename and data_content is not None:
            data_name = self._safe_filename(data_filename, default_name="data.csv")
            (case_dir / data_name).write_bytes(data_content)
            payload["dataRef"] = f"/cases/{case_ref}/{data_name}"
        if image_filename and image_content is not None:
            image_suffix = Path(image_filename).suffix if image_filename else ""
            image_name = f"visualization{image_suffix}" if image_suffix else "visualization.bin"
            (case_dir / image_name).write_bytes(image_content)
            payload["imageRef"] = f"/cases/{case_ref}/{image_name}"
        return payload

    @staticmethod
    def _safe_filename(filename: str | None, default_name: str) -> str:
        if not filename:
            return default_name
        return Path(filename).name or default_name

