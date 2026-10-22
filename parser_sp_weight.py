"""
【設計メモ】
■ 責務:
  - SP-API Catalog Items (v2022-04-01) の JSON レスポンスから、本体重量・梱包重量・寸法・商品名を正規化して抽出する。
  - dimensions フィールドおよび attributes フィールドの両方から安全に重量を取得する。

■ 入力:
  - item (dict): SP-API Catalog Items のレスポンス辞書

■ 出力:
  - dict:
    - asin: 商品コード
    - title: 商品名
    - item_weight: 本体重量 (例: "350 g")
    - item_weight_val: 本体重量数値 (例: 350.0)
    - package_weight: 梱包重量 (例: "480.82 g")
    - package_weight_val: 梱包重量数値 (例: 480.82)
    - primary_weight_unit: 単位 (g, kg, pounds 等)
    - url: Amazon商品ページURL
"""

from typing import Any, Dict, Optional


def parse_sp_catalog_weight(item: Dict[str, Any]) -> Dict[str, Any]:
    """SP-API Catalog Items レスポンスから重量情報をパース"""
    asin = item.get("asin", "")

    if "error" in item:
        return {
            "asin": asin,
            "title": "取得不可（NotFound）",
            "item_weight": "取得不可",
            "item_weight_val": None,
            "package_weight": "取得不可",
            "package_weight_val": None,
            "primary_weight_unit": "",
            "url": f"https://www.amazon.co.jp/dp/{asin}",
        }

    # タイトルの取得
    title = "（商品名不明）"
    summaries = item.get("summaries", [])
    if summaries and isinstance(summaries, list):
        title = summaries[0].get("itemName", title)

    # 1. attributes からの重量取得 (最優先: グラム表記が正確)
    attrs = item.get("attributes", {})
    item_pkg_weight_list = attrs.get("item_package_weight", [])
    item_weight_list = attrs.get("item_weight", [])

    pkg_w_val: Optional[float] = None
    pkg_w_unit: str = ""
    if item_pkg_weight_list and isinstance(item_pkg_weight_list, list):
        first = item_pkg_weight_list[0]
        pkg_w_val = first.get("value")
        pkg_w_unit = first.get("unit", "")

    item_w_val: Optional[float] = None
    item_w_unit: str = ""
    if item_weight_list and isinstance(item_weight_list, list):
        first = item_weight_list[0]
        item_w_val = first.get("value")
        item_w_unit = first.get("unit", "")

    # 2. dimensions 配列からのフォールバック取得
    if pkg_w_val is None:
        dimensions_list = item.get("dimensions", [])
        if dimensions_list and isinstance(dimensions_list, list):
            dim_entry = dimensions_list[0]
            pkg_info = dim_entry.get("package", {})
            w_info = pkg_info.get("weight", {})
            if w_info:
                val = w_info.get("value")
                unit = w_info.get("unit", "")
                if unit == "pounds" and val is not None:
                    # pounds -> grams 変換 (1 lb = 453.59237 g)
                    pkg_w_val = round(val * 453.59237, 2)
                    pkg_w_unit = "grams"
                else:
                    pkg_w_val = val
                    pkg_w_unit = unit

    primary_unit = pkg_w_unit or item_w_unit or "grams"

    return {
        "asin": asin,
        "title": title,
        "item_weight": f"{item_w_val} {item_w_unit}".strip() if item_w_val is not None else "未登録",
        "item_weight_val": item_w_val,
        "package_weight": f"{pkg_w_val} {pkg_w_unit}".strip() if pkg_w_val is not None else "未登録",
        "package_weight_val": pkg_w_val,
        "primary_weight_unit": primary_unit,
        "url": f"https://www.amazon.co.jp/dp/{asin}",
    }
