# 🚀 マルチ言語・並列処理Web自動化システム（技術デモ）

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg?style=for-the-badge&logo=python" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Node.js-18-green.svg?style=for-the-badge&logo=node.js" alt="Node.js 18">
  <img src="https://img.shields.io/badge/Selenium-4.21-darkgreen.svg?style=for-the-badge&logo=selenium" alt="Selenium">
  <img src="https://img.shields.io/badge/Puppeteer-22.10-blue.svg?style=for-the-badge&logo=puppeteer" alt="Puppeteer">
  <img src="https://img.shields.io/badge/AI_Integration-2Captcha-red.svg?style=for-the-badge" alt="AI Integration (2Captcha)">
</p>

## 1. プロジェクト概要
「Python（バックエンド）」と「Node.js（フロント）」という2つの言語を連携させ、「AI（reCAPTCHA解析）」と「高度な並列処理」を組み込んだWeb自動化システムの「技術デモ」である。特定のサイトを対象とせず、あらゆるWebシステムに応用可能な「設計思想（アーキテクチャ）」の証明を目的とする。

## 2. P：課題・背景 (Problem)
本プロジェクトは、あるWebサービスの複雑な認証システムに純粋な技術的興味を持ち、「もしAIを活用してこのプロセスを自動化するとしたら、自分ならどう設計するか」という**パーソナル・プロジェクト** [cite: 1-195-199] として開始した。

挑戦した技術的課題は以下の3点である。
1.  **AI認証の突破:** `hCaptcha/reCAPTCHA`（画像認証）の突破が必須。
2.  **リアルタイム連携:** 登録時に送信される「時間制限付きの認証URL」を、サーバーサイド（IMAP）で即座に検知し、クリックする必要がある。
3.  **異言語連携:** 上記プロセスは、フロントエンド操作（Node.js）とバックエンド処理（Python）の複雑な連携・並列処理を要する。

## 3. A：システム構成・設計 (Action)
上記課題を解決するため、「**責務の分離（Python / Node.js）**」と「**最適な並列技術の選択**」を軸としたアーキテクチャを設計した。

### システム構成図
![Web操作_ポートフォリオ_構造図](https://github.com/user-attachments/assets/1edf079f-229a-495d-8f5b-fa0e7b8468f4)


### A-1. 【Node.js】AI連携・並列アカウント“生成”ボット
* **担当:** `nodejs_bots/demo_parallel_register_ai.js`
* **目的:** AIと連携し、reCAPTCHAのあるWebフォームに「並列」で自動登録する。
* **設計:**
    * **Bot検知回避:** `puppeteer-extra-plugin-stealth` を使用し、ブラウザ自動化ツールの検知を回避する。
    * **AI連携:** `solveRecaptcha` 関数を設計。`axios` で「2Captcha（AI）」にAPIリクエストを発注し、AIが解いた「解答（`token`）」を`page.evaluate`で解答欄に自動入力する。
    * **並列処理:** `Promise.allSettled` の設計思想に基づき、`CONCURRENCY = 5`（例）の処理を「同時に（並列で）」実行し、スループットを最大化する。
    * **システム連携:** 成功したアカウント情報を`output.csv`に出力し、後続のPythonシステムへの「指示書」とする。

### A-2. 【Node.js】メールサーバー自動認証ボット
* **担当:** `nodejs_bots/demo_email_autoverify.js`
* **目的:** Webサイトから送信される「認証メール」を自動で検知し、認証URLを自動でクリックする。
* **設計:**
    * **サーバーサイド連携:** `imap-simple` を使い、ブラウザではアクセスできない「メールサーバー（IMAP）」に直接接続する。
    * **自動解析:** `UNSEEN`（未読）かつ「特定の件名」のメールを自動で検索し、`simpleParser`でメール本文を解析。正規表現（`match(/https?:\/\/[^\s"]+/)`）で「認証URL」のみを抜き出す。
    * **システム連携:** 抜き出したURLに`puppeteer`で自動アクセスし、アカウントの認証を完了させる。

### A-3. 【Python】並列・アカウント“情報登録”ワーカー
* **担当:** `python_bots/demo_main_register.py`, `demo_register_worker.py`
* **目的:** Node.jsが作成したアカウント群に対し、Pythonで「並列」にログインし、詳細情報（住所・電話番号など）を書き込む。
* **設計:**
    * **システム間連携:** `demo_main_register.py`（司令塔）が、Node.js部隊の`output.csv`を読み込み、処理対象を決定する。
    * **並列処理（`multiprocessing`）:** Pythonの`multiprocessing.Process`を採用。PCのCPUコアを最大限に活用し、複数の「作業員（`demo_register_worker.py`）」プロセスを同時に起動し、`Selenium`でのプロフィール更新を「並列」で実行する。
    * **安全設計（`FileLock`）:** 複数の作業員が「同時に」CSV（指示書）を読み書きするとデータが壊れるため、`FileLock`で「読み書きの瞬間だけは1人ずつ」と厳密に制御し、並列処理の「速度」と「安全性」を両立させている。

### A-4. 【Python】並列・アカウント“巡回”ボット
* **担当:** `python_bots/demo_parallel_patrol.py`
* **目的:** 多数のアカウントのステータスを、`Selenium`で「並列」に自動巡回・監視する。
* **設計（最適な並列技術の「使い分け」）:**
    `A-3`の「情報登録」はCPU負荷が高いため`multiprocessing`を採用した。しかし、「情報巡回」はWebサイトの応答を「待つ」時間がほとんど（I/Oバウンド）である。
    ここでは、その特性に合わせて**よりメモリ効率の良い「`ThreadPoolExecutor`（スレッドプール）**」を`max_workers=10`で採用。「**作業の“種類”に応じて、最適な“並列技術”を使い分ける**」という、高度なアーキテクチャ設計を実装している。

## 4. R：成果 (Result)
プログラミング言語の知識ゼロからスタートし、AIを「壁打ち相手」に、「**フロントエンド(JS)」「バックエンド(Python)」「メールサーバー(IMAP)**」を連携させた複雑な並列処理システムを独力で構築・完遂した。

この「パーソナル・プロジェクト」を通じて、AIを活用した要件定義と、複雑な異言語間システムの構築スキルを習得した。

## 5. 実行手順（技術デモ）
このリポジトリのコードは、実際のサイト名などの固有名詞を「`example.com`」などに書き換えた「技術デモ版」である。

### A. Python (`python_bots` フォルダ)
1.  `cd python_bots`
2.  `requirements.txt` に基づき、必要なライブラリをインストールする。
    ```bash
    pip install -r requirements.txt
    ```
3.  `demo_main_register.py` を実行すると、並列情報登録の「技術デモ」が開始される。

### B. Node.js (`nodejs_bots` フォルダ)
1.  `cd nodejs_bots`
2.  `package.json` に基づき、必要なライブラリをインストールする。
    ```bash
    npm install
    ```
3.  `.env.example` をコピーし、`.env` ファイルを作成する。
4.  `.env` ファイルに、ご自身の`IMAP_PASSWORD`や`CAPTCHA_API_KEY`を記述する。
5.  `package.json` のスクリプトを実行する。
    ```bash
    # AI連携・並列登録ボットのデモ
    npm run start:register
    
    # メール自動認証ボットのデモ
    npm run start:verify
    ```

## 6. 使用技術
* **Python:** Selenium, Pandas, Multiprocessing, ThreadPoolExecutor, FileLock
* **Node.js:** Puppeteer (puppeteer-extra, stealth-plugin), IMAP-Simple, Axios
* **AI連携:** 2Captcha (reCAPTCHA / hCaptcha 解析)
* **その他:** CSV, .env, JavaScript
