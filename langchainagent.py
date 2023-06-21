from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.utilities.google_search import GoogleSearchAPIWrapper
from llama_index.readers import BeautifulSoupWebReader

llm = ChatOpenAI(model="gpt-4-0613")

google_search = GoogleSearchAPIWrapper()

def link_results(query):
    return google_search.results(query,3)


def scraping(query):
    return BeautifulSoupWebReader().load_data(urls=[query])

tools = [
    Tool(
        name = "Search",
        func= link_results.run,
        description="useful for when you need to answer questions about current events. it is single-input tool Search."
    ),
    Tool(
        name = "Scraping",
        func= scraping.run,
        description="It is a tool that can get content from url."
    ),
]

mrkl = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

def langchain_agent(question):
    try:
        result = mrkl.run(question)
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        # 何らかのデフォルト値やエラーメッセージを返す
        return "An error occurred while processing the question"
 
