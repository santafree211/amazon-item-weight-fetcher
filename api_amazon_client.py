"""
【設計メモ】
■ 責務:
  - Amazon Product Advertising API (PA-API v5) のエンドポイントへ HTTP POST リクエストを発行する通信クライアント。
  - 認証署名の付与（auth_aws_signer の呼び出し）とレスポンスの取得に特化する。

■ 仕様:
  - オペレーション: GetItems
  - 1リクエスト上限: 10 ASIN
  - リソース指定: ItemInfo.Title, ItemInfo.ProductInfo, Offers.Listings.Price, Images.Primary.Medium

■ 依存モジュール:
  - auth_aws_signer (AWS SigV4署名)
  - config_settings (設定読込)
"""

import datetime
import hmac
import json
from typing import Any, Dict, List, Optional
import requests

from auth_aws_signer import calculate_signature_key, calculate_sha256, sign
from config_settings import AppConfig, load_config


class AmazonPAAPIClient:
    """PA-API v5 通信専用クライアント"""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.service = "ProductAdvertisingAPI"

    def get_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        GetItems API を呼び出す
        :param item_ids: 最大10個までのASINリスト
        :return: Amazon PA-APIのJSONレスポンス辞書
        """
        if not self.config.is_valid():
            raise ValueError(
                "Amazon PA-API の認証情報 (Access Key / Secret Key / Partner Tag) が未設定です。\n"
                ".env ファイルに設定してください。"
            )

        if len(item_ids) > 10:
            raise ValueError("PA-API の GetItems は一度に最大10件まで指定可能です。")

        endpoint = f"https://{self.config.marketplace}/paapi5/getitems"
        path = "/paapi5/getitems"

        payload = {
            "ItemIds": item_ids,
            "Resources": [
                "ItemInfo.Title",
                "ItemInfo.ProductInfo",
                "ItemInfo.Classifications",
                "Images.Primary.Medium",
                "Offers.Listings.Price",
            ],
            "PartnerTag": self.config.partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp",
        }
        payload_str = json.dumps(payload)

        # 署名用タイムスタンプ生成
        t = datetime.datetime.now(datetime.timezone.utc)
        amz_date = t.strftime("%Y%m%d%T%H%M%SZ").replace(":", "")
        date_stamp = t.strftime("%Y%m%d")

        canonical_uri = path
        canonical_querystring = ""
        payload_hash = calculate_sha256(payload_str)

        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.config.marketplace}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

        canonical_request = (
            f"POST\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.config.region}/{self.service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{calculate_sha256(canonical_request)}"
        )

        signing_key = calculate_signature_key(
            self.config.secret_key, date_stamp, self.config.region, self.service
        )
        signature = sign(signing_key, string_to_sign).hex()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.config.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "amz-1.0",
            "X-Amz-Date": amz_date,
            "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems",
            "Authorization": authorization_header,
        }

        response = requests.post(endpoint, headers=headers, data=payload_str, timeout=10)
        return response.json()
