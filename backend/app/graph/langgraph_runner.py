from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.graph.workflow import NodeA, NodeB, NodeC


class AgentGraphState(TypedDict, total=False):
    persona: dict[str, Any]
    context: dict[str, Any]
    whitelist: list[str]
    shift_prior: str
    node_a_result: dict[str, Any]
    node_b_result: dict[str, Any]
    node_c_result: dict[str, Any]
    action: str


class LangGraphRunner:
    """Single-agent graph runner with conditional routing."""

    def __init__(self, node_a: NodeA, node_b: NodeB, node_c: NodeC) -> None:
        self.node_a = node_a
        self.node_b = node_b
        self.node_c = node_c
        self.graph = self._build_graph()

    def run(
        self,
        persona: dict[str, Any],
        context: dict[str, Any],
        whitelist: list[str],
        shift_prior: str,
    ) -> AgentGraphState:
        initial_state: AgentGraphState = {
            "persona": persona,
            "context": context,
            "whitelist": whitelist,
            "shift_prior": shift_prior,
        }
        return self.graph.invoke(initial_state)

    def _build_graph(self):
        workflow = StateGraph(AgentGraphState)
        workflow.add_node("node_a", self._run_node_a)
        workflow.add_node("node_b", self._run_node_b)
        workflow.add_node("node_c", self._run_node_c)
        workflow.set_entry_point("node_a")
        workflow.add_edge("node_a", "node_b")
        workflow.add_conditional_edges(
            "node_b",
            self._route_after_node_b,
            {
                "continue": "node_c",
                "stop": END,
            },
        )
        workflow.add_edge("node_c", END)
        return workflow.compile()

    def _run_node_a(self, state: AgentGraphState) -> AgentGraphState:
        node_a_result = self.node_a.run(
            persona=state["persona"],
            context=state.get("context", {}),
        )
        return {"node_a_result": node_a_result}

    def _run_node_b(self, state: AgentGraphState) -> AgentGraphState:
        node_a_result = state["node_a_result"]
        # Pass NodeA's data-grounded inner_monologue to NodeB so strategy is perception-informed
        node_a_perception = str(node_a_result.get("inner_monologue", ""))
        node_b_result = self.node_b.run(
            gap_type=node_a_result["gap_type"],
            confidence=float(node_a_result["confidence"]),
            whitelist=state.get("whitelist", []),
            shift_prior=state.get("shift_prior", "minor"),
            persona=state.get("persona", {}),
            context=state.get("context", {}),
            node_a_perception=node_a_perception,
        )
        return {"node_b_result": node_b_result, "action": node_b_result["action"]}

    def _run_node_c(self, state: AgentGraphState) -> AgentGraphState:
        node_b_result = state["node_b_result"]
        node_a_result = state.get("node_a_result") or {}
        context = dict(state.get("context") or {})
        context["gap_type"] = node_b_result.get("gap_type") or ""
        context["inner_monologue"] = str(node_a_result.get("inner_monologue") or "")
        node_c_result = self.node_c.run(
            action=node_b_result["action"],
            operations=node_b_result["operations"],
            shift_magnitude=node_b_result["shift_magnitude"],
            selected_operations=node_b_result.get("selected_operations", []),
            context=context,
        )
        return {"node_c_result": node_c_result}

    @staticmethod
    def _route_after_node_b(state: AgentGraphState) -> str:
        action = state.get("action", "ignore")
        return "continue" if action in {"forward", "modify"} else "stop"

