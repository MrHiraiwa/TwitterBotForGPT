import os
import re
import random
import tweepy
from google.cloud import firestore
from datetime import datetime, time, timedelta
import pytz
from flask import Flask, request, render_template, session, redirect, url_for, jsonify, abort
from langchainagent import langchain_agent
import unicodedata

API_KEY = os.getenv('API_KEY')
API_KEY_SECRET = os.getenv('API_KEY_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
admin_password = os.environ["ADMIN_PASSWORD"]

REQUIRED_ENV_VARS = [
    "ORDER",
]

DEFAULT_ENV_VARS = {
    'ORDER': """
あなたは、Twitter投稿者です。
「AI {nowDateStr}」のキーワードで検索して、{nowDateStr}のAI・人工知能関連のニュースを一つ選び、下記の条件に従ってツイートしてください。
条件:
-文字数はURLも含めて138文字以内にしてください。
-検索して発表する形で文書を書かずに、最初から知ってた体裁で書いてください。
-冒頭に「選んだ」「検索した」等の記載は不要です。
-文書の冒頭は「AIニュースちゃん:」から初めてください。
-ニュースだけを短く簡潔に書いてください。
-小学生にもわかりやすく書いてください。
-出力文 は口語体で記述してください。
-文脈に応じて、任意の場所で絵文字を使ってください。
-{nowDateStr}の記事がない場合は近い日付の記事を選択してください。
""",
}

client = tweepy.Client(
    consumer_key = API_KEY,
    consumer_secret = API_KEY_SECRET,
    access_token = ACCESS_TOKEN,
    access_token_secret = ACCESS_TOKEN_SECRET
)

db = firestore.Client()

def reload_settings():
    global order, nowDate, nowDateStr, jst
    jst = pytz.timezone('Asia/Tokyo')
    nowDate = datetime.now(jst)
    nowDateStr = nowDate.strftime('%Y年%m月%d日')
    ORDER = get_setting('ORDER').split(',')
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
    future = executor.submit(_create_tweet, 0)  # Futureオブジェクトを受け取ります
    try:
        future.result()  
    except Exception as e:
        print(f"Error: {e}")  # エラーメッセージを表示します
    return jsonify({"status": "Tweet creation started"}), 200

def _create_tweet(retry_count):
    if retry_count >= 5:
        print("Exceeded maximum retry attempts.")
        return

    result = langchain_agent(order)
    result = result.strip('"') 
    character_count = count_chars(result)
    if 1 <= character_count <= 280: 
        try:
            response = client.create_tweet(text = result)
            print(f"response : {response}")
        except tweepy.errors.TweepyException as e:
            print(f"An Tweep error occurred: {e}")
    else:
        print(f"character_count is {character_count} retrying...")
        _create_tweet(retry_count + 1)

def count_chars(s):
    count = 0
    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', s)
    s = re.sub('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', s)
    for c in s:
        try:
            char_name = unicodedata.name(c)
            if 'HIRAGANA' in char_name or 'KATAKANA' in char_name:
                count += 2
            elif ord(c) < 128:
                count += 1
            else:
                count += 2
        except ValueError:
            # For characters that do not have a Unicode name, we assume they are control characters
            count += 1

    count += len(urls) * 23 # Each URL is counted as 23 characters
    return count

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
