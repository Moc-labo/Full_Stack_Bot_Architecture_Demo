# =============================================================================
# ポートフォリオ：【技術デモ】並列処理システム（Python 司令塔）
# =============================================================================
#
# 目的：
# このスクリプトは、「multiprocessing（並列処理）」を使い、
# 複数の「ワーカー（demo_register_worker.py）」プロセスを同時に起動し、
# CSV（指示書）に基づいた作業を「並列」で実行させる「司令塔」のデモです。
#
# =============================================================================

import csv
import multiprocessing
import time
import json
from filelock import FileLock
import os
import sys
from datetime import datetime

# demo_register_worker.py をインポート（同じフォルダにあると仮定）
try:
    from demo_register_worker import register_account_demo
except ImportError:
    print("❌ ERROR: demo_register_worker.py が同じフォルダに見つかりません。")
    sys.exit(1)

# ★ 安全化：ダミーのファイル名に変更
INPUT_CSV = "demo_accounts_input.csv" # (例: Node.jsが作ったアカウントリスト)
LOCK_FILE = "demo_accounts_input.csv.lock"
MAX_PROCESSES = 5 # 並列実行するプロセス数

def log(message):
    """ログ出力用の関数"""
    ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    msg = f"{ts} {message}"
    print(msg)
    with open("demo_register_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def clean_email(email):
    """メールアドレスの簡易クレンジング"""
    return email.strip().replace("　", "").replace("\n", "").replace("\r", "").lower()

def load_accounts():
    """
    指示書CSVを「安全に（FileLock）」読み込む関数
    """
    log(f"📄 {INPUT_CSV} を読み込み中...")
    try:
        with FileLock(LOCK_FILE):
            with open(INPUT_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                accounts = []
                for row in reader:
                    email = clean_email(row.get("メールアドレス", ""))
                    status = (row.get("登録済み") or "").strip()
                    if status not in ("登録済み", "登録失敗"):
                        row["メールアドレス"] = email
                        accounts.append(row)
                log(f"👉 読み込み完了、未登録アカウント数: {len(accounts)} 件")
                return accounts
    except FileNotFoundError:
        log(f"❌ ERROR: 入力ファイル {INPUT_CSV} が見つかりません。")
        return []
    except Exception as e:
        log(f"❌ ERROR: {INPUT_CSV} 読み込み中にエラー: {e}")
        return []

def worker_task(account_json_str, list_index):
    """
    各並列プロセス（作業員）が実行するタスク
    """
    import json # 子プロセスで必要になる可能性があるため再import
    account = json.loads(account_json_str)
    email = account.get("メールアドレス", "")
    
    # ★ 安全化：ダミーの住所録ファイル名を指定
    list_file = f"demo_address_list_{list_index}.csv"

    try:
        log(f"🚀 [PID: {os.getpid()}] ワーカー起動: {email} (リスト: {list_file})")
        # ★ 安全化：demo_register_worker.py の関数を呼び出す
        register_account_demo(account, list_file)
        log(f"✅ 登録成功: {email} 🍒🍥")
    except Exception as e:
        log(f"❌ {email} の登録中に失敗 [PID: {os.getpid()}]\n理由: {e}")

def main():
    log("🚀 [技術デモ] Python並列登録バッチ開始")
    
    while True:
        accounts = load_accounts()
        if not accounts:
            log("🎉 すべてのアカウントの登録が完了しました！")
            break

        log(f"🌀 残り {len(accounts)} 件、同時に最大 {MAX_PROCESSES} 件処理します。")

        procs = []
        # CPUコアを使い切る「マルチプロセス」で並列実行
        for idx, account in enumerate(accounts[:MAX_PROCESSES]):
            account_json_str = json.dumps(account, ensure_ascii=False)
            p = multiprocessing.Process(
                target=worker_task,
                args=(account_json_str, idx % MAX_PROCESSES) # (リストファイルを均等に割り当てる)
            )
            p.start()
            procs.append(p)

        # 全員の作業が完了するのを待つ
        for p in procs:
            p.join()

        log(f"--- 1バッチ（{len(procs)}件）完了。2秒待機 ---")
        time.sleep(2)

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn") # OS互換性のための「安全設計」
    main()