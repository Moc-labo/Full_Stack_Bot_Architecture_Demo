# =============================================================================
# ポートフォリオ：【技術デモ】並列処理用・指示書分割ツール
# =============================================================================
#
# 目的：
# このスクリプトは、`demo_main_register.py`（司令塔）が並列処理を行う前に、
# 作業員に配る「指示書（CSV）」を、指定した数（PARTS）に
# 自動で「分割」するための支援ツールです。
#
# =============================================================================

import csv
import math
import os

# ★ 安全化：ダミーのファイル名に変更
INPUT_FILE = "demo_address_list_original.csv"
OUTPUT_PREFIX = "demo_address_list_"
PARTS = 5  # 分割数

def split_list_csv():
    try:
        with open(INPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [row for row in reader if len(row) > 0]
    except FileNotFoundError:
        print(f"❌ ERROR: 分割元の指示書（{INPUT_FILE}）が見つかりません。")
        print("   > [デモ] ダミーの指示書を自動生成します...")
        # ★ 安全化：ファイルが無い場合にダミーを自動生成
        header = ["姓", "名", "セイ", "メイ", "郵便番号", "使用済み"]
        rows = [
            ["デモ", f"太郎{i}", "デモ", f"タロウ{i}", f"100000{i % 7}", ""]
            for i in range(1, 26) # 25人分のダミーデータ
        ]
        with open(INPUT_FILE, 'w', newline='', encoding='utf-8') as outf:
            writer = csv.writer(outf)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"   > ✅ {INPUT_FILE} を自動生成しました。")

    # 「使用済み」列のインデックスを探す
    try:
        used_idx = header.index("使用済み")
    except ValueError:
        used_idx = None

    # 「使用済み」と記入された行は除外
    if used_idx is not None:
        rows = [row for row in rows if row[used_idx].strip() != "使用済み"]

    total = len(rows)
    if total == 0:
        print("✅ 分割対象の行がありません（全て使用済みか、空です）。")
        return

    base_size = total // PARTS
    remainder = total % PARTS

    start = 0
    print(f"🚀 合計 {total} 件のデータを {PARTS} 個のファイルに分割します...")
    for i in range(PARTS):
        size = base_size + (1 if i < remainder else 0)
        chunk = rows[start:start+size]
        start += size

        out_file = f"{OUTPUT_PREFIX}{i}.csv"
        with open(out_file, 'w', newline='', encoding='utf-8') as outf:
            writer = csv.writer(outf)
            writer.writerow(header)
            writer.writerows(chunk)
        print(f"   > {out_file} に {len(chunk)} 行を書き出しました")

if __name__ == "__main__":
    split_list_csv()