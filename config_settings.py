"""
【設計メモ】
■ 責務:
  - アプリケーション全体で使用する環境変数・クレデンシャル（.env）の読込・保存・検証。
  - PA-API v5 および SP-API の両方の認証設定に対応する。

■ 主な設定項目:
  - SP_API_CLIENT_ID / SP_API_CLIENT_SECRET / SP_API_REFRESH_TOKEN (SP-API用)
  - SP_API_ENDPOINT / SP_API_REGION
  - AMAZON_ACCESS_KEY / AMAZON_SECRET_KEY / AMAZON_PARTNER_TAG (PA-API用)

■ 出力:
  - AppConfig (設定オブジェクト)
  - .env への保存機能
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv, set_key

ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE_PATH)


@dataclass
class AppConfig:
    # SP-API 用クレデンシャル
    sp_api_client_id: str = ""
    sp_api_client_secret: str = ""
    sp_api_refresh_token: str = ""
    sp_api_endpoint: str = "https://sellingpartnerapi-fe.amazon.com"
    sp_api_region: str = "us-east-1"
    marketplace_id: str = "A1VC38T7YXB528"  # 日本マーケットプレイス

    # PA-API 用クレデンシャル
    access_key: str = ""
    secret_key: str = ""
    partner_tag: str = ""
    marketplace: str = "webservices.amazon.co.jp"
    region: str = "us-west-2"

    def has_sp_api(self) -> bool:
        """SP-API の利用が可能か判定"""
        return bool(self.sp_api_client_id and self.sp_api_client_secret and self.sp_api_refresh_token)

    def has_pa_api(self) -> bool:
        """PA-API の利用が可能か判定"""
        return bool(self.access_key and self.secret_key and self.partner_tag and "your_" not in self.access_key)


def load_config() -> AppConfig:
    """現在の環境変数から AppConfig を読み出す"""
    load_dotenv(ENV_FILE_PATH, override=True)
    return AppConfig(
        sp_api_client_id=os.getenv("SP_API_CLIENT_ID", "").strip(),
        sp_api_client_secret=os.getenv("SP_API_CLIENT_SECRET", "").strip(),
        sp_api_refresh_token=os.getenv("SP_API_REFRESH_TOKEN", "").strip(),
        sp_api_endpoint=os.getenv("SP_API_ENDPOINT", "https://sellingpartnerapi-fe.amazon.com").strip(),
        sp_api_region=os.getenv("SP_API_REGION", "us-east-1").strip(),
        marketplace_id=os.getenv("MARKETPLACE_ID", "A1VC38T7YXB528").strip(),
        access_key=os.getenv("AMAZON_ACCESS_KEY", "").strip(),
        secret_key=os.getenv("AMAZON_SECRET_KEY", "").strip(),
        partner_tag=os.getenv("AMAZON_PARTNER_TAG", "").strip(),
        marketplace=os.getenv("AMAZON_MARKETPLACE", "webservices.amazon.co.jp").strip(),
        region=os.getenv("AMAZON_REGION", "us-west-2").strip(),
    )


def save_config(sp_client_id: str = "", sp_client_secret: str = "", sp_refresh_token: str = "") -> None:
    """.env ファイルへキーを保存し、現行環境変数も更新する"""
    if not os.path.exists(ENV_FILE_PATH):
        open(ENV_FILE_PATH, "w", encoding="utf-8").close()

    if sp_client_id:
        set_key(ENV_FILE_PATH, "SP_API_CLIENT_ID", sp_client_id)
        os.environ["SP_API_CLIENT_ID"] = sp_client_id
    if sp_client_secret:
        set_key(ENV_FILE_PATH, "SP_API_CLIENT_SECRET", sp_client_secret)
        os.environ["SP_API_CLIENT_SECRET"] = sp_client_secret
    if sp_refresh_token:
        set_key(ENV_FILE_PATH, "SP_API_REFRESH_TOKEN", sp_refresh_token)
        os.environ["SP_API_REFRESH_TOKEN"] = sp_refresh_token
