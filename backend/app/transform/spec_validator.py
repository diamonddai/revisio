from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


class SpecValidator:
    """Lightweight Vega-Lite structural validator for Node3 rollback decisions."""

    def validate(self, spec: dict[str, Any] | None) -> ValidationResult:
        if spec is None:
            return ValidationResult(ok=False, errors=["spec_missing"])
        if not isinstance(spec, dict):
            return ValidationResult(ok=False, errors=["spec_not_object"])

        errors: list[str] = []
        if "mark" not in spec and "layer" not in spec:
            errors.append("missing_mark_or_layer")

        layer = spec.get("layer")
        if layer is not None:
            if not isinstance(layer, list):
                errors.append("layer_not_list")
            elif len(layer) == 0:
                errors.append("layer_empty")

        transform = spec.get("transform")
        if transform is not None:
            if not isinstance(transform, list):
                errors.append("transform_not_list")
            elif any(not isinstance(item, dict) for item in transform):
                errors.append("transform_item_not_object")

        encoding = spec.get("encoding")
        if encoding is not None and not isinstance(encoding, dict):
            errors.append("encoding_not_object")

        # Semantic checks (MVP): encoding channel coherence and axis/legend consistency.
        errors.extend(self._semantic_checks(spec))

        return ValidationResult(ok=len(errors) == 0, errors=errors)

    def _semantic_checks(self, spec: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        units: list[dict[str, Any]] = [spec]
        layer = spec.get("layer")
        if isinstance(layer, list):
            units = [item for item in layer if isinstance(item, dict)]

        for unit in units:
            encoding = unit.get("encoding")
            if encoding is None:
                continue
            if not isinstance(encoding, dict):
                errors.append("encoding_not_object")
                continue

            has_x = isinstance(encoding.get("x"), dict)
            has_y = isinstance(encoding.get("y"), dict)

            for channel, channel_def in encoding.items():
                if not isinstance(channel_def, dict):
                    errors.append(f"encoding_channel_not_object:{channel}")
                    continue
                if channel in {"x2"} and not has_x:
                    errors.append("x2_without_x")
                if channel in {"y2"} and not has_y:
                    errors.append("y2_without_y")

                if not any(key in channel_def for key in ("field", "value", "datum")):
                    errors.append(f"encoding_channel_missing_field_or_value:{channel}")

                axis = channel_def.get("axis")
                if axis is not None and channel not in {"x", "y"}:
                    errors.append(f"axis_on_non_positional_channel:{channel}")

                legend = channel_def.get("legend")
                if legend is not None and channel in {"x", "x2", "y", "y2"}:
                    errors.append(f"legend_on_positional_channel:{channel}")

                scale = channel_def.get("scale")
                if isinstance(scale, dict):
                    domain = scale.get("domain")
                    if (
                        isinstance(domain, list)
                        and len(domain) == 2
                        and all(isinstance(v, (int, float)) for v in domain)
                        and float(domain[0]) > float(domain[1])
                    ):
                        errors.append(f"scale_domain_reversed:{channel}")

        return errors

