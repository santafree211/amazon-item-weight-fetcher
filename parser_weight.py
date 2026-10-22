"""
【設計メモ】
■ 責務:
  - Amazon PA-API v5 の JSON レスポンスから、重量情報（ItemDimensions / PackageDimensions）および関連情報を抽出し、統一モデルに変換する。
  - APIレスポンス構造の差異を吸収し、データ抽出・正規化に特化する。

■ 入力:
  - item (dict): PA-API v5 GetItems の Items 配列内の各要素

■ 出力:
  - dict:
    - asin: 商品コード
    - title: 商品名
    - item_weight: 本体重量（単位付き文字列）
    - package_weight: 梱包重量（単位付き文字列）
    - primary_weight_val: 数値重量（ソートや集計用）
    - primary_weight_unit: 重量単位（g, kg, pounds等）
    - url: Amazon商品ページURL
"""

from typing import Any, Dict


def parse_item_weight_info(item: Dict[str, Any]) -> Dict[str, Any]:
    """PA-API の 1 アイテム辞書から商品重量情報を正規化して抽出"""
    asin = item.get("ASIN", "")
    item_info = item.get("ItemInfo", {})
    title = item_info.get("Title", {}).get("DisplayValue", "（商品名不明）")
    product_info = item_info.get("ProductInfo", {})

    # 1. ItemDimensions (本体寸法・重量)
    item_dims = product_info.get("ItemDimensions", {})
    item_weight = item_dims.get("Weight", {})
    item_weight_val = item_weight.get("DisplayValue", None)
    item_weight_unit = item_weight.get("Unit", "")

    # 2. PackageDimensions (梱包寸法・重量)
    pkg_dims = product_info.get("PackageDimensions", {})
    pkg_weight = pkg_dims.get("Weight", {})
    pkg_weight_val = pkg_weight.get("DisplayValue", None)
    pkg_weight_unit = pkg_weight.get("Unit", "")

    # 代表値（本体が優先、無ければ梱包を採用）
    primary_weight = item_weight_val or pkg_weight_val
    primary_unit = item_weight_unit or pkg_weight_unit

    return {
        "asin": asin,
        "title": title,
        "item_weight": f"{item_weight_val} {item_weight_unit}".strip() if item_weight_val else "未登録",
        "package_weight": f"{pkg_weight_val} {pkg_weight_unit}".strip() if pkg_weight_val else "未登録",
        "primary_weight_val": primary_weight,
        "primary_weight_unit": primary_unit,
        "url": item.get("DetailPageURL", f"https://www.amazon.co.jp/dp/{asin}"),
    }
