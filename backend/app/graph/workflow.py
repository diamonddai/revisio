from __future__ import annotations

import random
from typing import Any

from app.agents.llm_client import LLMClient
from app.agents.rule_guard import RuleGuard
from app.transform.framing_reconstructor import FramingReconstructor
from app.transform.node3_executor import Node3Executor
from app.transform.spec_validator import SpecValidator


class NodeA:
    """Perception and gap estimation."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def run(self, persona: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self.llm_client.evaluate_gap(persona=persona, _context=context)


class NodeB:
    """Strategy proposal + guard sanitization."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.guard = RuleGuard()
        self.llm_client = llm_client

    _ALL_OPS: list[str] = [
        "select_data_variables", "add_data_variables", "select_data_range",
        "change_data_granularity", "change_chart_type", "change_color",
        "add_background", "simplify_axis", "change_aspect_ratio",
        "change_axis_scale", "change_title", "add_annotation",
        "change_annotation", "delete_source", "change_legend", "add_legend",
    ]

    def run(
        self,
        gap_type: str,
        confidence: float,
        whitelist: list[str],
        shift_prior: str,
        persona: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        node_a_perception: str = "",
    ) -> dict[str, Any]:
        if (context or {}).get("mode") == "random_baseline":
            return self._random_baseline_strategy(whitelist, shift_prior)

        proposal = self.llm_client.propose_strategy(
            gap_type=gap_type,
            persona=persona or {},
            context=context or {},
            whitelist=whitelist,
            shift_prior=shift_prior,
        )
        action = proposal["action"]
        operations = proposal.get("operations", [])
        if not isinstance(operations, list):
            operations = []
        operation_plan = proposal.get("selected_operations", [])
        if not isinstance(operation_plan, list):
            operation_plan = []
        strategy_shift = proposal.get("expected_shift_magnitude", shift_prior)
        if not isinstance(strategy_shift, str):
            strategy_shift = shift_prior
        operation_rationale = proposal.get("operation_rationale", "")
        if not isinstance(operation_rationale, str):
            operation_rationale = ""

        guard = self.guard.sanitize(
            action=action,
            gap_type=gap_type,
            shift_magnitude=strategy_shift,
            operations=operations,
            whitelist=whitelist,
            confidence=confidence,
            operation_plan=operation_plan,
        )
        return {
            "action": guard.action,
            "gap_type": guard.gap_type,
            "shift_magnitude": guard.shift_magnitude,
            "operations": guard.operations,
            "selected_operations": guard.selected_operation_plan,
            "operation_rationale": operation_rationale,
            "rule_adjustments": guard.adjustments,
        }


    def _random_baseline_strategy(
        self, whitelist: list[str], shift_prior: str
    ) -> dict[str, Any]:
        """Skip LLM strategy: pick 1-4 random ops from the whitelist."""
        pool = whitelist if whitelist else self._ALL_OPS
        count = random.randint(1, min(4, len(pool)))
        ops = random.sample(pool, count)
        plan = [{"operation": op, "layer": "TEXT", "intent": "random baseline"} for op in ops]
        magnitudes = ["none", "minor", "sig", "major"]
        mag = random.choice(magnitudes)
        return {
            "action": "modify",
            "gap_type": "random",
            "shift_magnitude": mag,
            "operations": ops,
            "selected_operations": plan,
            "operation_rationale": "random baseline — no narrative gap mechanism",
            "rule_adjustments": [],
        }


class NodeC:
    """Node3 executor: reconstruct framing from the incoming parent chart, else patch ops."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client
        self.executor = Node3Executor(llm_client=llm_client)
        self.validator = SpecValidator()
        self.reconstructor = FramingReconstructor(llm_client=llm_client)

    def run(
        self,
        action: str,
        operations: list[str],
        shift_magnitude: str,
        selected_operations: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if action == "ignore":
            return {
                "variant_description": "该路径被忽略，停止传播。",
                "layers": "none",
                "updated_chart_spec": (context or {}).get("chartSpec"),
                "executed_operations": [],
                "execution_mode": "ignore",
                "validation_errors": [],
                "operation_audit": [],
            }
        parent_spec = (context or {}).get("chartSpec")
        persona = (context or {}).get("persona")
        _persona = persona if isinstance(persona, dict) else {}
        _ctx = context or {}
        role = str(_persona.get("category", ""))
        if role in {"Amplifier", "Adverser", "Analyst", "Extender", "Bridger"} and isinstance(parent_spec, dict):
            reconstructed = self.reconstructor.reconstruct(
                parent_spec=parent_spec,
                role=role or "Amplifier",
                gap_type=str(_ctx.get("gap_type") or ""),
                perception=str(_ctx.get("inner_monologue") or ""),
                shift_magnitude=shift_magnitude,
                context=_ctx,
            )
            if reconstructed is not None and reconstructed.ok:
                return self.reconstructor.as_node_c_payload(reconstructed, shift_magnitude)
        if not operations:
            return {
                "variant_description": "执行保守转发（无显式操作）。",
                "layers": f"T {shift_magnitude}",
                "updated_chart_spec": (context or {}).get("chartSpec"),
                "executed_operations": [],
                "execution_mode": "forward_noop",
                "validation_errors": [],
                "operation_audit": [],
            }
        parent_spec = (context or {}).get("chartSpec")
        persona = (context or {}).get("persona")
        refined_selected_operations = selected_operations or []
        if self.llm_client is not None:
            refined_selected_operations = self.llm_client.refine_execution_plan(
                selected_operations=refined_selected_operations,
                persona=persona if isinstance(persona, dict) else {},
                context=context or {},
            )
        _persona = persona if isinstance(persona, dict) else {}
        _ctx = context or {}
        result = self.executor.execute(
            parent_chart_spec=parent_spec,
            selected_operations=refined_selected_operations,
            shift_magnitude=shift_magnitude,
            role=str(_persona.get("category", "")),
            institution=str(_ctx.get("institution", "") or ""),
            depth=int(_ctx.get("depth", 1) or 1),
        )
        requested_count = len(refined_selected_operations)
        if requested_count > 0 and not result.executed_operations:
            return {
                "variant_description": "操作执行失败，降级为文本传播。",
                "layers": f"T {shift_magnitude}",
                "updated_chart_spec": parent_spec,
                "executed_operations": [],
                "execution_mode": "fallback_text",
                "validation_errors": ["all_operations_failed"],
                "operation_audit": result.operation_audit,
            }

        validation = self.validator.validate(result.updated_chart_spec)
        if not validation.ok:
            return {
                "variant_description": "节点变体校验失败，回滚到父节点图表。",
                "layers": f"T {shift_magnitude}",
                "updated_chart_spec": parent_spec,
                "executed_operations": result.executed_operations,
                "execution_mode": "node_rollback",
                "validation_errors": validation.errors,
                "operation_audit": result.operation_audit,
            }

        layer_map = {"data": "D", "visual": "V", "text": "T"}
        if result.layers_affected:
            layer_text = "+".join(layer_map[item] for item in result.layers_affected)
        else:
            layer_text = "T"
        return {
            "variant_description": result.variant_description,
            "layers": f"{layer_text} {shift_magnitude}",
            "updated_chart_spec": result.updated_chart_spec,
            "executed_operations": result.executed_operations,
            "execution_mode": "applied",
            "validation_errors": [],
            "operation_audit": result.operation_audit,
        }

