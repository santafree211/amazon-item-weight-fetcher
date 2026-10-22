"""
【設計メモ】
■ 責務:
  - SP-API (または PA-API) を使ってサーバー1のDBマスターと重量データを同期するコマンドライン実行インターフェース。
  - テスト実行 (--limit) や実行間隔調整 (--delay) を受け付ける。

■ 引数:
  - --limit (-l): 巡回するASIN上限件数（未指定時は全件）
  - --delay (-d): API待機間隔（デフォルト: 0.5秒）
"""

import argparse
import sys
from service_sp_sync import run_sp_batch_sync


def main():
    parser = argparse.ArgumentParser(
        description="Amazon SP-API (Catalog Items) を使ってサーバー1のDBマスターに重量データを巡回同期するツール"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=None, help="巡回するASINの上限件数 (テスト時は 5〜20 推奨)"
    )
    parser.add_argument(
        "--delay", "-d", type=float, default=0.5, help="APIリクエスト待機秒数 (デフォルト: 0.5秒)"
    )

    args = parser.parse_args()

    print("==================================================")
    print(" サーバー1 DBマスター 重量巡回同期バッチ (SP-API)")
    print("==================================================")
    print(f"対象件数制限: {args.limit if args.limit else '全件 (未取得すべて)'}")
    print(f"リクエスト間隔: {args.delay} 秒")
    print("--------------------------------------------------")

    def on_progress(current, total, msg):
        if total > 0:
            pct = (current / total) * 100
            print(f"[{current}/{total} ({pct:.1f}%)] {msg}")
        else:
            print(f"[準備中] {msg}")

    try:
        res = run_sp_batch_sync(
            delay_sec=args.delay,
            limit=args.limit,
            progress_callback=on_progress,
        )
        print("--------------------------------------------------")
        print(res["message"])
        print("==================================================")
    except Exception as e:
        print(f"\n[致命的エラー] バッチ処理が中断されました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
