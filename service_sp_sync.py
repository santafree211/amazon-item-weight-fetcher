"""
【設計メモ】
■ 責務:
  - サーバー1のDBマスターから未処理ASINを取得し、Amazon SP-API (または PA-API) を使って重量を取得し、DBマスターへ順次UPSERT反映する巡回同期サービス。
  - レート制御（SP-APIは基本 2〜5 req/s）、429バックオフ自動再試行、中断・再開、進捗通知に特化する。

■ 入力:
  - remote_client: RemoteServer1Client
  - delay_sec: リクエスト待機時間（デフォルト 0.5秒）
  - limit: 今回巡回する上限件数
  - progress_callback: 進捗通知コールバック
"""

import time
from typing import Any, Callable, Dict, List, Optional

from api_sp_catalog import SPAPICatalogClient
from parser_sp_weight import parse_sp_catalog_weight
from remote_server1_client import RemoteServer1Client


def run_sp_batch_sync(
    remote_client: Optional[RemoteServer1Client] = None,
    catalog_client: Optional[SPAPICatalogClient] = None,
    delay_sec: float = 0.5,
    limit: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    SP-API Catalog Items を使用してサーバー1の未取得ASINの重量を巡回・反映
    """
    if remote_client is None:
        remote_client = RemoteServer1Client()

    if catalog_client is None:
        catalog_client = SPAPICatalogClient()

    # 1. 重量テーブルの初期化
    if progress_callback:
        progress_callback(0, 0, "サーバー1の重量テーブルを確認しています...")
    remote_client.init_weight_table()

    # 2. 未処理ASINの抽出 (purchase_targets 基準)
    if progress_callback:
        progress_callback(0, 0, "未取得のASINリストを抽出中...")
    pending_asins = remote_client.fetch_pending_asins(limit=limit)
    total_asins = len(pending_asins)

    if total_asins == 0:
        return {"total": 0, "success": 0, "error": 0, "message": "全ASINの重量取得が完了しています。"}

    success_count = 0
    error_count = 0
    save_batch_size = 10
    buffered_records: List[Dict[str, Any]] = []

    for idx, asin in enumerate(pending_asins, 1):
        if progress_callback:
            progress_callback(idx, total_asins, f"取得中: {idx}/{total_asins} (ASIN: {asin})")

        # リトライ処理付きでアイテム情報取得
        max_retries = 3
        retry_delay = 2.0
        record = None

        for attempt in range(max_retries):
            try:
                res = catalog_client.get_item(asin)
                parsed = parse_sp_catalog_weight(res)
                record = parsed
                if parsed.get("package_weight_val") is not None or parsed.get("item_weight_val") is not None:
                    success_count += 1
                else:
                    error_count += 1
                break
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "TooManyRequests" in err_msg:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue

                record = {
                    "asin": asin,
                    "title": f"エラー: {e}",
                    "item_weight": "エラー",
                    "item_weight_val": None,
                    "package_weight": "エラー",
                    "package_weight_val": None,
                    "primary_weight_unit": "",
                    "url": f"https://www.amazon.co.jp/dp/{asin}",
                }
                error_count += 1
                break

        if record:
            buffered_records.append(record)

        # 10件ごとにサーバー1へ一括反映
        if len(buffered_records) >= save_batch_size or idx == total_asins:
            try:
                remote_client.upsert_weights(buffered_records)
                buffered_records.clear()
            except Exception as e:
                if progress_callback:
                    progress_callback(idx, total_asins, f"[DB書込エラー] {e}")

        # レート制限遵守待機
        time.sleep(delay_sec)

    return {
        "total": total_asins,
        "success": success_count,
        "error": error_count,
        "message": f"巡回同期完了: 合計 {total_asins} 件中、重量取得 {success_count} 件、未登録/エラー {error_count} 件",
    }
