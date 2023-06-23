from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.utilities.google_search import GoogleSearchAPIWrapper
from llama_index.readers import BeautifulSoupWebReader
from bs4 import BeautifulSoup
from bs4.element import Comment
import re
import requests
from urllib.parse import urljoin
import openai

google_search = GoogleSearchAPIWrapper()

def link_results(query):
    return google_search.results(query,10)

def scraping(query):
    documents = BeautifulSoupWebReader().load_data(urls=[query])
    for i, document in enumerate(documents):
        text = re.sub(r'\n+', '\n', document.text)
        documents[i] = text[:1500]
    return documents

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def scrape_links_and_text(url):
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(['script', 'style', 'meta']):  # Remove these tags
        element.decompose()

    links = soup.find_all('a')

    result = ""
    for link in links:
        link_url = urljoin(url, link.get('href', ''))
        text = link.text.strip()
        result += f"{link_url} : {text}\n"

    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    result += " ".join(t.strip() for t in visible_texts)

    return result[:1500]  # Truncate the result string to 1500 characters

def generate_image(prompt):
    response = openai.Image.create(
        model="image-alpha-001",
        prompt=prompt,
        n=1,
        size="256x256",
        response_format="url"
    )
    
tools = [
    Tool(
        name = "Search",
        func= link_results,
        description="useful for when you need to answer questions about current events. it is single-input tool Search."
    ),
    Tool(
        name = "Links",
        func= scrape_links_and_text,
        description="It is a useful tool that can you to obtain a list of URLs by specifying a URL."
    ),
    Tool(
        name = "Scraping",
        func= scraping,
        description="it is a useful tool that can acquire content that does not contain a URL by giving a URL."
    ),
    Tool(
        name = "Painting",
        func= generate_image,
        description="It is a useful tool that can reply image URL based on the keyword by specifying the English keywords."
    ),
]

def langchain_agent(question,AI_MODEL):
    llm = ChatOpenAI(model=AI_MODEL)
    mrkl = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)
    try:
        result = mrkl.run(question)
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        # 何らかのデフォルト値やエラーメッセージを返す
        return "An error occurred while processing the question"
 
