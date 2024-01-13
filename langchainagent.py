from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain_community.chat_models import ChatOpenAI
from langchain_community.utilities.google_search import GoogleSearchAPIWrapper
from llama_index.readers import BeautifulSoupWebReader
from bs4 import BeautifulSoup
from bs4.element import Comment
import re
import requests
from urllib.parse import urljoin
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
from google.cloud import firestore
from datetime import datetime, timedelta
import urllib.parse

# Firestore clientの初期化
db = firestore.Client()


def create_firestore_document_id_from_url(url):
    return urllib.parse.quote_plus(url)

def add_url_to_firestore(url):
    url = create_firestore_document_id_from_url(url)
    doc_ref = db.collection('scraped_urls').document(url)
    doc_ref.set({
        'added_at': datetime.now()
    })

    # URLを一週間後に削除するタスクをスケジュール
    delete_at = datetime.now() + timedelta(weeks=1)
    doc_ref.update({
        'delete_at': delete_at
    })
    
def check_url_in_firestore(url):
    url = create_firestore_document_id_from_url(url)
    doc_ref = db.collection('scraped_urls').document(url)
    doc = doc_ref.get()
    return doc.exists

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
url_links_filter = []
read_text_count = []
read_links_count = []
painting_enable = []

def link_results(query):
    return google_search.results(query,10)


def scraping(url):
    retries = 3  # Maximum number of retries
    for attempt in range(retries):
        try:
            # 指定したURLに移動
            driver.get(url)

            # 任意の要素がロードされるまで待つ
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            texts = soup.findAll(text=True)
            visible_texts = filter(tag_visible, texts)
            result = " ".join(t.strip() for t in visible_texts)

            # Remove extra whitespace by splitting and joining
            result = ' '.join(result.split())
            add_url_to_firestore(url)
            print(result[:read_text_count])
            return result[:read_text_count]  

        except Exception as e:
            if attempt < retries - 1:  # if it's not the last attempt
                time.sleep(10)  # wait for 10 seconds before retrying
                continue
            else:
                raise e

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def scrape_links_and_text(url):
    retries = 3  # Maximum number of retries
    for attempt in range(retries):
        try:
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

                # URLがフィルタリストになく、またFirestoreに存在しない場合のみ、結果にリンクとテキストを追加
                if text not in url_links_filter and not check_url_in_firestore(link_url):
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

                    # URLがフィルタリストになく、またFirestoreに存在しない場合のみ、結果にリンクとテキストを追加
                    if text not in url_links_filter and not check_url_in_firestore(link_url):
                        result += f"{link_url} : {text}\n"

                # iframe内のテキストも取得
                iframe_texts = iframe_soup.findAll(text=True)
                visible_texts = filter(tag_visible, iframe_texts)
                result += " ".join(t.strip() for t in visible_texts)

                driver.switch_to.default_content()

            return result[:read_links_count]  

        except Exception as e:
            if attempt < retries - 1:  # if it's not the last attempt
                time.sleep(10)  # wait for 10 seconds before retrying
                continue
            else:
                raise e

def generate_image(prompt):
    if painting_enable == 'False':
        return 
    global image_result  # グローバル変数を使用することを宣言
    client = OpenAI()
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_result = response.data[0].url
    except Exception as e:
        return e    

    return 'generated the image.'

    
tools = [
    Tool(
        name = "Search",
        func= link_results,
        description="useful for when you need to answer questions about current events. it is single-input tool Search."
    ),
    Tool(
        name = "Links",
        func= scrape_links_and_text,
        description="It is a useful tool that can you to obtain a list of URLs by specifying a URL. it is single-input tool."
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

def langchain_agent(question,AI_MODEL, URL_LINKS_FILTER, READ_TEXT_COUNT, READ_LINKS_COUNT, PAINTING):
    global url_links_filter, read_text_count, read_links_count, painting_enable
    url_links_filter = URL_LINKS_FILTER
    read_text_count = READ_TEXT_COUNT
    read_links_count = READ_LINKS_COUNT
    painting_enable = PAINTING
    llm = ChatOpenAI(model=AI_MODEL)
    mrkl = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)
    try:
        result = mrkl.run(question)
        return result, image_result
    except Exception as e:
        print(f"An error occurred: {e}")
        # 何らかのデフォルト値やエラーメッセージを返す
        return "An error occurred while processing the question"
