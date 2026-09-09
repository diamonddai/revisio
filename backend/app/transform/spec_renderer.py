from __future__ import annotations

import base64
import hashlib
import html
import json
from typing import Any


class SpecRenderer:
    """
    Render chart spec to image data URL.

    - Prefer Vega-Lite SVG rendering if optional dependency is available.
    - Fallback to deterministic SVG summary so each node can still display
      an image that reflects spec changes.
    """

    def __init__(self) -> None:
        try:
            import vl_convert as vlc  # type: ignore

            self._vlc = vlc
        except Exception:
            self._vlc = None

    def to_data_url(self, chart_spec: dict[str, Any] | None) -> str | None:
        if not isinstance(chart_spec, dict):
            return None
        if self._vlc is not None:
            try:
                svg = self._vlc.vegalite_to_svg(chart_spec)
                if isinstance(svg, str) and svg.strip():
                    return self._encode_svg(svg)
            except Exception:
                pass
        return self._encode_svg(self._fallback_svg(chart_spec))

    @staticmethod
    def _encode_svg(svg: str) -> str:
        raw = svg.encode("utf-8")
        return f"data:image/svg+xml;base64,{base64.b64encode(raw).decode('ascii')}"

    @staticmethod
    def _fallback_svg(spec: dict[str, Any]) -> str:
        title = spec.get("title", "Untitled")
        if isinstance(title, dict):
            title = title.get("text", "Untitled")
        title_text = str(title)[:72]
        layer_count = len(spec.get("layer", [])) if isinstance(spec.get("layer"), list) else 0
        transform_count = len(spec.get("transform", [])) if isinstance(spec.get("transform"), list) else 0
        mark_type = ""
        if isinstance(spec.get("mark"), dict):
            mark_type = str(spec["mark"].get("type", ""))
        spec_hash = hashlib.sha1(
            json.dumps(spec, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:8]
        return (
            "<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450'>"
            "<rect width='100%' height='100%' fill='#ffffff' stroke='#d1d5db'/>"
            "<text x='24' y='56' font-size='32' fill='#111827' font-family='Arial'>"
            f"{html.escape(title_text)}"
            "</text>"
            "<text x='24' y='100' font-size='20' fill='#4b5563' font-family='Arial'>"
            f"layer={layer_count} transform={transform_count} mark={html.escape(mark_type)}"
            "</text>"
            "<text x='24' y='134' font-size='17' fill='#6b7280' font-family='Arial'>"
            f"spec:{spec_hash}"
            "</text>"
            "</svg>"
        )

