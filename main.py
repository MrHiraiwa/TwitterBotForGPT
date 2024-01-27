import os
from io import BytesIO
import re
import random
import tweepy
from google.cloud import firestore
from datetime import datetime, time, timedelta
import pytz
from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from langchainagent import langchain_agent
import unicodedata
from twitter_text import parse_tweet
import requests

API_KEY = os.getenv('API_KEY')
API_KEY_SECRET = os.getenv('API_KEY_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
admin_password = os.environ["ADMIN_PASSWORD"]

REQUIRED_ENV_VARS = [
    "ORDER",
    "AI_MODEL",
    "REGENERATE_ORDER",
    "REGENERATE_COUNT",
    "URL_LINKS_FILTER",
    "READ_TEXT_COUNT",
    "READ_LINKS_COUNT",
    "PAINTING",
]

DEFAULT_ENV_VARS = {
    'AI_MODEL': 'gpt-4',
    'ORDER': """
あなたは、Twitter投稿者です。
検索は行わずに次のURLからURLのリストを読み込んで{nowDateStr}のAI関連のニュースを一つ選び、下記の条件に従ってツイートしてください。
URL:
https://news.google.com/search?q=ai%20when%3A3h&hl=ja&gl=JP&ceid=JP%3Aja
条件:
-{nowDateStr}の記事がない場合は近い日付の記事を選択してください。
-ツイートする文字数はURLを除いて117文字以内にしてください。
-検索して発表する形で文書を書かずに、最初から知ってた体裁で書いてください。
-冒頭に「選んだ」「検索した」等の記載は不要です。
-文書の冒頭は「AIニュースちゃん:」から初めてください。
-ニュースだけを短く簡潔に書いてください。
-記事の参照元URLを短縮URLとしないで、そのまま提示してください。
-小学生にもわかりやすく書いてください。
-出力文 は口語体で記述してください。
-文脈に応じて、任意の場所で絵文字を使ってください。
画像を生成しないでください。
""",
    'REGENERATE_ORDER': '以下の文章はツイートするのに長すぎました。少し短くして出力してください。文書の冒頭の「AIニュースちゃん:」とURLは変更せずに維持してください。',
    'REGENERATE_COUNT': '5',
    'URL_LINKS_FILTER': 'マイページ,ログイン,新規取得,ヘルプ,Yahoo! JAPAN,キッズ,WORLD,ハートネット,アーカイブス,語学,ラーニング,for School,スポーツ,ラジオ,NHK_PR,音楽,アニメ,ドラマ,天気,健康,コロナ・感染症コロナ・感染,番組表番組表,受信料の窓口,NHKプラス,番組表,ニュース,コロナ・感染症,NHKについて,NHK,ホーム,おすすめ,フォロー中,ニュース ショーケース,日本,世界,世界,ビジネス,科学＆テクノロジー,エンタメ,購入履歴,トップ,速報,ライブ,個人,オリジナル,みんなの意見,ランキング,有料,ローカル,ウェザーニュース,トップニュース,すべての記事,Yahoo!ニュース,＠IT',
    'READ_TEXT_COUNT': '1000',
    'READ_LINKS_COUNT': '2000',
    'PAINTING': 'False',
}
auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

client = tweepy.Client(
    consumer_key = API_KEY,
    consumer_secret = API_KEY_SECRET,
    access_token = ACCESS_TOKEN,
    access_token_secret = ACCESS_TOKEN_SECRET
)

db = firestore.Client()

def reload_settings():
    global order, nowDate, nowDateStr, jst, AI_MODEL, REGENERATE_ORDER, REGENERATE_COUNT, URL_LINKS_FILTER
    global READ_TEXT_COUNT,READ_LINKS_COUNT, PAINTING
    jst = pytz.timezone('Asia/Tokyo')
    nowDate = datetime.now(jst)
    nowDateStr = nowDate.strftime('%Y年%m月%d日')
    AI_MODEL = get_setting('AI_MODEL')
    ORDER = get_setting('ORDER').split(',')
    REGENERATE_ORDER = get_setting('REGENERATE_ORDER')
    REGENERATE_COUNT = int(get_setting('REGENERATE_COUNT') or 5)
    URL_LINKS_FILTER = get_setting('URL_LINKS_FILTER').split(',')
    READ_TEXT_COUNT = int(get_setting('READ_TEXT_COUNT') or 1000)
    READ_LINKS_COUNT = int(get_setting('READ_LINKS_COUNT') or 2000)
    PAINTING = get_setting('PAINTING')
    order = random.choice(ORDER)  # ORDER配列からランダムに選択
    order = order.strip()  # 先頭と末尾の改行コードを取り除く
    if '{nowDateStr}' in order:
        order = order.format(nowDateStr=nowDateStr)

def get_setting(key):
    doc_ref = db.collection(u'settings').document('app_settings')
    doc = doc_ref.get()

    if doc.exists:
        doc_dict = doc.to_dict()
        if key not in doc_dict:
            # If the key does not exist in the document, use the default value
            default_value = DEFAULT_ENV_VARS.get(key, "")
            doc_ref.set({key: default_value}, merge=True)  # Add the new setting to the database
            return default_value
        else:
            return doc_dict.get(key)
    else:
        # If the document does not exist, create it using the default settings
        save_default_settings()
        return DEFAULT_ENV_VARS.get(key, "")
  
def save_default_settings():
    doc_ref = db.collection(u'settings').document('app_settings')
    doc_ref.set(DEFAULT_ENV_VARS, merge=True)

def update_setting(key, value):
    doc_ref = db.collection(u'settings').document('app_settings')
    doc_ref.update({key: value})
    
reload_settings()    

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', default='YOUR-DEFAULT-SECRET-KEY')

from flask_executor import Executor
executor = Executor(app)

@app.route('/login', methods=['GET', 'POST'])
def login():
    attempts_doc_ref = db.collection(u'settings').document('admin_attempts')
    attempts_doc = attempts_doc_ref.get()
    attempts_info = attempts_doc.to_dict() if attempts_doc.exists else {}

    attempts = attempts_info.get('attempts', 0)
    lockout_time = attempts_info.get('lockout_time', None)

    # ロックアウト状態をチェック
    if lockout_time:
        if datetime.now(jst) < lockout_time:
            return render_template('login.html', message='Too many failed attempts. Please try again later.')
        else:
            # ロックアウト時間が過ぎたらリセット
            attempts = 0
            lockout_time = None

    if request.method == 'POST':
        password = request.form.get('password')

        if password == admin_password:
            session['is_admin'] = True
            # ログイン成功したら試行回数とロックアウト時間をリセット
            attempts_doc_ref.set({'attempts': 0, 'lockout_time': None})
            return redirect(url_for('settings'))
        else:
            attempts += 1
            lockout_time = datetime.now(jst) + timedelta(minutes=10) if attempts >= 5 else None
            attempts_doc_ref.set({'attempts': attempts, 'lockout_time': lockout_time})
            return render_template('login.html', message='Incorrect password. Please try again.')
        
    return render_template('login.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'is_admin' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    current_settings = {key: get_setting(key) or DEFAULT_ENV_VARS.get(key, '') for key in REQUIRED_ENV_VARS}

    if request.method == 'POST':
        for key in REQUIRED_ENV_VARS:
            value = request.form.get(key)
            if value:
                update_setting(key, value)
        return redirect(url_for('settings'))
    return render_template(
    'settings.html', 
    settings=current_settings, 
    default_settings=DEFAULT_ENV_VARS, 
    required_env_vars=REQUIRED_ENV_VARS
    )

@app.route('/tweet')
def create_tweet():
    reload_settings()
    future = executor.submit(generate_tweet, 0, None)  # Futureオブジェクトを受け取ります
    try:
        future.result()  
    except Exception as e:
        print(f"Error: {e}")  # エラーメッセージを表示します
    return jsonify({"status": "Tweet creation started"}), 200

def generate_tweet(retry_count, result):
    image_result = []
    if retry_count >= REGENERATE_COUNT:
        print("Exceeded maximum retry attempts.")
        return
    
    if result is None:
        # First attempt
        instruction = order
    else:
        # Retry
        instruction = REGENERATE_ORDER + "\n" + result

    result, image_result = langchain_agent(instruction, AI_MODEL, URL_LINKS_FILTER, READ_TEXT_COUNT, READ_LINKS_COUNT, PAINTING)
    result = result.strip('"') 
    character_count = int(parse_tweet(result).weightedLength)
    
    if 1 <= character_count <= 280: 
        try:
            if image_result:
                # Download image from URL
                response = requests.get(image_result)
                img_data = BytesIO(response.content)
                # Upload image to Twitter
                media = api.media_upload(filename='image.jpg', file=img_data)
                # Tweet with image
                response = client.create_tweet(text=result, media_ids=[media.media_id])
                print(f"response : {response} and image")
            else:
                response = client.create_tweet(text = result)
                print(f"response : {response}")
        except tweepy.errors.TweepyException as e:
            print(f"An Tweep error occurred: {e}")
    else:
        print(f"character_count is {character_count} retrying...")
        generate_tweet(retry_count + 1, result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
