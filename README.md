# amazon-item-weight-fetcher
Amazon PA-API v5 (Product Advertising API) を使用して、ASIN または商品URLから商品重量・寸法・商品情報をオンデマンドで取得するローカルツールです。

CLI（コマンドライン）および GUI（デスクトップアプリ）の両方に対応しており、Gemini 等の AI エージェントからの自動呼び出しにも対応します。

---

## 主な機能

- **オンデマンド重量取得**: ASIN または Amazon 商品URL を指定して重量（PackageWeight / ItemWeight）を取得
- **二重インターフェース**:
  - **CLI / スクリプト**: Gemini や自動化スクリプトから呼び出しやすいコマンドライン操作、JSON/CSV 出力
  - **GUI アプリ**: Windows 環境で手軽に操作できる Tkinter 製デスクトップ画面
- **CSV 一括処理**: 複数 ASIN の一括重量取得
- **AWS Signature v4 準拠**: 公式の PA-API v5 署名プロトコルによる安全なリクエスト

---

## 動作環境・前提条件

- **OS**: Windows 10 / 11
- **Python**: 3.10 以上 (Python 3.13 動作確認済み)
- **Amazon アソシエイト・PA-API 認証情報**:
  - `Access Key ID`
  - `Secret Access Key`
  - `Partner Tag` (アソシエイトタグ、例: `xxxx-22`)
  - ※ PA-API は AWS 認証（Signature Version 4）を使用します。

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
   `.env.example` をコピーして `.env` を作成し、Amazon の認証情報を記入します。
   ```bash
   cp .env.example .env
   ```
   `.env` 内の設定例:
   ```env
   AMAZON_ACCESS_KEY=your_access_key_here
   AMAZON_SECRET_KEY=your_secret_key_here
   AMAZON_PARTNER_TAG=your_partner_tag-22
   AMAZON_MARKETPLACE=www.amazon.co.jp
   ```

---

## 使い方

### 1. CLI（Gemini / コマンドラインからの実行）

単一 ASIN の重量取得:
```bash
python get_weight.py --asin B08N5WRWNW
```

JSON 形式で出力（AI や他プログラムとの連携用）:
```bash
python get_weight.py --asin B08N5WRWNW --format json
```

CSV からの一括取得:
```bash
python get_weight.py --input asins.csv --output results.csv
```

### 2. GUI（デスクトップ画面）

GUI を起動します:
```bash
python app_gui.py
```
または `run_gui.bat` をダブルクリックして起動できます。

---

## ディレクトリ構成

```text
├── README.md            # 本ドキュメント
├── .gitignore           # Git 除外設定 (.env やキャッシュ等)
├── .env.example         # 環境変数テンプレート
├── requirements.txt     # 必要パッケージ一覧
├── amazon_paapi.py      # PA-API v5 署名 & 通信コアモジュール
├── get_weight.py        # CLI 実行スクリプト (Gemini 連携対応)
└── app_gui.py           # Tkinter デスクトップ GUI アプリ
```

---

## ライセンス

MIT License
