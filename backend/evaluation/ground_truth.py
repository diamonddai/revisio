"""Parse taxonomy markdown tables into structured GroundTruthLineage objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "taxonomy"

CANONICAL_OPS: list[str] = [
    "select_data_variables",
    "add_data_variables",
    "select_data_range",
    "change_data_granularity",
    "change_chart_type",
    "change_color",
    "add_background",
    "simplify_axis",
    "change_aspect_ratio",
    "change_axis_scale",
    "change_title",
    "add_annotation",
    "change_annotation",
    "delete_source",
    "change_legend",
    "add_legend",
]

OP_INDEX: dict[str, int] = {op: i for i, op in enumerate(CANONICAL_OPS)}

# Operation → layer (Data / Visual / Text) for layer-coverage trajectory
OP_TO_LAYER: dict[str, str] = {
    "select_data_variables": "data",
    "add_data_variables": "data",
    "select_data_range": "data",
    "change_data_granularity": "data",
    "change_chart_type": "visual",
    "change_color": "visual",
    "add_background": "visual",
    "simplify_axis": "visual",
    "change_aspect_ratio": "visual",
    "change_axis_scale": "visual",
    "change_legend": "visual",
    "add_legend": "visual",
    "change_title": "text",
    "add_annotation": "text",
    "change_annotation": "text",
    "delete_source": "text",
}


def layers_touched_by_ops(ops: list[str]) -> set[str]:
    """Return the set of layers (data/visual/text) touched by these operations."""
    layers: set[str] = set()
    for op in ops:
        layer = OP_TO_LAYER.get(op)
        if layer:
            layers.add(layer)
    return layers

_NORMALIZE_MAP: dict[str, str] = {
    "change type": "change_chart_type",
    "change chart type": "change_chart_type",
    "simplify axis": "simplify_axis",
    "simplify axis text": "simplify_axis",
    "change ldg": "change_legend",
    "change lgd": "change_legend",
    "change legend": "change_legend",
    "add lgd": "add_legend",
    "add legend": "add_legend",
    "add lgd": "add_legend",
    "change title": "change_title",
    "add annotation": "add_annotation",
    "change annotation": "change_annotation",
    "change color": "change_color",
    "select time range": "select_data_range",
    "select data range": "select_data_range",
    "delete source": "delete_source",
    "change aspect ratio": "change_aspect_ratio",
    "add background": "add_background",
    "change visual background": "add_background",
    "add data variables": "add_data_variables",
    "select data variables": "select_data_variables",
    "change data granularity": "change_data_granularity",
    "change axis scale": "change_axis_scale",
}


def normalize_op(raw: str) -> str | None:
    """Map a raw operation string from the taxonomy to its canonical name."""
    cleaned = raw.strip().lower()
    if cleaned in _NORMALIZE_MAP:
        return _NORMALIZE_MAP[cleaned]
    underscored = cleaned.replace(" ", "_")
    if underscored in OP_INDEX:
        return underscored
    return None


def get_operation_vector(ops: list[str]) -> np.ndarray:
    """Convert a list of canonical operation names into a 16-dim frequency vector."""
    vec = np.zeros(len(CANONICAL_OPS), dtype=np.float64)
    for op in ops:
        idx = OP_INDEX.get(op)
        if idx is not None:
            vec[idx] += 1.0
    return vec


@dataclass
class GTEdge:
    edge_id: str
    case_id: str
    source_node: str
    target_node: str
    source_role: str
    target_role: str
    operations: list[str]
    shift_magnitude: str


@dataclass
class GTNode:
    node_id: str
    case_id: str
    role: str
    platform: str
    is_source: bool


@dataclass
class GroundTruthLineage:
    case_id: str
    topic: str
    max_depth: int
    total_variants: int
    topology_type: str
    nodes: dict[str, GTNode] = field(default_factory=dict)
    edges: list[GTEdge] = field(default_factory=list)

    def all_operations(self) -> list[str]:
        """Flatten all edge operations into a single list."""
        ops: list[str] = []
        for edge in self.edges:
            ops.extend(edge.operations)
        return ops

    def node_depth_map(self) -> dict[str, int]:
        """BFS from the root (is_source) to assign depth to each node."""
        children: dict[str, list[str]] = {}
        for edge in self.edges:
            children.setdefault(edge.source_node, []).append(edge.target_node)
        root = None
        for nid, node in self.nodes.items():
            if node.is_source:
                root = nid
                break
        if root is None:
            return {}
        depth_map: dict[str, int] = {root: 0}
        queue = [root]
        while queue:
            current = queue.pop(0)
            for child in children.get(current, []):
                if child not in depth_map:
                    depth_map[child] = depth_map[current] + 1
                    queue.append(child)
        return depth_map

    def cumulative_layers_by_depth(self) -> list[float]:
        """Build per-depth trajectory: count of distinct layers (Data/Visual/Text) modified.

        Trajectory[i] = mean over nodes at depth i of |layers touched at that step|.
        Values in [0, 3]. Quantitative proxy for framing offset breadth.
        """
        depth_map = self.node_depth_map()
        if not depth_map:
            return [0.0]

        edge_ops: dict[str, dict[str, list[str]]] = {}
        for edge in self.edges:
            edge_ops.setdefault(edge.source_node, {})[edge.target_node] = edge.operations

        parent_map: dict[str, str] = {}
        for edge in self.edges:
            parent_map[edge.target_node] = edge.source_node

        max_depth = max(depth_map.values())
        trajectory: list[float] = [0.0]
        for d in range(1, max_depth + 1):
            nodes_at_d = [nid for nid, dep in depth_map.items() if dep == d]
            if not nodes_at_d:
                trajectory.append(trajectory[-1])
                continue
            layers_at_d: list[int] = []
            for nid in nodes_at_d:
                parent = parent_map.get(nid)
                ops = edge_ops.get(parent, {}).get(nid, []) if parent else []
                layers_at_d.append(len(layers_touched_by_ops(ops)))
            trajectory.append(sum(layers_at_d) / len(layers_at_d))
        return trajectory


def _parse_md_table(text: str) -> list[dict[str, str]]:
    """Parse a markdown table into a list of row dicts."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    table_lines = [ln for ln in lines if ln.startswith("|")]
    if len(table_lines) < 3:
        return []
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for row_line in table_lines[2:]:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        row = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def _normalize_role(raw: str) -> str:
    """Normalize role strings like 'transformer/adverser' -> 'adverser'."""
    role = raw.strip().lower()
    if "/" in role:
        parts = [p.strip() for p in role.split("/")]
        for p in parts:
            if p in ("amplifier", "adverser", "extender", "bridger", "analyst"):
                return p
        return parts[-1]
    return role


def _normalize_platform(raw: str) -> str:
    """Map Chinese platform names to English equivalents for the simulation."""
    p = raw.strip()
    mapping: dict[str, str] = {
        "政府/官方机构/国际组织": "政府/官方机构/国际组织",
        "新闻媒体": "新闻媒体",
        "社交媒体": "社交媒体",
        "个人网站/博客": "个人网站/博客",
        "机构博客": "机构博客",
        "第三方数据平台": "第三方数据平台",
        "在线社区/UGC平台": "在线社区/UGC平台",
        "科研机构": "科研机构",
    }
    return mapping.get(p, p)


def load_all_lineages() -> dict[str, GroundTruthLineage]:
    """Load and merge all three taxonomy tables into GroundTruthLineage objects."""
    how_path = DOCS_DIR / "taxonomy_how.md"
    who_path = DOCS_DIR / "taxonomy_who_where.md"
    case_path = DOCS_DIR / "taxonomy_case.md"

    case_rows = _parse_md_table(case_path.read_text(encoding="utf-8"))
    cases: dict[str, GroundTruthLineage] = {}
    for row in case_rows:
        cid = row.get("case_id", "").strip()
        if not cid:
            continue
        max_d = int(row.get("max_depth", "1").strip() or "1")
        total_v = int(row.get("total_variants", "1").strip() or "1")
        cases[cid] = GroundTruthLineage(
            case_id=cid,
            topic=row.get("topic", "").strip(),
            max_depth=max_d,
            total_variants=total_v,
            topology_type=row.get("topology_type", "tree").strip(),
        )

    who_rows = _parse_md_table(who_path.read_text(encoding="utf-8"))
    for row in who_rows:
        nid = row.get("node_id", "").strip()
        cid = row.get("case_id", "").strip()
        if not nid or cid not in cases:
            continue
        is_src = row.get("is_source", "").strip().lower() == "yes"
        role = _normalize_role(row.get("role", "bridger"))
        platform = _normalize_platform(row.get("platform", ""))
        cases[cid].nodes[nid] = GTNode(
            node_id=nid,
            case_id=cid,
            role=role,
            platform=platform,
            is_source=is_src,
        )

    how_rows = _parse_md_table(how_path.read_text(encoding="utf-8"))
    for row in how_rows:
        eid = row.get("edge_id", "").strip()
        cid = row.get("case_id", "").strip()
        if not eid or cid not in cases:
            continue
        raw_ops = row.get("frame_operation", "")
        ops: list[str] = []
        for part in re.split(r",\s*", raw_ops):
            norm = normalize_op(part)
            if norm:
                ops.append(norm)
        cases[cid].edges.append(GTEdge(
            edge_id=eid,
            case_id=cid,
            source_node=row.get("source_node", "").strip(),
            target_node=row.get("target_node", "").strip(),
            source_role=_normalize_role(row.get("source_role", "bridger")),
            target_role=_normalize_role(row.get("target_role", "bridger")),
            operations=ops,
            shift_magnitude=row.get("shift_magnitude", "none").strip(),
        ))

    return cases
