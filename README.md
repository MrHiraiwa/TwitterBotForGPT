# TwitterBotForGPT

このリポジトリは、Cloudrun上で動作するPythonベースのTwitterボットです。このボットはChatGPT APIを使用して、WEB上の最新情報をTwitter上にツイートします。
このボットプログラムの機能や設置方法についての詳細は以下のページを確認してください。
URL

## 機能
以下の機能を持っています。：

-ツイート機能: 指定したページやWEB検索の結果を元につぶやきます。
-スケジュール機能: このスクリプトの機能というよりはGoogle Cloud Platformの機能になりますが決まった時間にツイートします。

## セットアップ
以下のステップに従ってセットアップしてください：
1. Google Cloud Runでデプロイします：Google Cloud Consoleでプロジェクトを作成しCloud Run APIを有効にし、本レポジトリを指定してデプロイします。 デプロイの際は以下の環境変数を設定する必要があります。
2. 同じプロジェクト内でFirestoreを有効にします：左側のナビゲーションメニューで「Firestore」を選択し、Firestoreをプロジェクトで有効にします。
3. データベースを作成します：Firestoreダッシュボードに移動し、「データベースの作成」をクリックします。「ネイティブ」モードを選択します。
4. Custom SearchのAPIを有効にします。
5. Cloud RunのURLに「/login」を付与して管理画面にログインし、パラメータを設定します
7. TwitterのAPIを有効にし4つのKEY情報を環境変数に登録します。

## 環境変数
- API_KEY: TwitterのAPIキーを入力してください。
- API_KEY_SECRET: TwitterのAPIキーシークレットを入力してください。
- ACCESS_TOKEN: Twitterのアクセストークンを入力してください。
- ACCESS_TOKEN_SECRET: Twitterのアクセストークンシークレットを入力してください。
- OPENAI_APIKEY: OpenAIのAPIキーを入力してください。
- GOOGLE_API_KEY: Google Cloud Pratformに発行したAPIキーを入力してください。
-GOOGLE_CSE_ID: Google Cloud PratformのCustom Search設定時に発行した検索エンジンIDを設定してください。
- ADMIN_PASSWORD: WEBの管理画面のログインに使用する管理者パスワードです。このシステムはインターネットから誰でも触れるので、必ず複雑なパスワードを設定してください。

## 注意
このアプリケーションはFlaskベースで作成されています。そのため、任意のウェブサーバー上にデプロイすることが可能ですが、前提としてはGoogle Cloud runでの動作を想定しています。デプロイ方法は使用するウェブサーバーによります。

Google Cloud run以外で動作させる場合はFirestoreとの紐づけが必要になります。

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。
