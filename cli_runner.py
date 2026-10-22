"""
【設計メモ】
■ 責務:
  - コマンドライン引数の解析、CLI出力（テキストまたはJSONフォーマット）、Gemini連携インターフェースの提供。
  - 業務ロジックは service_weight_fetcher、設定は config_settings に委譲する。

■ 主な引数:
  - --asin (-a): 単一のASINまたは商品URL
  - --input (-i): ASINリストファイルのパス
  - --output (-o): 結果CSVの保存先パス
  - --format (-f): 出力形式 (text または json)
"""

import argparse
import json
import os
import sys

from config_settings import load_config
from parser_asin import extract_asin
from service_weight_fetcher import fetch_weights_service
from storage_csv import read_asins_from_file, export_weights_to_csv


def main():
    parser = argparse.ArgumentParser(
        description="Amazon PA-API v5 を使って商品重量・寸法を取得するCLIツール (Gemini連携対応)"
    )
    parser.add_argument("--asin", "-a", help="取得対象のASIN または Amazon商品URL")
    parser.add_argument("--input", "-i", help="ASINリストが記述されたCSV/テキストファイルのパス")
    parser.add_argument("--output", "-o", help="結果を書き出すCSVファイルのパス")
    parser.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="出力フォーマット (text または json)"
    )

    args = parser.parse_args()

    # 対象ASINの収集
    target_asins = []
    if args.asin:
        extracted = extract_asin(args.asin)
        if not extracted:
            print(f"エラー: 有効なASINまたは商品URLではありません: {args.asin}", file=sys.stderr)
            sys.exit(1)
        target_asins.append(extracted)

    elif args.input:
        if not os.path.exists(args.input):
            print(f"エラー: 入力ファイルが見つかりません: {args.input}", file=sys.stderr)
            sys.exit(1)
        target_asins = read_asins_from_file(args.input)

    else:
        parser.print_help()
        sys.exit(0)

    if not target_asins:
        print("エラー: 対象のASINが見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

    # 設定検証
    config = load_config()
    if not config.is_valid():
        msg = (
            "【未設定】Amazon PA-API 認証情報が設定されていません。\n"
            ".env ファイルを作成し、AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG を入力してください。"
        )
        if args.format == "json":
            print(json.dumps({"status": "error", "message": msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    # サービス呼び出し
    results = fetch_weights_service(target_asins)

    # 結果出力
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print("----------------------------------------")
            print(f"ASIN: {r['asin']}")
            print(f"商品名: {r['title']}")
            print(f"本体重量: {r['item_weight']}")
            print(f"梱包重量: {r['package_weight']}")
            print(f"URL: {r['url']}")
        print("----------------------------------------")

    # CSV出力指定がある場合
    if args.output:
        export_weights_to_csv(args.output, results)
        print(f"結果をCSVファイルに保存しました: {args.output}")


if __name__ == "__main__":
    main()
