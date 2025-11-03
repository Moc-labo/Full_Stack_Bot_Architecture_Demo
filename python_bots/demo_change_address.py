# =============================================================================
# ポートフォリオ：【技術デモ】並列Web情報“変更”システム (Python版)
# =============================================================================
#
# 目的：
# このスクリプトは、「ThreadPoolExecutor（並列処理）」を使い、
# 複数のアカウントで同時に（並列で）Webサイトにログインし、
# CSV指示書に基づき、登録情報（例：メールアドレス）を
# 自動で「変更」する「技術（アーキテクチャ）」を実証するデモです。
#
# =============================================================================

import pandas as pd
import time
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from selenium.webdriver.common.keys import Keys # キーボード操作
import random

# ダミーの入力ファイル名を定義
INPUT_CSV = "demo_account_change_list.csv"
OUTPUT_CSV = "demo_account_change_list.csv" # 読み込み元に上書き保存

# ダミーのデモサイトURLを定義
LOGIN_URL = "https://login.example.com/users/sign_in"
EDIT_URL = "https://mypage.example.com/home/edit"
LOGOUT_URL = "https://login.example.com/users/sign_out"

# 並列処理中にCSVの読み書きが衝突するのを防ぐ「安全装置」
lock = Lock()

def init_driver():
    """ブラウザ（Chrome）を初期化する"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Bot検知を回避するための高度なオプション
    options.add_argument('--disable-blink-features=AutomationControlled')
    return webdriver.Chrome(options=options)

def login(driver, email, password):
    """ダミーのデモサイトにログインする"""
    try:
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "user_email"))).send_keys(email)
        driver.find_element(By.ID, "user_password").send_keys(password)
        driver.find_element(By.NAME, "commit").click()

        WebDriverWait(driver, 10).until(lambda d: "ログイン" not in d.title)
        
        page = driver.page_source
        if "ロボット認証" in page: return "robot"
        if "パスワードが違います" in page: return "invalid"
        return "success"
    except Exception as e:
        return f"login_exception: {str(e)}"

def change_email_demo(driver, current_email, new_email):
    """
    安全化された「メールアドレス変更」関数
    （元の `change_email` のロジックを抽象化）
    """
    try:
        driver.get(EDIT_URL)

        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", email_field)
        time.sleep(1)

        email_field.clear()
        time.sleep(0.5)

        # 「人間らしい」ランダムなタイピング速度で入力するロジック
        for char in new_email:
            email_field.send_keys(char)
            time.sleep(random.uniform(0.04, 0.08))

        time.sleep(0.5)
        email_field.send_keys(Keys.TAB)
        time.sleep(1)

        # 「更新」ボタンをクリック（ダミー）
        buttons = driver.find_elements(By.XPATH, '//input[@type="submit" and @value="更新"]')
        if len(buttons) >= 2:
            driver.execute_script("arguments[0].scrollIntoView(true);", buttons[1])
            time.sleep(1)
            buttons[1].click()
        else:
            return "更新ボタン見つからず"

        WebDriverWait(driver, 10).until(lambda d: "edit" in d.current_url or "Dashboard" in d.title)
        time.sleep(2)
        
        # 検証：再度編集ページにアクセスし、変更が反映されたか確認
        driver.get(EDIT_URL)
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        )
        updated_email = email_field.get_attribute("value").strip()

        if updated_email == new_email:
            return "変更済み"
        else:
            return "変更失敗"
    except Exception as e:
        return f"change_exception: {str(e)}"

def logout(driver):
    """ダミーのデモサイトからログアウトする"""
    try:
        driver.get(LOGOUT_URL)
        time.sleep(1)
    except Exception:
        pass

def process_account(row):
    """
    1つのアカウント（1スレッド）が実行するタスク
    """
    current_email = row['メールアドレス']
    password = row['パスワード']
    new_email = row['変更後メールアドレス']
    driver = None
    status = ""

    try:
        driver = init_driver()
        login_result = login(driver, current_email, password)

        if login_result == "success":
            status = change_email_demo(driver, current_email, new_email)
        elif login_result == "invalid":
            status = "ログイン失敗"
        elif login_result == "robot":
            status = "ロボット認証"
        else:
            status = f"ログイン異常: {login_result}"
        
        logout(driver)
    except Exception as e:
        status = f"例外: {str(e)}\n{traceback.format_exc(limit=1)}"
    finally:
        if driver:
            driver.quit()

    # 「安全装置（Lock）」を使って、CSVファイルに結果を書き込む
    with lock:
        df = pd.read_csv(OUTPUT_CSV, dtype=str)
        df.loc[df["メールアドレス"] == current_email, "変更済み"] = status
        df.to_csv(OUTPUT_CSV, index=False)

    print(f"[{current_email}] → {new_email} :: {status}")

def main():
    """
    メイン関数（並列処理の司令塔）
    """
    try:
        df = pd.read_csv(INPUT_CSV, dtype=str)
    except FileNotFoundError:
        print(f"❌ 入力ファイル（{INPUT_CSV}）が見つかりません。")
        return
        
    if "変更済み" not in df.columns:
        df["変更済み"] = ""
    df.fillna("", inplace=True)

    targets = df[df["変更済み"].isin(["", None])]
    print(f"🚀 並列情報変更システム（技術デモ）を開始します。")
    print(f"🕵️‍♂️ 変更対象: {len(targets)} 件")

    # 並列処理（ThreadPoolExecutor）
    with ThreadPoolExecutor(max_workers=10) as executor:
        # iterrows()から辞書に行を変換して渡す
        for _, row in targets.iterrows():
            executor.submit(process_account, row.to_dict())

    print("✅ 全処理が完了しました。")

if __name__ == "__main__":
    main()