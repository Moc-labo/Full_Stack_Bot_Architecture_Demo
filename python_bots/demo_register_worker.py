# =============================================================================
# ポートフォリオ：【技術デモ】並列処理ワーカー (Python 作業員)
# =============================================================================
#
# 目的：
# このスクリプトは、「司令塔（demo_main_register.py）」から呼び出され、
# 「並列」で実行される「作業員」のデモです。
#
# SeleniumでWebサイトにログインし、CSVから読み込んだ「住所」や「電話番号」を
# プロフィール欄に自動入力する「RPAロジック」を実証します。
#
# =============================================================================

import sys
import pandas as pd
import random
import os
import time
import json
from datetime import datetime
from filelock import FileLock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ★ 安全化：ダミーのデモサイトURLを定義
LOGIN_URL = "https://login.example.com/users/sign_in"
EDIT_URL = "https://mypage.example.com/home/edit"
LOGOUT_URL = "https://login.example.com/users/sign_out"
INPUT_CSV = "demo_accounts_input.csv" # (司令塔とファイル名を合わせる)

# --- ログ出力 ---
def log(message):
    ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    msg = f"{ts} [PID: {os.getpid()}] {message}" # PID (プロセスID) をログに出力
    print(msg)
    with open("demo_register_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# --- ドライバ初期化 ---
def init_driver():
    opts = Options()
    opts.add_argument('--headless') # サーバー実行用
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=opts)

# --- ユーティリティ ---
def wait_for_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        return None

def js_click(driver, elem):
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", elem)

def safe_get(driver, url, retries=3, delay=3):
    for i in range(retries):
        try:
            driver.get(url)
            return
        except WebDriverException as e:
            log(f"[警告] ページ取得失敗 {i+1}/{retries}")
            time.sleep(delay)
    raise Exception(f"ページ取得に失敗: {url}")

# --- ログイン処理（安全化） ---
def login_demo(driver, email, password):
    safe_get(driver, LOGIN_URL)
    driver.delete_all_cookies()
    
    f_email = wait_for_element(driver, By.ID, "user_email", timeout=5)
    f_pass = wait_for_element(driver, By.ID, "user_password", timeout=5)

    if not f_email or not f_pass:
        raise Exception("デモ用ログインフォームが見つかりません")

    f_email.send_keys(email)
    f_pass.send_keys(password)
    
    btn = wait_for_element(driver, By.NAME, "commit")
    js_click(driver, btn)
    time.sleep(1) # ログイン完了待ち

    if "ログイン" in driver.title:
        raise Exception("デモ用ログインに失敗しました")
    return True

# --- プロフィール更新（安全化） ---
def update_profile_demo(driver, info):
    safe_get(driver, EDIT_URL)
    if not wait_for_element(driver, By.ID, "last_name", timeout=5): # ★ 安全化：ID名をダミー（一般的）に変更
        raise Exception("デモ用プロフィール編集ページエラー")

    def fill(fid, val):
        el = wait_for_element(driver, By.ID, fid)
        if el:
            el.clear()
            el.send_keys(val)

    # ★ 安全化：ID名をダミー（一般的）に変更
    fill("phone_1", info["phone1"])
    fill("phone_2", info["phone2"])
    fill("phone_3", info["phone3"])
    fill("postal_code", info["postal"])
    fill("last_name", info["last"])
    fill("first_name", info["first"])
    fill("last_name_kana", info["last_kana"])
    fill("first_name_kana", info["first_kana"])

    # ★ 安全化：ダミーの住所自動入力（のシミュレーション）
    try:
        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.ID, "address").get_attribute("value").strip() != ""
        )
    except TimeoutException:
        log("   > 住所の自動入力（シミュレーション）完了")
        # (デモサイトなので、実際には自動入力されなくても続行する)
        fill("address", "（自動入力されたダミー住所）")

    btn = wait_for_element(driver, By.XPATH, '//input[@value="登録"]')
    js_click(driver, btn)
    time.sleep(1)
    if "更新" not in driver.page_source:
        log("[警告] 更新完了メッセージが（デモサイトで）見つかりませんでした")

# --- アカウント処理（メイン関数） ---
def register_account_demo(account, list_file):
    if not isinstance(account, dict):
        raise TypeError("account は dict 形式で渡される必要があります。")

    email = account.get("メールアドレス")
    password = account.get("パスワード")
    if not email or not password:
        raise ValueError("account に必要な情報が不足しています")

    # ★ 安全化：FileLock（安全装置）でダミー住所録を読み書き
    list_lock = list_file + ".lock"
    with FileLock(INPUT_CSV + ".lock"), FileLock(list_lock):
        
        try:
            ldf = pd.read_csv(list_file, dtype={"郵便番号": str})
        except FileNotFoundError:
            log(f"❌ ERROR: ダミー住所録 {list_file} が見つかりません。")
            # ★ 安全化：ダミーの住所録を自動生成
            log(f"   > [デモ] ダミー住所録 {list_file} を自動生成します...")
            demo_address_data = [{
                "姓": "デモ", "名": "太郎", "セイ": "デモ", "メイ": "タロウ", "郵便番号": "1000001", "使用済み": ""
            }]
            ldf = pd.DataFrame(demo_address_data)
            ldf.to_csv(list_file, index=False)
        
        ldf["郵便番号"] = ldf["郵便番号"].str.replace("-", "").str.zfill(7)
        unused = ldf[ldf["使用済み"] != "使用済み"]
        if unused.empty:
            raise Exception(f"ダミー住所録 {list_file} に使用可能なデータがありません")
        
        idx = unused.index[0]
        row = unused.iloc[0]
        user_info = {
            "last": row["姓"],
            "first": row["名"],
            "last_kana": row["セイ"],
            "first_kana": row["メイ"],
            "postal": row["郵便番号"],
            "phone1": str(random.randint(7, 9)) + "0",
            "phone2": str(random.randint(1000, 9999)),
            "phone3": str(random.randint(0, 9999)).zfill(4)
        }
        # 使用済みにマーク
        ldf.at[idx, "使用済み"] = "使用済み"
        ldf.to_csv(list_file, index=False)

    driver = init_driver()
    try:
        safe_get(driver, LOGOUT_URL)
        driver.delete_all_cookies()
        
        if not login_demo(driver, email, password):
            raise Exception("デモ用ログイン失敗")
        
        update_profile_demo(driver, user_info)
        
        safe_get(driver, LOGOUT_URL)
        time.sleep(1)
        
        # ★ 安全化：FileLock（安全装置）でメインのCSVを更新
        with FileLock(INPUT_CSV + ".lock"):
            df = pd.read_csv(INPUT_CSV, dtype=str)
            
            # (堅牢性のため、カラムが存在するか確認)
            cols_to_update = [k for k in user_info.keys() if k in df.columns]
            df.loc[df["メールアドレス"] == email, cols_to_update] = [user_info[k] for k in cols_to_update]
            
            if "登録済み" in df.columns:
                df.loc[df["メールアドレス"] == email, "登録済み"] = "登録済み"
            
            df.to_csv(INPUT_CSV, index=False)
    finally:
        driver.quit()

# (このファイルは「ワーカー（作業員）」なので、
#  `if __name__ == "__main__":` ブロックは不要です)