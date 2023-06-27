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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

# Seleniumの設定
options = Options()
options.add_argument("--headless")  
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# ユーザーエージェントを偽装する
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)  

google_search = GoogleSearchAPIWrapper()

image_result = []

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
    # 指定したURLに移動
    driver.get(url)
    
    # 任意の要素がロードされるまで待つ
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    result = ""

    # 初期フレームのリンクを取得
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all('a')
    for link in links:
        link_url = urljoin(url, link.get('href', ''))
        text = link.text.strip()

        if text not in url_links_filter:
        # 条件が成立する場合の処理
            result += f"{link_url} : {text}\n"

    # iframe内のリンクを取得
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    for i in range(len(iframes)):
        driver.switch_to.frame(iframes[i])
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        iframe_html = driver.page_source
        iframe_soup = BeautifulSoup(iframe_html, "html.parser")
        iframe_links = iframe_soup.find_all('a')
        for link in iframe_links:
            link_url = urljoin(url, link.get('href', ''))
            text = link.text.strip()
            if text not in url_links_filter:
                result += f"{link_url} : {text}\n"

        # iframe内のテキストも取得
        iframe_texts = iframe_soup.findAll(text=True)
        visible_texts = filter(tag_visible, iframe_texts)
        result += " ".join(t.strip() for t in visible_texts)

        driver.switch_to.default_content()

    return result[:2000]  

def generate_image(prompt):
    global image_result  # グローバル変数を使用することを宣言
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url"
    )
    image_result = response['data'][0]['url']  # グローバル変数に値を代入
    time.sleep(10)
    return 'generated the image. Images are tweeted separately from messages'

    
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
        description="It is a useful tool that can reply image URL based on the Sentence by specifying the Sentence."
    ),
]

def langchain_agent(question,AI_MODEL, URL_LINKS_FILTER):
    global url_links_filter
    url_links_filter = URL_LINKS_FILTER
    llm = ChatOpenAI(model=AI_MODEL)
    mrkl = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)
    try:
        result = mrkl.run(question)
        return result, image_result
    except Exception as e:
        print(f"An error occurred: {e}")
        # 何らかのデフォルト値やエラーメッセージを返す
        return "An error occurred while processing the question"
