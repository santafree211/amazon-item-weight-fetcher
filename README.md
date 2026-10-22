# amazon-item-weight-fetcher
Amazon PA-API v5 (Product Advertising API) を使用して、ASIN または商品URLから商品重量・寸法・商品情報をオンデマンドで取得するローカルツールです。

CLI（コマンドライン）および GUI（デスクトップアプリ）の両方に対応し、Gemini 等の AI エージェントからの自動呼び出しに対応します。

---

## 開発憲法（アーキテクチャ方針）

- **1ファイル1責務（Single Responsibility Principle）**: 責務ごとにモジュールを明確に分割
- **命名規則**: `カテゴリ名_機能名.py` 形式（例: `auth_aws_signer.py`, `service_weight_fetcher.py`）
- **自己文書化**: 全てのファイル先頭に【設計メモ】（責務、入出力、依存関係）と実コードを同梱

---

## ファイル構成と役割（1ファイル1責務）

| ファイル名 | カテゴリ | 責務・役割 |
|---|---|---|
| `auth_aws_signer.py` | auth | AWS Signature Version 4 (SigV4) 暗号署名計算・派生キー導出 |
| `config_settings.py` | config | .env / 環境変数の読み込み、永続化保存、設定バリデーション |
| `parser_asin.py` | parser | URL または テキストからの ASIN（10桁英数字）正規化抽出 |
| `parser_weight.py` | parser | PA-APIレスポンスから重量（本体/梱包）・商品名等の正規化抽出 |
| `api_amazon_client.py` | api | PA-API v5 エンドポイントへの署名付き HTTP リクエスト発行 |
| `service_weight_fetcher.py`| service | バッチ分割（最大10件/回）・エラー補正・ビジネスロジック統括 |
| `storage_csv.py` | storage | CSV / テキストファイルの読み込みおよび結果 CSV 保存 |
| `cli_runner.py` | cli | コマンドライン実行・JSON出力 (Gemini 呼び出し用) |
| `gui_app.py` | gui | Tkinter によるデスクトップ GUI 画面表示・イベント処理 |
| `run_gui.bat` | script | Windows 用 GUI ワンクリック起動バッチファイル |

---

## 使い方

### 1. CLI（Gemini / コマンドラインからの実行）

単一 ASIN の重量取得:
```bash
python cli_runner.py --asin B08N5WRWNW
```

JSON 形式で出力（AI や他プログラムとの連携用）:
```bash
python cli_runner.py --asin B08N5WRWNW --format json
```

CSV からの一括取得:
```bash
python cli_runner.py --input asins.csv --output results.csv
```

### 2. GUI（デスクトップ画面）

GUI を起動します:
```bash
python gui_app.py
```
または `run_gui.bat` をダブルクリックして起動できます。
画面上の「API認証設定」から直接アクセスキー等を保存可能です。

---

## インストール手順

1. **リポジトリのクローン**:
   ```bash
   git clone https://github.com/santafree211/amazon-item-weight-fetcher.git
   cd amazon-item-weight-fetcher
   ```

2. **依存ライブラリのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

3. **環境設定**:
   `.env.example` をコピーして `.env` を作成し、Amazon の認証情報を記入します（GUI画面からの入力保存も可能です）。
   ```bash
   cp .env.example .env
   ```

---

## ライセンス

MIT License
