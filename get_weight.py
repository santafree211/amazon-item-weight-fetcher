import argparse
import csv
import json
import os
import sys
from typing import List
from amazon_paapi import AmazonPAAPIClient, extract_asin


def get_weights_for_asins(asins: List[str], client: AmazonPAAPIClient) -> List[dict]:
    """ASINリストを受け取り、重量情報のリストを返却（PA-APIは最大10個ずつ）"""
    results = []
    chunk_size = 10
    
    for i in range(0, len(asins), chunk_size):
        chunk = asins[i : i + chunk_size]
        try:
            res = client.get_items(chunk)
            # エラーチェック
            if "Errors" in res:
                for err in res["Errors"]:
                    print(f"[警告] APIエラー: {err.get('Message')} ({err.get('Code')})", file=sys.stderr)

            items_result = res.get("ItemsResult", {})
            items = items_result.get("Items", [])
            found_asins = set()

            for item in items:
                parsed = client.parse_item_weight(item)
                results.append(parsed)
                found_asins.add(parsed["asin"])

            # 取得できなかったASIN
            for asin in chunk:
                if asin not in found_asins:
                    results.append({
                        "asin": asin,
                        "title": "取得不可（非対応ASINまたは削除済み）",
                        "item_weight": "取得不可",
                        "package_weight": "取得不可",
                        "primary_weight_val": None,
                        "primary_weight_unit": "",
                        "url": f"https://www.amazon.co.jp/dp/{asin}",
                    })

        except Exception as e:
            for asin in chunk:
                results.append({
                    "asin": asin,
                    "title": f"エラー: {e}",
                    "item_weight": "エラー",
                    "package_weight": "エラー",
                    "primary_weight_val": None,
                    "primary_weight_unit": "",
                    "url": f"https://www.amazon.co.jp/dp/{asin}",
                })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Amazon PA-API v5 を使って商品重量・寸法を取得するCLIツール (Gemini連携対応)"
    )
    parser.add_argument("--asin", "-a", help="取得したいASIN または Amazonの商品URL")
    parser.add_argument("--input", "-i", help="ASINリストが記述されたCSVまたはテキストファイルのパス")
    parser.add_argument("--output", "-o", help="結果を出力するCSVファイルのパス")
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

        with open(args.input, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                extracted = extract_asin(line)
                if extracted:
                    target_asins.append(extracted)

    else:
        parser.print_help()
        sys.exit(0)

    if not target_asins:
        print("エラー: 対象のASINが見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

    client = AmazonPAAPIClient()

    # 認証情報の確認
    if not client.is_configured():
        msg = (
            "【未設定】Amazon PA-API 認証情報が設定されていません。\n"
            ".env ファイルを作成し、AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG を入力してください。"
        )
        if args.format == "json":
            print(json.dumps({"status": "error", "message": msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    # 重量取得
    results = get_weights_for_asins(target_asins, client)

    # 出力処理
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"----------------------------------------")
            print(f"ASIN: {r['asin']}")
            print(f"商品名: {r['title']}")
            print(f"本体重量: {r['item_weight']}")
            print(f"梱包重量: {r['package_weight']}")
            print(f"URL: {r['url']}")
        print(f"----------------------------------------")

    # CSV書き出し
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["asin", "title", "item_weight", "package_weight", "url"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(results)
        print(f"結果をCSVファイルに保存しました: {args.output}")


if __name__ == "__main__":
    main()
