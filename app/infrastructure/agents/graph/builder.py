from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.agents.nodes.classify_intent import classify_intent
from app.infrastructure.agents.nodes.memory_node import memory_node
from app.infrastructure.agents.nodes.proposal_node import proposal_node
from app.infrastructure.agents.nodes.rag_node import rag_node
from app.infrastructure.agents.nodes.respond_node import respond_node


def _route_after_rag(state: AgentState) -> str:
    return "proposal_node" if state["intent"] == "proposal" else "respond_node"


def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """
    Assembles and compiles the LangGraph state machine.
    Call once at app startup — the compiled graph is thread-safe and stateless.
    All per-conversation state lives in the Redis checkpointer keyed by thread_id.

    Flow:
        classify_intent → rag_node → (proposal_node | respond_node) → respond_node → memory_node → END
    """
    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("rag_node", rag_node)
    builder.add_node("proposal_node", proposal_node)
    builder.add_node("respond_node", respond_node)
    builder.add_node("memory_node", memory_node)

    builder.set_entry_point("classify_intent")

    # RAG always runs — both branches need retrieved context
    builder.add_edge("classify_intent", "rag_node")

    # Branch after RAG based on classified intent
    builder.add_conditional_edges(
        "rag_node",
        _route_after_rag,
        {"proposal_node": "proposal_node", "respond_node": "respond_node"},
    )

    # Proposal path rejoins respond_node
    builder.add_edge("proposal_node", "respond_node")

    # Final nodes always run
    builder.add_edge("respond_node", "memory_node")
    builder.add_edge("memory_node", END)

    return builder.compile(checkpointer=checkpointer)
