"""
【設計メモ】
■ 責務:
  - Amazon LWA (Login with Amazon) OAuth2 トークンエンドポイントへ問い合わせ、一時アクセストークンを取得・キャッシュする。
  - トークンの有効期限（3600秒）を管理し、期限内の再利用と期限切れ前の自動リフレッシュを行う。
  - SP-API 通信本体やビジネスロジックは一切持たない。

■ 入力:
  - client_id (str): LWA Client ID
  - client_secret (str): LWA Client Secret
  - refresh_token (str): LWA Refresh Token

■ 出力:
  - access_token (str): 有効な Bearer トークン文字列
"""

import time
from typing import Optional
import requests
from config_settings import load_config


class SPAPIAuthClient:
    """LWA トークン取得・自動キャッシュマネージャー"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        cfg = load_config()
        self.client_id = client_id or cfg.sp_api_client_id
        self.client_secret = client_secret or cfg.sp_api_client_secret
        self.refresh_token = refresh_token or cfg.sp_api_refresh_token

        self._cached_token: Optional[str] = None
        self._expires_at: float = 0.0

    def is_configured(self) -> bool:
        """必要なクレデンシャルが設定されているか確認"""
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def get_access_token(self) -> str:
        """
        有効期限内のトークンがあればそれを返却し、
        切れているか未取得なら api.amazon.com/auth/o2/token にて再取得する。
        """
        # 有効期限の60秒前まではキャッシュを利用
        if self._cached_token and time.time() < (self._expires_at - 60):
            return self._cached_token

        if not self.is_configured():
            raise ValueError(
                "SP-APIの認証情報 (SP_API_CLIENT_ID / SP_API_CLIENT_SECRET / SP_API_REFRESH_TOKEN) が未設定です。\n"
                ".env ファイルを確認してください。"
            )

        url = "https://api.amazon.com/auth/o2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"LWA トークン取得失敗: HTTP {response.status_code} - {response.text}")

        data = response.json()
        self._cached_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        self._expires_at = time.time() + expires_in

        return self._cached_token
