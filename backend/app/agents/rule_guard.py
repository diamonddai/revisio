from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


VALID_ACTIONS = {"forward", "modify", "ignore"}
VALID_GAPS = {"resonance", "tension", "conflict", "noise"}
VALID_SHIFT = {"none", "minor", "sig", "major"}
SHIFT_ALIAS = {"significant": "sig"}


@dataclass
class GuardResult:
    action: str
    gap_type: str
    shift_magnitude: str
    operations: list[str]
    selected_operation_plan: list[dict[str, Any]]
    adjustments: list[str]


class RuleGuard:
    def __init__(self) -> None:
        self.max_operations_per_step = 5
        self.operation_layer: dict[str, str] = {}
        self.mutual_exclusive_pairs: list[tuple[str, str]] = []
        self._load_node3_schema()

    def _load_node3_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "config" / "node3_operation_schema_v1.yaml"
        if not schema_path.exists():
            return
        try:
            payload = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return

        limits = payload.get("limits")
        if isinstance(limits, dict):
            max_ops = limits.get("max_operations_per_step")
            if isinstance(max_ops, int) and max_ops > 0:
                self.max_operations_per_step = max_ops

        catalog = payload.get("operation_catalog")
        if isinstance(catalog, dict):
            for op_name, cfg in catalog.items():
                if not isinstance(op_name, str) or not isinstance(cfg, dict):
                    continue
                layer = cfg.get("layer")
                if isinstance(layer, str) and layer in {"data", "visual", "text"}:
                    self.operation_layer[op_name] = layer

        pairs = payload.get("mutual_exclusive_rules")
        if isinstance(pairs, list):
            parsed: list[tuple[str, str]] = []
            for pair in pairs:
                if (
                    isinstance(pair, list)
                    and len(pair) == 2
                    and isinstance(pair[0], str)
                    and isinstance(pair[1], str)
                ):
                    parsed.append((pair[0], pair[1]))
            self.mutual_exclusive_pairs = parsed

    def _sanitize_operation_plan(
        self,
        operation_plan: list[dict[str, Any]],
        allowed_ops: set[str],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        adjustments: list[str] = []
        normalized: list[dict[str, Any]] = []

        for item in operation_plan:
            if not isinstance(item, dict):
                adjustments.append("selected_operation_plan_item_invalid")
                continue
            op = item.get("operation")
            if not isinstance(op, str):
                adjustments.append("selected_operation_plan_missing_operation")
                continue
            if op not in allowed_ops:
                adjustments.append("selected_operation_plan_filtered_by_whitelist")
                continue

            expected_layer = self.operation_layer.get(op)
            layer = item.get("layer")
            safe_layer = expected_layer if expected_layer else "text"
            if isinstance(layer, str) and layer in {"data", "visual", "text"}:
                safe_layer = layer
            if expected_layer and safe_layer != expected_layer:
                safe_layer = expected_layer
                adjustments.append("selected_operation_plan_layer_normalized")

            intent = item.get("intent")
            safe_intent = intent if isinstance(intent, str) else ""
            params = item.get("params")
            safe_params = params if isinstance(params, dict) else {}
            normalized.append(
                {
                    "operation": op,
                    "layer": safe_layer,
                    "intent": safe_intent,
                    "params": safe_params,
                }
            )

        if self.mutual_exclusive_pairs:
            seen_ops: set[str] = set()
            filtered: list[dict[str, Any]] = []
            for item in normalized:
                op = item["operation"]
                conflict = False
                for left, right in self.mutual_exclusive_pairs:
                    if op == left and right in seen_ops:
                        conflict = True
                        break
                    if op == right and left in seen_ops:
                        conflict = True
                        break
                if conflict:
                    adjustments.append("selected_operation_plan_mutual_exclusive_filtered")
                    continue
                seen_ops.add(op)
                filtered.append(item)
            normalized = filtered

        if len(normalized) > self.max_operations_per_step:
            normalized = normalized[: self.max_operations_per_step]
            adjustments.append("selected_operation_plan_truncated")

        return normalized, adjustments

    def sanitize(
        self,
        action: str,
        gap_type: str,
        shift_magnitude: str,
        operations: list[str],
        whitelist: list[str],
        confidence: float,
        operation_plan: list[dict[str, Any]] | None = None,
    ) -> GuardResult:
        adjustments: list[str] = []

        safe_action = action if action in VALID_ACTIONS else "ignore"
        if safe_action != action:
            adjustments.append("action->ignore")

        safe_gap = gap_type if gap_type in VALID_GAPS else "noise"
        if safe_gap != gap_type:
            adjustments.append("gap_type->noise")

        normalized_shift = SHIFT_ALIAS.get(shift_magnitude, shift_magnitude)
        safe_shift = normalized_shift if normalized_shift in VALID_SHIFT else "minor"
        if safe_shift != shift_magnitude:
            adjustments.append("shift_magnitude_normalized")

        safe_ops = [op for op in operations if op in whitelist]
        if len(safe_ops) != len(operations):
            adjustments.append("operation_whitelist_filtered")
        if len(safe_ops) > self.max_operations_per_step:
            safe_ops = safe_ops[: self.max_operations_per_step]
            adjustments.append("operation_list_truncated")

        # Low confidence policy: downshift and avoid aggressive modify.
        if confidence < 0.55 and safe_action == "modify":
            safe_action = "forward"
            if safe_shift == "major":
                safe_shift = "sig"
            adjustments.append("low_confidence_downgrade")

        safe_plan: list[dict[str, Any]]
        plan_adjustments: list[str]
        safe_plan, plan_adjustments = self._sanitize_operation_plan(operation_plan or [], set(safe_ops))
        adjustments.extend(plan_adjustments)
        if not safe_plan and safe_ops:
            safe_plan = [
                {
                    "operation": op,
                    "layer": self.operation_layer.get(op, "text"),
                    "intent": "",
                    "params": {},
                }
                for op in safe_ops
            ]

        return GuardResult(
            action=safe_action,
            gap_type=safe_gap,
            shift_magnitude=safe_shift,
            operations=safe_ops,
            selected_operation_plan=safe_plan,
            adjustments=adjustments,
        )

