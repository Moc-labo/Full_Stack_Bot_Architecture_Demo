# 🚀 【技術デモ】マルチ言語・並列処理Webボットシステム

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg?style=for-the-badge&logo=python" alt="Python 3.12">
  &nbsp;
  <img src="https://img.shields.io/badge/Node.js-18-green.svg?style=for-the-badge&logo=node.js" alt="Node.js 18">
  &nbsp;
  <img src="https://img.shields.io/badge/Selenium-4.21-darkgreen.svg?style=for-the-badge&logo=selenium" alt="Selenium">
  &nbsp;
  <img src="https://img.shields.io/badge/Puppeteer-22.10-blue.svg?style=for-the-badge&logo=puppeteer" alt="Puppeteer">
  &nbsp;
  <img src="https://img.shields.io/badge/AI_Integration-2Captcha-red.svg?style=for-the-badge" alt="AI Integration (2Captcha)">
</p>

## 1. プロジェクト概要：AI時代の自動化アーキテクチャ

このプロジェクトは、「**Python（バックエンド処理）**」と「**Node.js（フロントエンド自動化）**」という2つの異なる言語を使いこなし、「**AI（reCAPTCHA解析）**」と「**並列処理**」を組み合わせて構築した、Webアカウント管理システムの「技術デモ」です。

特定のWebサイトを対象としたものではなく、あらゆるWebシステムに応用可能な「**設計思想（アーキテクチャ）**」と「**技術力**」を証明するために公開しています。

### システム構成図
(https://via.placeholder.com/900x400/f0f0f0/333333?text=ここに「システム構成図（スクリーンショット 2025-11-03 15.35.35.png）」を挿入)

---

## 2. 実装された「4つの主力コンポーネント」

### A. 【Node.js】AI連携・並列アカウント“生成”ボット
* **担当コード:** `nodejs_bots/demo_parallel_register_ai.js`
* **目的:** AIと連携し、reCAPTCHAのあるWebフォームに「並列」で自動登録する。
* **設計（技術）:**
    * **Bot検知回避:** `puppeteer-extra-plugin-stealth` を使用し、ブラウザ自動化ツールがWebサイトに「ボットである」と検知されるのを回避します。
    * **AI連携 (XAI):** `solveRecaptcha` 関数を設計。`axios` で「2Captcha（AI）」 にAPIリクエストを発注し、`sitekey`（問題用紙） を渡し、AIが解いた「解答（`token`）」 を`page.evaluate` で解答欄に自動入力します。
    * **並列処理:** `Promise.allSettled` の設計思想に基づき、`CONCURRENCY = 5`（例）のアカウント作成処理を「同時に（並列で）」実行し、スループット（処理速度）を最大化します。
    * **システム連携:** 成功したアカウント情報を`output.csv` に出力し、後続のPythonシステムへの「指示書」とします。

### B. 【Node.js】メールサーバー自動認証ボット
* **担当コード:** `nodejs_bots/demo_email_autoverify.js`
* **目的:** Webサイトから送信される「認証メール」を自動で検知し、認証URLを自動でクリックする。
* **設計（技術）:**
    * **サーバーサイド連携:** `imap-simple` を使い、ブラウザではアクセスできない「メールサーバー（IMAP）」 に直接接続します。
    * **自動解析:** `UNSEEN`（未読） かつ「特定の件名」 のメールを自動で検索し、`simpleParser` でメール本文を解析し、正規表現（`match(/https?:\/\/[^\s"]+/)`）で「認証URL」 だけを抜き出します。
    * **システム連携:** 抜き出したURLに`puppeteer` で自動アクセスし、アカウントの認証を完了させます。

### C. 【Python】並列・アカウント“情報登録”ワーカー
* **担当コード:** `python_bots/demo_main_register.py`, `demo_register_worker.py`
* **目的:** Node.jsが作成したアカウント群に対し、Pythonで「並列」にログインし、詳細情報（住所・電話番号など）を書き込む。
* **設計（技術）:**
    * **システム間連携:** `demo_main_register.py`（司令塔） が、Node.js部隊の`output.csv` を読み込み、処理対象を決定します。
    * **並列処理（`multiprocessing`）:** Pythonの`multiprocessing.Process` を採用。PCのCPUコアを最大限に活用し、複数の「作業員（`demo_register_worker.py`）」 プロセスを同時に起動し、`Selenium` でのプロフィール更新を「並列」で実行します。
    * **安全設計（`FileLock`）:** 複数の作業員が「同時に」CSV（指示書）を読み書きするとデータが壊れるため、`FileLock`（ファイルロック）という技術で「読み書きの瞬間だけは1人ずつ」と厳密に制御し、並列処理の「速度」と「安全性」を両立させています。

### D. 【Python】並列・アカウント“巡回”ボット
* **担当コード:** `python_bots/demo_parallel_patrol.py`
* **目的:** 多数のアカウントのステータス（認証済みか？応募済みか？）を、`Selenium` で「並列」に自動巡回・監視する。
* **設計（技術）:**
    * **最適な並列技術の「使い分け」:**
        `C`の「情報登録」はCPU負荷が高いため`multiprocessing` を使いました。
        しかし、「情報巡回」はWebサイトの応答を「待つ」時間がほとんど（I/Oバウンド）です。
        ここでは、その特性に合わせ、**よりメモリ効率の良い「`ThreadPoolExecutor`（スレッドプール）」** を`max_workers=10` で採用。**「作業の“種類”に応じて、最適な“並列技術”を使い分ける」**という、高度なアーキテクチャ設計を実装しています。
    * **安全設計（`threading.Lock`）:** `C`と同様に、`threading.Lock` を使い、並列スレッドがCSVファイル（住所録）の読み書きで衝突（競合）しないよう、安全性を担保しています。

---

## 5. 実行手順（技術デモ）

このリポジトリのコードは、実際のサイト名などの固有名詞を「`example.com`」などに書き換えた「技術デモ版」です。

### A. Python (`python_bots` フォルダ)
1.  `cd python_bots`
2.  `pip install -r requirements.txt` を実行し、必要な「道具（ライブラリ）」をインストールします。
3.  `demo_list_splitter.py` を実行し、ダミーの住所録（指示書）を生成します。
4.  `demo_main_register.py` を実行すると、並列情報登録の「技術デモ」が開始されます。

### B. Node.js (`nodejs_bots` フォルダ)
1.  `cd nodejs_bots`
2.  `npm install` を実行し、`package.json` に基づき必要な「道具（ライブラリ）」をインストールします。
3.  `.env.example` をコピーし、`.env` ファイルを作成します。
4.  `.env` ファイルに、ご自身の`IMAP_PASSWORD`や`CAPTCHA_API_KEY`を記述します。
5.  `npm run start:register` を実行すると、「AI連携・並列登録ボット」の「技術デモ」が開始されます。
