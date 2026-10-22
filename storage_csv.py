"""
【設計メモ】
■ 責務:
  - 取得結果リストの CSV 入出力、および ASIN リストファイルの読み込み処理。
  - ファイル I/O フォーマット変換に特化する。

■ 入力/出力:
  - CSV ファイル ⇄ ASINリスト / 重量データ辞書リスト
"""

import csv
from typing import Any, Dict, List
from parser_asin import extract_asin


def read_asins_from_file(file_path: str) -> List[str]:
    """ファイル（CSVまたはテキスト）を行ごとに読み込み、有効なASINリストを抽出"""
    asins: List[str] = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            asin = extract_asin(line.strip())
            if asin:
                asins.append(asin)
    return asins


def export_weights_to_csv(file_path: str, records: List[Dict[str, Any]]) -> None:
    """重量取得結果の辞書リストを CSV 形式で保存"""
    fieldnames = ["asin", "title", "item_weight", "package_weight", "url"]
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
