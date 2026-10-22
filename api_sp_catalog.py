"""
【設計メモ】
■ 責務:
  - Amazon SP-API Catalog Items API (v2022-04-01) のエンドポイントへ HTTP GET リクエストを発行し、商品カタログ情報を取得する。
  - LWAアクセストークン（auth_sp_token）を付与し、API通信とレスポンス返却に特化する。

■ エンドポイント:
  - GET /catalog/2022-04-01/items/{asin}
  - パラメータ: marketplaceIds=A1VC38T7YXB528, includedData=dimensions,attributes,summaries
"""

from typing import Any, Dict, Optional
import requests
from auth_sp_token import SPAPIAuthClient
from config_settings import AppConfig, load_config


class SPAPICatalogClient:
    """SP-API Catalog Items 通信クライアント"""

    def __init__(self, config: Optional[AppConfig] = None, auth_client: Optional[SPAPIAuthClient] = None):
        self.config = config or load_config()
        self.auth_client = auth_client or SPAPIAuthClient()

    def get_item(self, asin: str) -> Dict[str, Any]:
        """
        単一のASINのカタログ情報を取得
        """
        access_token = self.auth_client.get_access_token()
        url = f"{self.config.sp_api_endpoint}/catalog/2022-04-01/items/{asin}"

        headers = {
            "x-amz-access-token": access_token,
            "Accept": "application/json",
        }
        params = {
            "marketplaceIds": self.config.marketplace_id,
            "includedData": "dimensions,attributes,summaries",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        # レートリミット (429) や エラーのハンドリング
        if response.status_code == 429:
            raise RuntimeError(f"429 TooManyRequests: SP-APIレート超過 (ASIN: {asin})")
        if response.status_code == 404:
            return {"asin": asin, "error": "NotFound"}
        if response.status_code != 200:
            raise RuntimeError(f"SP-API エラー: HTTP {response.status_code} - {response.text}")

        return response.json()
