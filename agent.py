from typing import Annotated
from langchain_ollama import ChatOllama
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

from tools import tools

memory = InMemorySaver()
llm = ChatOllama(model="llama3.1")
agent = create_react_agent(llm, tools, checkpointer=memory)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    return {"messages": [agent.invoke(state["messages"])]}


def invoke_graph_updates(user_input: str, config: dict):
    # The config is the **second positional argument** to stream() or invoke()!
    events = agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        stream_mode="values",
    )
    return events["messages"][-1].content


def stream_graph_pretty(user_input: str, config: dict):
    # The config is the **second positional argument** to stream() or invoke()!
    events = agent.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        stream_mode="values",
    )
    for event in events:
        event["messages"][-1].pretty_print()


while True:
    config = {"configurable": {"thread_id": "1"}}
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    if user_input.lower() in ["s"]:
        for state in agent.get_state_history(config):
            print("Num Messages: ", len(state.values["messages"]), "Next: ", state.next, "Message:", state.values["messages"])
        continue
    #stream_graph_pretty(user_input, config)
    print("Assistant: ", invoke_graph_updates(user_input, config))
