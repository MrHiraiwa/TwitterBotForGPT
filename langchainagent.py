from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.utilities.google_search import GoogleSearchAPIWrapper
from llama_index.readers import BeautifulSoupWebReader
import re

llm = ChatOpenAI(model="gpt-4-0613")

google_search = GoogleSearchAPIWrapper()

def link_results(query):
    return google_search.results(query,10)

def scraping(query):
    documents = BeautifulSoupWebReader().load_data(urls=[query])
    for i, document in enumerate(documents):
        text = re.sub(r'\n+', '\n', document.text)
        documents[i] = text[:1500]
    return documents


tools = [
    Tool(
        name = "Search",
        func= link_results,
        description="useful for when you need to answer questions about current events. it is single-input tool Search."
    ),
    Tool(
        name = "Scraping",
        func= scraping,
        description="It is a useful tool that can acquire content by giving a URL."
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
 
