"""
【設計メモ】
■ 責務:
  - 任意の件数のASINリストを受け取り、10件ごとのバッチ分割・API実行・パース・エラーハンドリングを行うサービス層。
  - UI層（CLIやGUI）と通信クライアントの仲介に専念する。

■ 入力:
  - asins (List[str]): 処理対象のASINリスト
  - client (AmazonPAAPIClient): API通信クライアント（未指定時は自動生成）

■ 出力:
  - List[Dict[str, Any]]: 各ASINごとの結果リスト（商品名、重量、URL等）
"""

import sys
from typing import Any, Dict, List, Optional

from api_amazon_client import AmazonPAAPIClient
from parser_weight import parse_item_weight_info


def fetch_weights_service(asins: List[str], client: Optional[AmazonPAAPIClient] = None) -> List[Dict[str, Any]]:
    """ASINリストを受け取り、バッチ処理で商品重量データを取得して返却"""
    if client is None:
        client = AmazonPAAPIClient()

    results: List[Dict[str, Any]] = []
    chunk_size = 10

    for i in range(0, len(asins), chunk_size):
        chunk = asins[i : i + chunk_size]
        try:
            res = client.get_items(chunk)

            # APIエラーがあれば標準エラー出力へ
            if "Errors" in res:
                for err in res["Errors"]:
                    print(f"[警告] APIエラー: {err.get('Message')} ({err.get('Code')})", file=sys.stderr)

            items_result = res.get("ItemsResult", {})
            items = items_result.get("Items", [])
            found_asins = set()

            for item in items:
                parsed = parse_item_weight_info(item)
                results.append(parsed)
                found_asins.add(parsed["asin"])

            # レスポンスに含まれなかった（見つからなかった）ASINの補完
            for asin in chunk:
                if asin not in found_asins:
                    results.append({
                        "asin": asin,
                        "title": "取得不可（非対応ASINまたは削除済み）",
                        "item_weight": "取得不可",
                        "package_weight": "取得不可",
                        "primary_weight_val": None,
                        "primary_weight_unit": "",
                        "url": f"https://www.amazon.co.jp/dp/{asin}",
                    })

        except Exception as e:
            for asin in chunk:
                results.append({
                    "asin": asin,
                    "title": f"エラー: {e}",
                    "item_weight": "エラー",
                    "package_weight": "エラー",
                    "primary_weight_val": None,
                    "primary_weight_unit": "",
                    "url": f"https://www.amazon.co.jp/dp/{asin}",
                })

    return results
