"""
【設計メモ】
■ 責務:
  - AWS Signature Version 4 (SigV4) 署名文字列・署名キーの導出計算。
  - 暗号化・ハッシュ化計算（HMAC-SHA256, SHA256）に特化し、HTTP通信やビジネスロジックは一切持たない。

■ 入力:
  - secret_key (str): AWSシークレットアクセスキー
  - date_stamp (str): YYYYMMDD 形式の日付文字列
  - region_name (str): AWSリージョン名 (例: us-west-2)
  - service_name (str): AWSサービス名 (例: ProductAdvertisingAPI)
  - string_to_sign (str): 署名対象文字列

■ 出力:
  - 署名ダイジェスト / 署名派生バイナリキー

■ 依存関係:
  - 標準ライブラリ (hashlib, hmac) のみ
"""

import hashlib
import hmac


def sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256 署名をバイナリで計算"""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def calculate_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    """
    AWS Signature Version 4 の派生キーを生成
    kSigning = HMAC(HMAC(HMAC(HMAC("AWS4" + kSecret,"date"),"region"),"service"),"aws4_request")
    """
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def calculate_sha256(content: str) -> str:
    """UTF-8文字列のSHA256ハッシュ値を小文字16進文字列で返却"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
