from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.agents.llm_client import LLMClient
from app.agents.taxonomy_adapter import TaxonomyAdapter
from app.analysis.offset_analyzer import OffsetAnalyzer
from app.config.settings import get_settings
from app.graph.langgraph_runner import LangGraphRunner
from app.graph.workflow import NodeA, NodeB, NodeC
from app.infra.storage import RunStorage
from app.transform.spec_renderer import SpecRenderer
from app.schemas.api_contract import (
    AgentLogItem,
    PathOffsetTrendItem,
    SimulationStartRequest,
    SimulationStartResponse,
    SummaryPayload,
    TreeEdge,
    TreeNode,
    TreePayload,
)


class SimulationService:
    OP_LAYER_FOR_UI: dict[str, str] = {
        "select_data_variables": "DATA",
        "add_data_variables": "DATA",
        "select_data_range": "DATA",
        "change_data_granularity": "DATA",
        "change_chart_type": "VISUAL",
        "change_color": "VISUAL",
        "add_background": "VISUAL",
        "simplify_axis": "VISUAL",
        "change_aspect_ratio": "VISUAL",
        "change_axis_scale": "VISUAL",
        "change_title": "TEXT",
        "add_annotation": "TEXT",
        "change_annotation": "TEXT",
        "delete_source": "TEXT",
        "change_legend": "TEXT",
        "add_legend": "TEXT",
    }
    def __init__(self) -> None:
        settings = get_settings()
        use_taxonomy = settings.use_taxonomy
        use_llm = settings.use_llm
        self.max_depth = settings.sim_max_depth
        self.adapter = TaxonomyAdapter(use_taxonomy=use_taxonomy)
        self.llm_client = LLMClient(enabled=use_llm)
        self.node_a = NodeA(llm_client=self.llm_client)
        self.node_b = NodeB(llm_client=self.llm_client)
        self.node_c = NodeC(llm_client=self.llm_client)
        self.graph_runner = LangGraphRunner(self.node_a, self.node_b, self.node_c)
        self.storage = RunStorage()
        self.analyzer = OffsetAnalyzer()
        self.spec_renderer = SpecRenderer()

    def run_sync(self, req: SimulationStartRequest) -> SimulationStartResponse:
        run_id = uuid4().hex[:8]
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        run_max_depth = req.maxDepth or self.max_depth
        run_mode = req.mode or "neutral"
        case_inputs = self._resolve_case_inputs(req)
        resolved_image_ref = case_inputs["image_ref"]
        resolved_desc = case_inputs["description"]
        root_label = case_inputs["root_label"]
        chart_spec_ref = case_inputs["chart_spec_ref"]
        chart_spec = case_inputs["chart_spec"]
        root_node = TreeNode(
            id="SRC",
            label=root_label,
            actionLabel="源",
            nodeType="neutral",
            offset="none",
            imageUrl=resolved_image_ref,
            chartSpecUrl=chart_spec_ref,
            chartSpec=chart_spec,
            variantDescription=resolved_desc,
        )

        nodes = [root_node]
        edges: list[TreeEdge] = []
        node_depth: dict[str, int] = {"SRC": 0}
        logs = [
            AgentLogItem(
                id="log-1",
                time=now,
                source="SYSTEM",
                message=(
                    f"初始化模拟环境（V1-Batch11）"
                    f" rule_source={self.adapter.rule_source}"
                    f" rule_version={self.adapter.rule_version}"
                    f" mode={run_mode}"
                    f" max_depth={run_max_depth}"
                ),
                offsetLevel="none",
            )
        ]
        provenance_chain: list[dict[str, object]] = []

        parent_frontier = ["SRC"]
        next_node_seq = 1
        next_edge_seq = 1
        generated_agents = 0
        depth = 0
        max_depth_reached = 0
        node_image_map: dict[str, str | None] = {"SRC": resolved_image_ref}
        node_spec_map: dict[str, dict[str, object] | None] = {"SRC": chart_spec}
        profile_pool_size = len(req.agentProfiles) if req.agentProfiles else 0
        branch_budget = min(req.agentCount, profile_pool_size) if profile_pool_size else req.agentCount
        unused_profile_indexes = list(range(profile_pool_size))
        node_category_map: dict[str, str] = {"SRC": "Bridger"}
        # Chain context: track modification history from root to each node
        # so downstream agents can perceive what prior agents did.
        node_chain_history: dict[str, list[dict[str, object]]] = {"SRC": []}
        chain_plan = self._plan_chain(req=req, chart_spec=chart_spec, description=resolved_desc, budget=branch_budget)
        if chain_plan and chain_plan.get("story"):
            logs.append(
                AgentLogItem(
                    id="log-chain-plan",
                    time=now,
                    source="SYSTEM",
                    message=f"Chain plan: {str(chain_plan.get('story'))[:220]}",
                    offsetLevel="none",
                )
            )

        # Batch5+: multi-depth expansion with per-layer agent allocation.
        while parent_frontier and generated_agents < branch_budget and depth < run_max_depth:
            next_frontier: list[str] = []
            ignored_frontier: list[str] = []
            remaining_agents = branch_budget - generated_agents
            remaining_depth = max(run_max_depth - depth, 1)
            agents_this_depth = min(remaining_agents, max(1, math.ceil(remaining_agents / remaining_depth)))
            # Ordered profiles that fit in maxDepth run as a spine (parent → child),
            # so Extender→Extender or Amp→Ext→Adv can compound instead of fanning from SRC.
            if profile_pool_size > 0 and branch_budget <= run_max_depth:
                agents_this_depth = min(1, remaining_agents)
            assigned_parents = [
                parent_frontier[i % len(parent_frontier)]
                for i in range(agents_this_depth)
            ]
            # Track categories already assigned at this depth layer to enforce diversity:
            # nodes at the same layer should preferably have different types.
            used_categories_this_depth: set[str] = set()

            for parent_id in assigned_parents:
                if generated_agents >= branch_budget:
                    break

                current_profile = None
                category = self._resolve_agent_category(
                    req=req, index=generated_agents, used_this_depth=used_categories_this_depth
                )
                if req.agentProfiles and unused_profile_indexes:
                    parent_category = node_category_map.get(parent_id, "Bridger")
                    selected_profile_index = self._pick_profile_index_by_f2(
                        req=req,
                        parent_category=parent_category,
                        unused_indexes=unused_profile_indexes,
                        used_this_depth=used_categories_this_depth,
                    )
                    if selected_profile_index is not None:
                        current_profile = req.agentProfiles[selected_profile_index]
                        mapped = self._normalize_profile_role(current_profile.role)
                        if mapped:
                            category = mapped
                        unused_profile_indexes.remove(selected_profile_index)
                used_categories_this_depth.add(category)

                persona = self.adapter.pick_persona(category=category, seed=generated_agents + len(run_id) + depth)
                whitelist = self.adapter.get_operation_whitelist(persona)
                agent_depth = depth + 1
                parent_chain = node_chain_history.get(parent_id, [])
                agent_context = {
                    "description": resolved_desc,
                    "topic": req.topic,
                    "imageRef": resolved_image_ref,
                    "chartSpec": node_spec_map.get(parent_id),
                    "rootChartSpec": chart_spec,
                    "parentId": parent_id,
                    "mode": run_mode,
                    "institution": current_profile.institution if current_profile else None,
                    "persona": persona,
                    "depth": agent_depth,
                    "maxDepth": run_max_depth,
                    "chainHistory": parent_chain,
                    "chain_plan": chain_plan,
                    "chain_plan_step": (
                        (chain_plan.get("steps") or [None])[generated_agents]
                        if chain_plan and generated_agents < len(chain_plan.get("steps") or [])
                        else None
                    ),
                }
                shift_prior = self.adapter.get_shift_prior(persona, "tension")
                shift_prior = self._apply_mode_shift_bias(shift_prior=shift_prior, mode=run_mode)
                shift_prior = self._apply_depth_offset_escalation(shift_prior=shift_prior, depth=agent_depth)
                graph_state = self.graph_runner.run(
                    persona=persona,
                    context=agent_context,
                    whitelist=whitelist,
                    shift_prior=shift_prior,
                )
                node_a_result = graph_state["node_a_result"]
                node_b_result = graph_state["node_b_result"]
                node_c_result = graph_state.get(
                    "node_c_result",
                    {"variant_description": "该路径被忽略，停止传播。", "layers": "none"},
                )

                generated_agents += 1
                provenance_chain.append(
                    {
                        "agent_id": generated_agents,
                        "parent_id": parent_id,
                        "depth": depth + 1,
                        "persona": persona,
                        "mode": run_mode,
                        "gap_evidence": node_a_result["inner_monologue"],
                        "gap_type": node_b_result["gap_type"],
                        "alignment_with_preference": node_a_result.get("alignment_with_preference"),
                        "identified_gaps": node_a_result.get("identified_gaps", []),
                        "expected_modification_intensity": node_a_result.get("expected_modification_intensity"),
                        "selected_operations": node_b_result["operations"],
                        "selected_operation_plan": node_b_result.get("selected_operations", []),
                        "operation_rationale": node_b_result.get("operation_rationale"),
                        "rule_adjustments": node_b_result["rule_adjustments"],
                        "node_decision_trace": {
                            "action": node_b_result["action"],
                            "shift_magnitude": node_b_result["shift_magnitude"],
                        },
                        "executed_operations": node_c_result.get("executed_operations", []),
                        "operation_audit": node_c_result.get("operation_audit", []),
                        "execution_mode": node_c_result.get("execution_mode"),
                        "validation_errors": node_c_result.get("validation_errors", []),
                        "framing_contract": node_c_result.get("framing_contract"),
                        "verify_reasons": node_c_result.get("verify_reasons", []),
                        "chain_plan_step": agent_context.get("chain_plan_step"),
                    }
                )
                logs.append(
                    AgentLogItem(
                        id=f"log-{generated_agents + 1}",
                        time=now,
                        source=f"AGENT_{generated_agents}",
                        message=(
                            f"Agent#{generated_agents} {category} "
                            f"parent={parent_id} depth={depth + 1} "
                            f"gap={node_b_result['gap_type']} "
                            f"action={node_b_result['action']} "
                            f"mode={run_mode} "
                            f"exec={node_c_result.get('execution_mode')} "
                            f"adjustments={len(node_b_result['rule_adjustments'])}"
                        ),
                        offsetLevel=node_b_result["shift_magnitude"],
                    )
                )

                node_id = f"V{next_node_seq}"
                next_node_seq += 1
                parent_image = node_image_map.get(parent_id)
                node_chart_spec = node_c_result.get("updated_chart_spec")
                if node_b_result["action"] == "ignore":
                    node_image = parent_image or resolved_image_ref
                else:
                    rendered = self.spec_renderer.to_data_url(node_chart_spec)
                    node_image = rendered or resolved_image_ref or parent_image
                ui_operations = self._format_operations_for_ui(
                    node_c_result.get("executed_operations", []) or node_b_result.get("selected_operations", []),
                    node_b_result["operations"],
                    node_c_result.get("operation_audit", []),
                )
                node = TreeNode(
                    id=node_id,
                    label=f"@Agent-{generated_agents}",
                    nodeType=self._category_to_node_type(category),
                    role=self._display_role_for_node(
                        persona=persona,
                        category=category,
                        profile_role=(current_profile.role if current_profile else None),
                    ),
                    institution=(current_profile.institution if current_profile else None),
                    motivation=str(persona.get("motivation", "传播")),
                    offset=node_b_result["shift_magnitude"],
                    imageUrl=node_image,
                    operations=ui_operations,
                    chartSpec=node_chart_spec,
                    variantDescription=node_c_result["variant_description"],
                    layers=node_c_result["layers"],
                )
                nodes.append(node)
                node_depth[node_id] = depth + 1
                node_image_map[node_id] = node_image
                node_spec_map[node_id] = node_chart_spec or node_spec_map.get(parent_id)
                node_category_map[node_id] = category
                node_chain_history[node_id] = parent_chain + [{
                    "agent_role": category,
                    "institution": current_profile.institution if current_profile else None,
                    "depth": agent_depth,
                    "gap_type": node_b_result["gap_type"],
                    "action": node_b_result["action"],
                    "operations": node_b_result["operations"],
                    "shift_magnitude": node_b_result["shift_magnitude"],
                }]
                max_depth_reached = max(max_depth_reached, depth + 1)
                edge = TreeEdge(
                    id=f"e{next_edge_seq}",
                    source=parent_id,
                    target=node_id,
                    offset=node_b_result["shift_magnitude"],
                )
                next_edge_seq += 1
                edges.append(edge)
                if node_b_result["action"] != "ignore":
                    next_frontier.append(node_id)
                else:
                    ignored_frontier.append(node_id)

            if not next_frontier and generated_agents < branch_budget:
                # If all current-layer actions are ignore, keep chain alive by using
                # ignore nodes as pass-through parents for the next layer.
                next_frontier = ignored_frontier

            parent_frontier = next_frontier
            depth += 1

        highest_offset = self.analyzer.highest_offset(nodes)
        highest_path = self.analyzer.highest_path_from_edges(nodes, edges) if edges else "SRC (none)"
        trend = self.analyzer.trend_for_path(highest_path, nodes)
        tree = TreePayload(
            nodes=nodes,
            edges=edges,
            nodeCount=len(nodes),
            edgeCount=len(edges),
            maxDepth=max_depth_reached,
            highestOffsetPath=highest_path,
            topologyType="tree" if len(nodes) > 1 else "single",
        )
        summary = SummaryPayload(
            agentCount=req.agentCount,
            edgeCount=tree.edgeCount,
            highestOffset=highest_offset,
        )

        response = SimulationStartResponse(
            ok=True,
            tree=tree,
            agentLog=logs,
            summary=summary,
            pathOffsetTrend=trend,
            overallVariantDescription=(
                "V1 Batch13：接入 Node3 参数协议与执行器（M1+M2 起步）"
            ),
            variantImageUrl=(node_image_map.get(nodes[-1].id) if nodes else resolved_image_ref),
        )
        self.storage.save_snapshot(
            run_id,
            {
                "run_id": run_id,
                "rule_source": self.adapter.rule_source,
                "rule_version": self.adapter.rule_version,
                "llm_enabled": self.llm_client.enabled,
                "max_depth": run_max_depth,
                "mode": run_mode,
                "request": req.model_dump(),
                "response": response.model_dump(),
                "provenance_chain": provenance_chain,
            },
        )
        return response

    @staticmethod
    def _category_to_node_type(category: str) -> str:
        mapping = {
            "Amplifier": "amplifier",
            "Analyst": "analyst",
            "Bridger": "bridger",
            "Adverser": "adverser",
        }
        return mapping.get(category, "neutral")

    @staticmethod
    def _normalize_profile_role(role: str | None) -> str | None:
        if not role:
            return None
        normalized = role.strip().lower()
        mapping = {
            "bridger": "Bridger",
            "amplifier": "Amplifier",
            "adverser": "Adverser",
            "analyst": "Analyst",
            "extender": "Analyst",
            # keep historical typo compatible for old payloads
            "extensioner": "Analyst",
        }
        return mapping.get(normalized)

    def _resolve_agent_category(
        self,
        req: SimulationStartRequest,
        index: int,
        used_this_depth: set[str] | None = None,
    ) -> str:
        if req.agentProfiles and index < len(req.agentProfiles):
            mapped = self._normalize_profile_role(req.agentProfiles[index].role)
            if mapped:
                return mapped
        categories = req.agentCategories
        if not used_this_depth:
            return categories[index % len(categories)]
        # Prefer a category not yet used at this depth layer for diversity
        unused = [c for c in categories if c not in used_this_depth]
        if unused:
            return unused[index % len(unused)]
        return categories[index % len(categories)]

    def _pick_profile_index_by_f2(
        self,
        req: SimulationStartRequest,
        parent_category: str,
        unused_indexes: list[int],
        used_this_depth: set[str] | None = None,
    ) -> int | None:
        if not req.agentProfiles or not unused_indexes:
            return None
        transition_prior = self.adapter.get_role_transition_prior(parent_category=parent_category)
        best_index = unused_indexes[0]
        best_score = -1.0
        for index in unused_indexes:
            profile = req.agentProfiles[index]
            mapped = self._normalize_profile_role(profile.role)
            category = mapped or req.agentCategories[index % len(req.agentCategories)]
            score = float(transition_prior.get(category, 0.0))
            # Diversity bonus: prefer categories not yet used at this depth layer
            if used_this_depth is not None and category not in used_this_depth:
                score += 0.35
            if score > best_score:
                best_score = score
                best_index = index
        return best_index

    @staticmethod
    def _display_role_for_node(
        persona: dict[str, object],
        category: str,
        profile_role: str | None = None,
    ) -> str:
        if isinstance(profile_role, str) and profile_role.strip():
            role = profile_role.strip()
            if role.lower() == "analyst":
                return "Extender"
            return role
        raw_role = persona.get("role")
        if isinstance(raw_role, str):
            role = raw_role.strip()
            if role.lower() == "analyst":
                return "Extender"
            return role
        if category == "Analyst":
            return "Extender"
        return category

    @staticmethod
    def _apply_mode_shift_bias(shift_prior: str, mode: str) -> str:
        if mode == "adversarial":
            up = {"none": "minor", "minor": "sig", "sig": "major", "major": "major"}
            return up.get(shift_prior, shift_prior)
        if mode == "conservative":
            down = {"major": "sig", "sig": "minor", "minor": "none", "none": "none"}
            return down.get(shift_prior, shift_prior)
        return shift_prior

    @staticmethod
    def _apply_depth_offset_escalation(shift_prior: str, depth: int) -> str:
        """Escalate offset based on propagation depth.
        Deeper nodes accumulate more framing shift — depth 1 is baseline,
        depth 2 escalates by one level, depth 3+ escalates by two levels.
        """
        _UP = {"none": "minor", "minor": "sig", "sig": "major", "major": "major"}
        result = shift_prior
        escalation_steps = max(0, depth - 1)
        for _ in range(escalation_steps):
            result = _UP.get(result, result)
        return result

    def _resolve_case_inputs(self, req: SimulationStartRequest) -> dict[str, object]:
        metadata = self._load_json_from_ref(req.metadataRef)
        chart_spec = self._load_json_from_ref(req.chartSpecRef)
        chart_spec_ref = req.chartSpecRef
        image_ref = req.imageRef  # deprecated compatibility

        if req.caseRef:
            case_dir = Path("storage/cases") / req.caseRef
            if case_dir.exists():
                if metadata is None:
                    metadata = self._load_json_from_file(case_dir / "metadata.json")
                if chart_spec is None:
                    chart_spec = self._load_json_from_file(case_dir / "chart_spec.json")
                    if chart_spec is not None and chart_spec_ref is None:
                        chart_spec_ref = f"/cases/{req.caseRef}/chart_spec.json"
                if image_ref is None:
                    image_ref = self._pick_case_image_ref(req.caseRef, case_dir)

        resolved_desc = req.description or str((metadata or {}).get("description") or "用户上传原始图表")
        root_label = str((metadata or {}).get("title") or "Source Visualization")
        return {
            "image_ref": image_ref,
            "description": resolved_desc,
            "root_label": root_label,
            "chart_spec_ref": chart_spec_ref,
            "chart_spec": chart_spec,
        }

    @staticmethod
    def _pick_case_image_ref(case_ref: str, case_dir: Path) -> str | None:
        for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
            candidate = case_dir / f"visualization{ext}"
            if candidate.exists():
                return f"/cases/{case_ref}/{candidate.name}"
        return None

    @staticmethod
    def _load_json_from_ref(ref: str | None) -> dict[str, object] | None:
        if not ref or not ref.startswith("/cases/"):
            return None
        local = Path("storage/cases") / ref.removeprefix("/cases/")
        return SimulationService._load_json_from_file(local)

    def _plan_chain(
        self,
        req: SimulationStartRequest,
        chart_spec: dict[str, object] | None,
        description: str,
        budget: int,
    ) -> dict[str, object] | None:
        if not req.agentProfiles or budget <= 0:
            return None
        if not self.llm_client.enabled or not self.llm_client.api_key:
            return None
        profiles = []
        for item in req.agentProfiles[:budget]:
            profiles.append(
                {
                    "role": str(item.role or "Amplifier"),
                    "institution": str(item.institution or ""),
                }
            )
        series = LLMClient._extract_xy_series_summary(chart_spec if isinstance(chart_spec, dict) else None)
        if series:
            summary = (
                f"{series.get('y_label')} {series.get('trend')} "
                f"{series.get('first_x')}→{series.get('last_x')} peak {series.get('peak_x')}"
            )
        else:
            summary = description or "source chart"
        return self.llm_client.plan_propagation_chain(
            source_title=LLMClient._extract_title(chart_spec if isinstance(chart_spec, dict) else None) or description,
            series_summary=summary,
            profiles=profiles,
        )

    @staticmethod
    def _load_json_from_file(path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @classmethod
    def _format_operations_for_ui(
        cls,
        selected_operation_plan: list[dict[str, object]] | None,
        operation_names: list[str],
        operation_audit: list[dict[str, object]] | None = None,
    ) -> list[str]:
        formatted_from_audit: list[str] = []
        if operation_audit:
            for item in operation_audit:
                if not isinstance(item, dict):
                    continue
                op = item.get("operation")
                if not isinstance(op, str):
                    continue
                params = item.get("params")
                intent = params.get("intent") if isinstance(params, dict) else None
                status = item.get("status")
                error = item.get("error")
                prefix = cls.OP_LAYER_FOR_UI.get(op, "TEXT")
                base = f"{op}: {intent}" if isinstance(intent, str) and intent.strip() else op
                if status == "applied":
                    formatted_from_audit.append(f"{prefix} {base}")
                elif isinstance(status, str) and status:
                    err = str(error).strip() if isinstance(error, str) else ""
                    formatted_from_audit.append(f"{prefix} {base} [{status}{': ' + err if err else ''}]")
                else:
                    formatted_from_audit.append(f"{prefix} {base}")
        if formatted_from_audit:
            return formatted_from_audit

        formatted: list[str] = []
        if selected_operation_plan:
            for item in selected_operation_plan:
                if not isinstance(item, dict):
                    continue
                op = item.get("operation")
                layer = item.get("layer")
                intent = item.get("intent")
                if not isinstance(intent, str):
                    params = item.get("params")
                    if isinstance(params, dict) and isinstance(params.get("intent"), str):
                        intent = params.get("intent")
                if not isinstance(op, str):
                    continue
                prefix = str(layer).upper() if isinstance(layer, str) else cls.OP_LAYER_FOR_UI.get(op, "TEXT")
                if prefix not in {"DATA", "TEXT", "VISUAL"}:
                    prefix = cls.OP_LAYER_FOR_UI.get(op, "TEXT")
                tail = f"{op}: {intent}" if isinstance(intent, str) and intent.strip() else op
                formatted.append(f"{prefix} {tail}")
        if formatted:
            return formatted

        fallback: list[str] = []
        for op in operation_names:
            prefix = cls.OP_LAYER_FOR_UI.get(op, "TEXT")
            fallback.append(f"{prefix} {op}")
        return fallback

