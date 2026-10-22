"""
【設計メモ】
■ 責務:
  - アプリケーション全体で使用する環境変数・クレデンシャル（.env）の読込・保存・検証。
  - OS環境変数との同期を行い、設定管理に特化する。

■ 主な設定項目:
  - AMAZON_ACCESS_KEY: AWSアクセスキー
  - AMAZON_SECRET_KEY: AWSシークレットキー
  - AMAZON_PARTNER_TAG: アソシエイトタグ
  - AMAZON_MARKETPLACE: 接続先マーケットプレイス（デフォルト: webservices.amazon.co.jp）
  - AMAZON_REGION: AWSリージョン（デフォルト: us-west-2）

■ 出力:
  - 設定値の取得 (dataclass / 辞書)
  - .env への保存反映
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv, set_key

# 実行パスに隣接する .env を対象とする
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE_PATH)


@dataclass
class AppConfig:
    access_key: str
    secret_key: str
    partner_tag: str
    marketplace: str = "webservices.amazon.co.jp"
    region: str = "us-west-2"

    def is_valid(self) -> bool:
        """有効なキーが登録されているか判定"""
        return bool(
            self.access_key
            and self.secret_key
            and self.partner_tag
            and "your_" not in self.access_key
        )


def load_config() -> AppConfig:
    """現在の環境変数から AppConfig を読み出す"""
    load_dotenv(ENV_FILE_PATH, override=True)
    host = os.getenv("AMAZON_MARKETPLACE", "webservices.amazon.co.jp")
    if "webservices." not in host:
        host = f"webservices.{host.replace('www.', '')}"

    return AppConfig(
        access_key=os.getenv("AMAZON_ACCESS_KEY", "").strip(),
        secret_key=os.getenv("AMAZON_SECRET_KEY", "").strip(),
        partner_tag=os.getenv("AMAZON_PARTNER_TAG", "").strip(),
        marketplace=host,
        region=os.getenv("AMAZON_REGION", "us-west-2").strip(),
    )


def save_config(access_key: str, secret_key: str, partner_tag: str) -> None:
    """.env ファイルへキーを保存し、現行環境変数も更新する"""
    if not os.path.exists(ENV_FILE_PATH):
        open(ENV_FILE_PATH, "w", encoding="utf-8").close()

    set_key(ENV_FILE_PATH, "AMAZON_ACCESS_KEY", access_key)
    set_key(ENV_FILE_PATH, "AMAZON_SECRET_KEY", secret_key)
    set_key(ENV_FILE_PATH, "AMAZON_PARTNER_TAG", partner_tag)

    os.environ["AMAZON_ACCESS_KEY"] = access_key
    os.environ["AMAZON_SECRET_KEY"] = secret_key
    os.environ["AMAZON_PARTNER_TAG"] = partner_tag
