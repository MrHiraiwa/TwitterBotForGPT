from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.utilities.google_search import GoogleSearchAPIWrapper

llm = ChatOpenAI(model="gpt-4-0613")

google_search = GoogleSearchAPIWrapper()

def link_results(query):
    return google_search.results(query,10)
    

tools = [
    Tool(
        name = "Search",
        func=link_results,
        description="useful for when you need to answer questions about current events. it is single-input tool Search."
    ),
]

mrkl = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

def langchain_agent(question):
    result = mrkl.run(question)
    return result
  
