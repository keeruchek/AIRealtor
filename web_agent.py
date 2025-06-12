# web_agent.py
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_community.chat_models import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

llm = ChatOllama(model="mistral")  # You can change to llama3 or any other local model

search = DuckDuckGoSearchRun()
tools = [
    Tool(
        name="Search",
        func=search.run,
        description="Useful for answering questions about current events or web data."
    )
]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def ask_web_ai(query):
    return agent.run(query)
