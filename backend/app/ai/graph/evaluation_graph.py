from langgraph.graph import END, START, StateGraph
from app.ai.agents.coordinator import coordinator_node
from app.ai.agents.technical import technical_node
from app.ai.graph.state import EvaluationState


def build_evaluation_graph():
    graph = StateGraph(EvaluationState)
    graph.add_node("coordinador", coordinator_node)
    graph.add_node("tecnico", technical_node)
    graph.add_edge(START, "coordinador")
    graph.add_edge("coordinador", "tecnico")
    graph.add_edge("tecnico", END)
    return graph.compile()
