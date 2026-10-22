import datetime
import hashlib
import hmac
import json
import os
import re
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()


def sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256 署名を計算"""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    """AWS Signature Version 4 派生キーの生成"""
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def extract_asin(text: str) -> Optional[str]:
    """URLまたは文字列からASIN（10桁の英数字）を抽出"""
    text = text.strip()
    # ASINそのもの (例: B08N5WRWNW, 4873119033)
    if re.fullmatch(r"[A-Z0-9]{10}", text, re.IGNORECASE):
        return text.upper()
    
    # URLからの抽出
    match = re.search(r"/(?:dp|gp/product|exec/obidos/ASIN)/([A-Z0-9]{10})", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    match = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


class AmazonPAAPIClient:
    """
    Amazon Product Advertising API (PA-API v5) クライアント
    AWS Signature Version 4 プロトコルに準拠して GetItems を呼び出します。
    """

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        partner_tag: Optional[str] = None,
        host: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.access_key = access_key or os.getenv("AMAZON_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("AMAZON_SECRET_KEY", "")
        self.partner_tag = partner_tag or os.getenv("AMAZON_PARTNER_TAG", "")
        self.host = host or os.getenv("AMAZON_MARKETPLACE", "webservices.amazon.co.jp")
        self.region = region or os.getenv("AMAZON_REGION", "us-west-2")
        self.service = "ProductAdvertisingAPI"

        # ホスト名補正 (もし www.amazon.co.jp が指定されていた場合)
        if "webservices." not in self.host:
            self.host = f"webservices.{self.host.replace('www.', '')}"

    def is_configured(self) -> bool:
        """必要な認証情報が設定されているか確認"""
        return bool(
            self.access_key
            and self.secret_key
            and self.partner_tag
            and "your_" not in self.access_key
        )

    def get_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        PA-API v5 の GetItems オペレーションを実行
        item_ids: 最大10個までのASINリスト
        """
        if not self.is_configured():
            raise ValueError(
                "Amazon PA-API の認証情報 (Access Key / Secret Key / Partner Tag) が未設定です。\n"
                ".env ファイルに正しいキーを設定してください。"
            )

        endpoint = f"https://{self.host}/paapi5/getitems"
        path = "/paapi5/getitems"

        payload = {
            "ItemIds": item_ids[:10],
            "Resources": [
                "ItemInfo.Title",
                "ItemInfo.ProductInfo",
                "ItemInfo.Classifications",
                "Images.Primary.Medium",
                "Offers.Listings.Price",
            ],
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp",
        }
        payload_str = json.dumps(payload)

        # 署名生成準備
        t = datetime.datetime.now(datetime.timezone.utc)
        amz_date = t.strftime("%Y%m%d%T%H%M%SZ").replace(":", "")
        date_stamp = t.strftime("%Y%m%d")

        canonical_uri = path
        canonical_querystring = ""
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.host}\n"
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
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
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

    def parse_item_weight(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        PA-APIのレスポンスItemから重量や寸法をわかりやすい辞書に変換
        """
        asin = item.get("ASIN", "")
        item_info = item.get("ItemInfo", {})
        title = item_info.get("Title", {}).get("DisplayValue", "不明")
        product_info = item_info.get("ProductInfo", {})

        # ItemDimensions (商品本体)
        item_dims = product_info.get("ItemDimensions", {})
        item_weight = item_dims.get("Weight", {})
        item_weight_val = item_weight.get("DisplayValue", None)
        item_weight_unit = item_weight.get("Unit", "")

        # PackageDimensions (パッケージ/梱包込み)
        pkg_dims = product_info.get("PackageDimensions", {})
        pkg_weight = pkg_dims.get("Weight", {})
        pkg_weight_val = pkg_weight.get("DisplayValue", None)
        pkg_weight_unit = pkg_weight.get("Unit", "")

        # どちらか取得できた重量を採用
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
