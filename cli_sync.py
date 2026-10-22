"""
【設計メモ】
■ 責務:
  - サーバー1のDBマスターと同期する巡回バッチコマンドライン実行インターフェース。
  - Gemini や タスクスケジューラからの呼び出しに対応する。

■ 引数:
  - --limit (-l): 今回実行する上限件数（例: --limit 50 でテスト実行、指定なしで全件巡回）
  - --delay (-d): リクエスト間隔秒数（デフォルト: 1.1秒）
"""

import argparse
import sys
from service_batch_sync import run_batch_weight_sync


def main():
    parser = argparse.ArgumentParser(
        description="サーバー1のDBマスターと連携して6万件ASINの重量を自動巡回取得・更新するバッチツール"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=None, help="巡回するASINの上限件数 (テスト時は 10〜50 推奨、全件は未指定)"
    )
    parser.add_argument(
        "--delay", "-d", type=float, default=1.1, help="APIリクエスト待機秒数 (デフォルト: 1.1秒)"
    )

    args = parser.parse_args()

    print("==================================================")
    print(" サーバー1 DBマスター 重量巡回同期バッチ")
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
        res = run_batch_weight_sync(
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
