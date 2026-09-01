"""Agent Runtime · LangGraph 循环。

V0 没有独立 Planner：LLM 自己决定是否调用工具。
V0.6 再按当前问题检索知识库；V1 工具走 tools/registry.py 分组登记。

reason 是「推理」不是「原因」，来自 ReAct：想一轮 → 动手 → 看结果 → 再想。
图解与整条请求链路见 系统文档.md。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from model.llm import build_llm
from runtime.memory import prompt_block
from runtime.rag import prompt_block as rag_block
from runtime.prompts import SYSTEM_PROMPT
from tools import ALL_TOOLS


class AgentState(TypedDict):
    # add_messages：节点 return {"messages": [...]} 时是追加，不是整表覆盖
    messages: Annotated[list[BaseMessage], add_messages]


def _last_user_text(messages: list[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and isinstance(msg.content, str):
            return msg.content
    return ""


async def reason(state: AgentState) -> dict:
    """唯一调用 LLM 的节点。输出要么是最终回答，要么是 tool_calls。"""
    llm = build_llm().bind_tools(ALL_TOOLS)
    question = _last_user_text(state["messages"])
    system = (
        SYSTEM_PROMPT.replace(
            "__NOW__", datetime.now().astimezone().isoformat(timespec="seconds")
        )
        .replace("__MEMORIES__", prompt_block())
        .replace("__RAG__", rag_block(question))
    )
    # System 每轮现拼（记忆 + RAG）；state["messages"] 只是本会话短时历史
    response = await llm.ainvoke([SystemMessage(content=system), *state["messages"]])
    return {"messages": [response]}


def build_graph():
    """带回路的图，不是 while True。

    START → reason ─(有 tool_calls)→ tools → reason → …
                      └(没有)→ END
    """
    graph = StateGraph(AgentState)
    graph.add_node("reason", reason)
    # 只执行工具，不思考
    graph.add_node("tools", ToolNode(ALL_TOOLS)) 

    # 每条用户消息固定先想一轮
    graph.add_edge(START, "reason")  

    # tools_condition 不是节点，是路由器：有 tool_calls 去 tools，否则 END
    graph.add_conditional_edges("reason", tools_condition)

    # 观察结果后必须再 reason，才能开口回答
    graph.add_edge("tools", "reason")  
    return graph.compile()


GRAPH = build_graph()  # 启动时编译一次；请求里只 astream_events


def to_lc_messages(rows: list[dict]) -> list[BaseMessage]:
    """Postgres 里的 {role, content} → LangChain 消息。System 不在这里。"""
    out: list[BaseMessage] = []
    for row in rows:
        if row["role"] == "user":
            out.append(HumanMessage(content=row["content"]))
        elif row["role"] == "assistant":
            out.append(AIMessage(content=row["content"]))
    return out
