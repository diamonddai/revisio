"""Batch simulation runner for system and random baseline conditions."""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from evaluation.ground_truth import GroundTruthLineage, normalize_op, layers_touched_by_ops

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CASE_MAPPING_PATH = Path(__file__).resolve().parent / "case_mapping.yaml"

ROLE_POOL = ["Amplifier", "Adverser", "Bridger", "Analyst"]
PLATFORM_POOL = [
    "新闻媒体", "社交媒体", "政府/官方机构/国际组织",
    "个人网站/博客", "机构博客", "第三方数据平台",
    "在线社区/UGC平台", "科研机构",
]


@dataclass
class SimRunResult:
    """Extracted result from a single simulation run."""
    case_id: str
    condition: str  # "system" or "random"
    all_operations: list[str] = field(default_factory=list)
    ops_by_depth: dict[int, list[list[str]]] = field(default_factory=dict)
    cum_ops_trajectory: list[float] = field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


def load_case_mapping() -> dict[str, str]:
    """Load case_id -> data directory path mapping."""
    with open(CASE_MAPPING_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return {k: str(v) for k, v in raw.items()}


def _ensure_eval_symlinks(case_mapping: dict[str, str]) -> None:
    """Create symlinks in backend/storage/cases/ for each data directory."""
    cases_dir = BACKEND_DIR / "storage" / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    for case_id, data_rel_path in case_mapping.items():
        link_name = f"eval-{case_id}"
        link_path = cases_dir / link_name
        target_path = PROJECT_ROOT / data_rel_path

        if link_path.is_symlink():
            if link_path.resolve() == target_path.resolve():
                continue
            link_path.unlink()
        elif link_path.exists():
            continue

        if target_path.exists():
            link_path.symlink_to(target_path)


def _map_role_to_category(role: str) -> str:
    """Map GT role string to SimulationStartRequest category."""
    mapping = {
        "amplifier": "Amplifier",
        "adverser": "Adverser",
        "bridger": "Bridger",
        "extender": "Analyst",
        "analyst": "Analyst",
    }
    return mapping.get(role.lower(), "Bridger")


def _build_system_request(
    lineage: GroundTruthLineage,
    case_mapping: dict[str, str],
    run_seed: int = 0,
):
    """Build a SimulationStartRequest for the system condition.

    run_seed shuffles agent profile order and appends a unique suffix to the
    description, ensuring each repeated run produces varied LLM outputs (breaks
    API-level prompt caching).
    """
    from app.schemas.api_contract import AgentProfile, SimulationStartRequest

    case_ref = f"eval-{lineage.case_id}"

    non_root_nodes = [
        n for n in lineage.nodes.values() if not n.is_source
    ]
    profiles = []
    categories = []
    for node in non_root_nodes:
        cat = _map_role_to_category(node.role)
        categories.append(cat)
        profiles.append(AgentProfile(
            role=node.role,
            institution=node.platform,
        ))

    if run_seed > 0 and len(profiles) > 1:
        rng = random.Random(run_seed)
        combined = list(zip(profiles, categories))
        rng.shuffle(combined)
        profiles, categories = [list(t) for t in zip(*combined)]

    if not categories:
        categories = ["Amplifier"]

    desc_suffix = f" (trial {run_seed + 1})" if run_seed > 0 else ""

    return SimulationStartRequest(
        agentCount=len(non_root_nodes),
        agentCategories=list(dict.fromkeys(categories)) or ["Amplifier"],
        agentProfiles=profiles,
        maxDepth=lineage.max_depth,
        mode="neutral",
        description=f"{lineage.topic}{desc_suffix}" if desc_suffix else None,
        topic=lineage.topic,
        caseRef=case_ref,
    )


def _build_random_request(
    lineage: GroundTruthLineage,
    case_mapping: dict[str, str],
):
    """Build a SimulationStartRequest for the random baseline condition."""
    from app.schemas.api_contract import AgentProfile, SimulationStartRequest

    case_ref = f"eval-{lineage.case_id}"
    n_agents = lineage.total_variants

    profiles = []
    categories = []
    for _ in range(n_agents):
        role = random.choice(ROLE_POOL)
        platform = random.choice(PLATFORM_POOL)
        categories.append(role)
        profiles.append(AgentProfile(
            role=role.lower(),
            institution=platform,
        ))

    return SimulationStartRequest(
        agentCount=n_agents,
        agentCategories=list(dict.fromkeys(categories)) or ["Amplifier"],
        agentProfiles=profiles,
        maxDepth=lineage.max_depth,
        mode="random_baseline",
        topic=lineage.topic,
        caseRef=case_ref,
    )


def _extract_operations_from_response(response) -> tuple[list[str], dict[int, list[list[str]]]]:
    """Extract normalized operation names from a simulation response.

    Returns (all_ops_flat, ops_by_depth).
    """
    all_ops: list[str] = []
    ops_by_depth: dict[int, list[list[str]]] = {}

    tree = response.tree
    if not tree:
        return all_ops, ops_by_depth

    parent_map: dict[str, str] = {}
    for edge in tree.edges:
        parent_map[edge.target] = edge.source

    depth_map: dict[str, int] = {"SRC": 0}
    for node in tree.nodes:
        if node.id == "SRC":
            continue
        parent = parent_map.get(node.id)
        depth_map[node.id] = depth_map.get(parent, 0) + 1 if parent else 1

    for node in tree.nodes:
        if node.id == "SRC":
            continue
        node_ops: list[str] = []
        if node.operations:
            for op_str in node.operations:
                cleaned = re.sub(r"^(DATA|VISUAL|TEXT)\s+", "", op_str)
                op_name = cleaned.split(":")[0].strip()
                norm = normalize_op(op_name)
                if norm:
                    node_ops.append(norm)

        all_ops.extend(node_ops)
        d = depth_map.get(node.id, 1)
        ops_by_depth.setdefault(d, []).append(node_ops)

    return all_ops, ops_by_depth


def _build_layers_trajectory_from_response(response) -> list[float]:
    """Build per-depth trajectory: avg count of layers (Data/Visual/Text) modified."""
    tree = response.tree
    if not tree:
        return [0.0]

    parent_map: dict[str, str] = {}
    for edge in tree.edges:
        parent_map[edge.target] = edge.source

    depth_map: dict[str, int] = {"SRC": 0}
    for node in tree.nodes:
        if node.id == "SRC":
            continue
        parent = parent_map.get(node.id)
        depth_map[node.id] = depth_map.get(parent, 0) + 1 if parent else 1

    node_ops: dict[str, list[str]] = {"SRC": []}
    for node in tree.nodes:
        if node.id == "SRC":
            continue
        ops: list[str] = []
        if node.operations:
            for op_str in node.operations:
                cleaned = re.sub(r"^(DATA|VISUAL|TEXT)\s+", "", op_str)
                op_name = cleaned.split(":")[0].strip()
                norm = normalize_op(op_name)
                if norm:
                    ops.append(norm)
        node_ops[node.id] = ops

    max_depth = max(depth_map.values()) if depth_map else 0
    trajectory: list[float] = [0.0]
    for d in range(1, max_depth + 1):
        nodes_at_d = [n for n, dep in depth_map.items() if dep == d]
        if not nodes_at_d:
            trajectory.append(trajectory[-1])
            continue
        counts = [len(layers_touched_by_ops(node_ops.get(n, []))) for n in nodes_at_d]
        trajectory.append(sum(counts) / len(counts))
    return trajectory


def run_evaluation(
    lineages: dict[str, GroundTruthLineage],
    case_mapping: dict[str, str],
    case_ids: list[str] | None = None,
    n_runs: int = 3,
    skip_random: bool = False,
    verbose: bool = True,
) -> dict[str, list[SimRunResult]]:
    """Run evaluation for specified cases.

    Returns dict: case_id -> list of SimRunResult (system + random runs).
    """
    os.chdir(BACKEND_DIR)
    _ensure_eval_symlinks(case_mapping)

    from app.services.simulation_service import SimulationService
    service = SimulationService()

    target_cases = case_ids or [cid for cid in case_mapping if cid in lineages]
    results: dict[str, list[SimRunResult]] = {}

    for cid in target_cases:
        if cid not in lineages:
            if verbose:
                print(f"[SKIP] {cid}: no ground truth lineage found")
            continue
        if cid not in case_mapping:
            if verbose:
                print(f"[SKIP] {cid}: no data directory mapping found")
            continue

        data_path = PROJECT_ROOT / case_mapping[cid]
        if not (data_path / "chart_spec.json").exists():
            if verbose:
                print(f"[SKIP] {cid}: chart_spec.json not found at {data_path}")
            continue

        lin = lineages[cid]
        case_results: list[SimRunResult] = []

        if verbose:
            print(f"\n{'='*60}")
            print(f"[EVAL] Case {cid}: {lin.topic}")
            print(f"  GT: {lin.total_variants} variants, max_depth={lin.max_depth}")
            print(f"  GT ops: {lin.all_operations()}")

        for run_idx in range(n_runs):
            if verbose:
                print(f"  [System Run {run_idx+1}/{n_runs}] ...", end=" ", flush=True)
            req = _build_system_request(lin, case_mapping, run_seed=run_idx)
            try:
                resp = service.run_sync(req)
                all_ops, ops_by_depth = _extract_operations_from_response(resp)
                trajectory = _build_layers_trajectory_from_response(resp)
                result = SimRunResult(
                    case_id=cid,
                    condition="system",
                    all_operations=all_ops,
                    ops_by_depth=ops_by_depth,
                    cum_ops_trajectory=trajectory,
                    node_count=resp.tree.nodeCount if resp.tree else 0,
                    edge_count=resp.tree.edgeCount if resp.tree else 0,
                )
                case_results.append(result)
                if verbose:
                    print(f"OK ({len(all_ops)} ops, {result.node_count} nodes)")
            except Exception as e:
                if verbose:
                    print(f"FAILED: {e}")
                case_results.append(SimRunResult(case_id=cid, condition="system"))

        if not skip_random:
            for run_idx in range(n_runs):
                if verbose:
                    print(f"  [Random Run {run_idx+1}/{n_runs}] ...", end=" ", flush=True)
                req = _build_random_request(lin, case_mapping)
                try:
                    resp = service.run_sync(req)
                    all_ops, ops_by_depth = _extract_operations_from_response(resp)
                    trajectory = _build_layers_trajectory_from_response(resp)
                    result = SimRunResult(
                        case_id=cid,
                        condition="random",
                        all_operations=all_ops,
                        ops_by_depth=ops_by_depth,
                        cum_ops_trajectory=trajectory,
                        node_count=resp.tree.nodeCount if resp.tree else 0,
                        edge_count=resp.tree.edgeCount if resp.tree else 0,
                    )
                    case_results.append(result)
                    if verbose:
                        print(f"OK ({len(all_ops)} ops, {result.node_count} nodes)")
                except Exception as e:
                    if verbose:
                        print(f"FAILED: {e}")
                    case_results.append(SimRunResult(case_id=cid, condition="random"))

        results[cid] = case_results

    return results
