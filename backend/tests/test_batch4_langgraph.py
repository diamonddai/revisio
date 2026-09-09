from app.agents.llm_client import LLMClient
from app.graph.langgraph_runner import LangGraphRunner
from app.graph.workflow import NodeA, NodeB, NodeC


def _build_runner() -> LangGraphRunner:
    llm = LLMClient(enabled=False)
    return LangGraphRunner(node_a=NodeA(llm), node_b=NodeB(llm), node_c=NodeC())


def test_langgraph_continue_route_has_node_c_output() -> None:
    runner = _build_runner()
    state = runner.run(
        persona={"category": "Analyst"},
        context={"topic": "science"},
        whitelist=["change_title", "add_annotation", "add_data_variables"],
        shift_prior="sig",
    )
    assert state["node_b_result"]["action"] in {"forward", "modify"}
    assert "node_c_result" in state


def test_langgraph_stop_route_without_node_c_output() -> None:
    runner = _build_runner()
    state = runner.run(
        persona={"category": "Noise"},
        context={"topic": "science"},
        whitelist=["change_title"],
        shift_prior="none",
    )
    assert state["node_b_result"]["action"] == "ignore"
    assert "node_c_result" not in state

