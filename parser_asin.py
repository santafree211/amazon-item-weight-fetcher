"""
【設計メモ】
■ 責務:
  - 入力された文字列（URLまたは単体の識別子）から、有効な10桁のAmazon標準識別番号 (ASIN) を抽出・バリデーションする。
  - 正規表現を用いたURLパースに特化し、ネットワーク通信やUI表示は持たない。

■ 入力:
  - raw_text (str): ユーザー入力文字列（ASIN単体 または 商品詳細URL）

■ 出力:
  - Optional[str]: 抽出・正規化された10桁大文字のASIN（一致しない場合は None）

■ 主なパターン:
  - 10桁英数字単体 (例: B08N5WRWNW, 4873119033)
  - /dp/ASIN
  - /gp/product/ASIN
  - /exec/obidos/ASIN/ASIN
"""

import re
from typing import Optional


def extract_asin(text: str) -> Optional[str]:
    """
    URLまたは文字列からASIN（10桁の英数字）を抽出して大文字で返却する。
    無効な形式の場合は None を返す。
    """
    if not text:
        return None

    cleaned = text.strip()

    # パターン1: ASINそのもの (例: B08N5WRWNW, 4873119033)
    if re.fullmatch(r"[A-Z0-9]{10}", cleaned, re.IGNORECASE):
        return cleaned.upper()

    # パターン2: Amazonの代表的なURLパス構造 (/dp/, /gp/product/, /exec/obidos/ASIN/)
    match = re.search(r"/(?:dp|gp/product|exec/obidos/ASIN)/([A-Z0-9]{10})", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # パターン3: パス末尾またはクエリ前の10桁英数字
    match = re.search(r"/([A-Z0-9]{10})(?:[/?#]|$)", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None
