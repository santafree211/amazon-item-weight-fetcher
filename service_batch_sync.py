"""
【設計メモ】
■ 責務:
  - サーバー1のDBマスターから未取得ASINを抽出し、Amazon PA-API v5 による巡回取得を行い、DBへ随時UPDATE反映するバッチ同期処理の統括。
  - レート制御（1秒1リクエスト）、リトライ（429バックオフ）、中断・再開、進捗通知に特化する。

■ 入力:
  - batch_size: 1リクエストのASIN数（PA-API上限10件）
  - delay_sec: リクエスト間インターバル（標準1.1秒）
  - total_limit: 巡回上限件数（未指定時は全未取得件数）
  - progress_callback: 進捗通知用コールバック関数 (current, total, msg)

■ 出力:
  - 処理結果サマリー (成功件数, エラー件数, スキップ件数)
"""

import time
from typing import Any, Callable, Dict, List, Optional

from api_amazon_client import AmazonPAAPIClient
from config_settings import load_config
from parser_weight import parse_item_weight_info
from remote_server1_client import RemoteServer1Client


def run_batch_weight_sync(
    remote_client: Optional[RemoteServer1Client] = None,
    api_client: Optional[AmazonPAAPIClient] = None,
    delay_sec: float = 1.1,
    limit: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    サーバー1のDBマスターから未処理ASINを取得し、
    PA-API v5 で重量を取得してDBへ順次UPSERT反映する巡回パイプライン
    """
    if remote_client is None:
        remote_client = RemoteServer1Client()

    if api_client is None:
        cfg = load_config()
        if not cfg.is_valid():
            raise ValueError("Amazon PA-API の認証情報が未設定です。.env を設定してください。")
        api_client = AmazonPAAPIClient(cfg)

    # 1. 重量テーブルの初期化（存在しない場合のみ作成）
    if progress_callback:
        progress_callback(0, 0, "サーバー1の重量テーブルを確認しています...")
    remote_client.init_weight_table()

    # 2. 未処理ASINの抽出
    if progress_callback:
        progress_callback(0, 0, "未取得のASINリストを抽出中...")
    pending_asins = remote_client.fetch_pending_asins(limit=limit)
    total_asins = len(pending_asins)

    if total_asins == 0:
        return {"total": 0, "success": 0, "error": 0, "message": "全ASINの重量取得が完了しています。"}

    chunk_size = 10
    success_count = 0
    error_count = 0

    # 3. 10件単位で巡回
    for i in range(0, total_asins, chunk_size):
        chunk = pending_asins[i : i + chunk_size]
        current_progress = min(i + len(chunk), total_asins)

        if progress_callback:
            progress_callback(
                current_progress,
                total_asins,
                f"取得中: {current_progress}/{total_asins} (ASIN: {chunk[0]}...)",
            )

        # PA-API リクエスト（429エラー時は指数バックオフで再試行）
        max_retries = 3
        retry_delay = 3.0
        records: List[Dict[str, Any]] = []

        for attempt in range(max_retries):
            try:
                res = api_client.get_items(chunk)
                items = res.get("ItemsResult", {}).get("Items", [])
                found_asins = set()

                for item in items:
                    parsed = parse_item_weight_info(item)
                    records.append(parsed)
                    found_asins.add(parsed["asin"])
                    success_count += 1

                for a in chunk:
                    if a not in found_asins:
                        records.append({
                            "asin": a,
                            "title": "取得不可（非対応ASINまたは削除済み）",
                            "item_weight": "取得不可",
                            "package_weight": "取得不可",
                            "item_weight_val": None,
                            "package_weight_val": None,
                            "primary_weight_unit": "",
                            "url": f"https://www.amazon.co.jp/dp/{a}",
                        })
                        error_count += 1
                break  # 成功したらリトライループを抜ける

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "TooManyRequests" in err_msg:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue

                # リトライ失敗または他エラーの場合
                for a in chunk:
                    records.append({
                        "asin": a,
                        "title": f"エラー: {e}",
                        "item_weight": "エラー",
                        "package_weight": "エラー",
                        "item_weight_val": None,
                        "package_weight_val": None,
                        "primary_weight_unit": "",
                        "url": f"https://www.amazon.co.jp/dp/{a}",
                    })
                    error_count += 1
                break

        # 4. サーバー1へ一括UPSERT反映
        try:
            remote_client.upsert_weights(records)
        except Exception as e:
            if progress_callback:
                progress_callback(current_progress, total_asins, f"[DB書込エラー] {e}")

        # レートリミット遵守待機
        time.sleep(delay_sec)

    return {
        "total": total_asins,
        "success": success_count,
        "error": error_count,
        "message": f"巡回同期完了: 合計 {total_asins} 件中、成功 {success_count} 件、エラー {error_count} 件",
    }
