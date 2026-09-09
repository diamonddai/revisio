from __future__ import annotations

from app.schemas.api_contract import PathOffsetTrendItem, TreeEdge, TreeNode


class OffsetAnalyzer:
    rank = {"none": 0, "minor": 1, "sig": 2, "major": 3}

    def highest_offset(self, nodes: list[TreeNode]) -> str:
        best = "none"
        for node in nodes:
            val = node.offset or "none"
            if self.rank[val] > self.rank[best]:
                best = val
        return best

    def highest_path(self, nodes: list[TreeNode]) -> str:
        best_node = "SRC"
        best_offset = "none"
        for node in nodes:
            if node.id == "SRC":
                continue
            val = node.offset or "none"
            if self.rank[val] > self.rank[best_offset]:
                best_offset = val
                best_node = node.id
        return f"SRC->{best_node} ({best_offset})" if best_node != "SRC" else "SRC (none)"

    def highest_path_from_edges(self, nodes: list[TreeNode], edges: list[TreeEdge]) -> str:
        node_map = {n.id: n for n in nodes}
        parent: dict[str, str] = {}
        for edge in edges:
            parent[edge.target] = edge.source

        best_node = "SRC"
        best_offset = "none"
        for node in nodes:
            if node.id == "SRC":
                continue
            val = node.offset or "none"
            if self.rank[val] > self.rank[best_offset]:
                best_offset = val
                best_node = node.id

        if best_node == "SRC":
            return "SRC (none)"

        chain = [best_node]
        cur = best_node
        while cur in parent:
            cur = parent[cur]
            chain.append(cur)
            if cur == "SRC":
                break
        chain = list(reversed(chain))
        return f"{'->'.join(chain)} ({best_offset})"

    def trend_for_path(self, path: str, nodes: list[TreeNode]) -> list[PathOffsetTrendItem]:
        if path == "SRC (none)":
            return [PathOffsetTrendItem(step="SRC", offset="none")]
        left = path.split(" (")[0]
        ids = left.split("->")
        node_map = {n.id: n for n in nodes}
        trend: list[PathOffsetTrendItem] = []
        for node_id in ids:
            node = node_map.get(node_id)
            if node is None:
                continue
            trend.append(PathOffsetTrendItem(step=node_id, offset=node.offset or "none"))
        return trend

