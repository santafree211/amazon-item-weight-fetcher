import csv
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dotenv import set_key, load_dotenv

from amazon_paapi import AmazonPAAPIClient, extract_asin

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)


class WeightFetcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Amazon 商品重量取得ツール (PA-API v5)")
        self.geometry("780x620")
        self.minsize(650, 500)

        self.setup_ui()
        self.check_api_status()

    def setup_ui(self):
        # 1. API設定フレーム
        config_frame = ttk.LabelFrame(self, text="API認証設定 (.env)", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(config_frame, text="Access Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_access = ttk.Entry(config_frame, width=28)
        self.entry_access.insert(0, os.getenv("AMAZON_ACCESS_KEY", ""))
        self.entry_access.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(config_frame, text="Secret Key:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.entry_secret = ttk.Entry(config_frame, width=28, show="*")
        self.entry_secret.insert(0, os.getenv("AMAZON_SECRET_KEY", ""))
        self.entry_secret.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(config_frame, text="Partner Tag:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entry_tag = ttk.Entry(config_frame, width=28)
        self.entry_tag.insert(0, os.getenv("AMAZON_PARTNER_TAG", ""))
        self.entry_tag.grid(row=1, column=1, padx=5, pady=2)

        btn_save = ttk.Button(config_frame, text="設定を保存", command=self.save_settings)
        btn_save.grid(row=1, column=2, padx=5, pady=2)

        self.lbl_status = ttk.Label(config_frame, text="", foreground="gray")
        self.lbl_status.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        # 2. 入力フレーム
        input_frame = ttk.LabelFrame(self, text="商品指定 (ASIN または 商品URL)", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="ASIN / URL:").pack(side=tk.LEFT)
        self.entry_asin = ttk.Entry(input_frame, width=40)
        self.entry_asin.pack(side=tk.LEFT, padx=5)
        self.entry_asin.bind("<Return>", lambda event: self.fetch_single())

        self.btn_fetch = ttk.Button(input_frame, text="重量を取得", command=self.fetch_single)
        self.btn_fetch.pack(side=tk.LEFT, padx=5)

        ttk.Separator(input_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.btn_csv_input = ttk.Button(input_frame, text="CSVから一括取得...", command=self.load_and_fetch_csv)
        self.btn_csv_input.pack(side=tk.LEFT, padx=5)

        # 3. 結果表示フレーム (Treeview)
        result_frame = ttk.LabelFrame(self, text="取得結果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("asin", "title", "item_weight", "package_weight", "url")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("asin", text="ASIN")
        self.tree.heading("title", text="商品名")
        self.tree.heading("item_weight", text="本体重量")
        self.tree.heading("package_weight", text="梱包重量")
        self.tree.heading("url", text="商品URL")

        self.tree.column("asin", width=95, anchor=tk.CENTER)
        self.tree.column("title", width=250)
        self.tree.column("item_weight", width=90, anchor=tk.CENTER)
        self.tree.column("package_weight", width=90, anchor=tk.CENTER)
        self.tree.column("url", width=180)

        scroll_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # 4. フッター (CSV保存・クリア・進捗バー)
        footer_frame = ttk.Frame(self, padding=5)
        footer_frame.pack(fill=tk.X, padx=10, pady=5)

        self.btn_export = ttk.Button(footer_frame, text="結果をCSV保存", command=self.export_csv)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(footer_frame, text="クリア", command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(footer_frame, mode="indeterminate", length=150)
        self.progress.pack(side=tk.RIGHT, padx=5)

    def check_api_status(self):
        client = AmazonPAAPIClient()
        if client.is_configured():
            self.lbl_status.config(text="● API設定済", foreground="green")
        else:
            self.lbl_status.config(text="▲ API未設定", foreground="red")

    def save_settings(self):
        ak = self.entry_access.get().strip()
        sk = self.entry_secret.get().strip()
        pt = self.entry_tag.get().strip()

        if not os.path.exists(ENV_PATH):
            open(ENV_PATH, "w", encoding="utf-8").close()

        set_key(ENV_PATH, "AMAZON_ACCESS_KEY", ak)
        set_key(ENV_PATH, "AMAZON_SECRET_KEY", sk)
        set_key(ENV_PATH, "AMAZON_PARTNER_TAG", pt)
        os.environ["AMAZON_ACCESS_KEY"] = ak
        os.environ["AMAZON_SECRET_KEY"] = sk
        os.environ["AMAZON_PARTNER_TAG"] = pt

        self.check_api_status()
        messagebox.showinfo("保存完了", "API認証情報を .env に保存しました。")

    def fetch_single(self):
        query = self.entry_asin.get().strip()
        if not query:
            messagebox.showwarning("入力エラー", "ASINまたは商品URLを入力してください。")
            return

        asin = extract_asin(query)
        if not asin:
            messagebox.showerror("形式エラー", "有効なASIN（10桁英数字）または商品URLではありません。")
            return

        self.run_fetch_task([asin])

    def load_and_fetch_csv(self):
        file_path = filedialog.askopenfilename(
            title="ASINリストCSVの選択",
            filetypes=[("CSV / Text files", "*.csv;*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        asins = []
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    asin = extract_asin(line.strip())
                    if asin:
                        asins.append(asin)
        except Exception as e:
            messagebox.showerror("読み込みエラー", f"ファイルの読み込みに失敗しました:\n{e}")
            return

        if not asins:
            messagebox.showwarning("該当なし", "ファイル内に有効なASINが見つかりませんでした。")
            return

        self.run_fetch_task(asins)

    def run_fetch_task(self, asins):
        client = AmazonPAAPIClient()
        if not client.is_configured():
            messagebox.showwarning("未設定", "上部の認証情報（Access Key, Secret Key, Partner Tag）を入力して保存してください。")
            return

        self.progress.start()
        self.btn_fetch.config(state=tk.DISABLED)
        self.btn_csv_input.config(state=tk.DISABLED)

        def worker():
            results = []
            chunk_size = 10
            for i in range(0, len(asins), chunk_size):
                chunk = asins[i : i + chunk_size]
                try:
                    res = client.get_items(chunk)
                    items = res.get("ItemsResult", {}).get("Items", [])
                    found = set()
                    for it in items:
                        p = client.parse_item_weight(it)
                        results.append(p)
                        found.add(p["asin"])
                    for a in chunk:
                        if a not in found:
                            results.append({
                                "asin": a,
                                "title": "取得不可（非対応ASINまたは削除済み）",
                                "item_weight": "取得不可",
                                "package_weight": "取得不可",
                                "url": f"https://www.amazon.co.jp/dp/{a}",
                            })
                except Exception as e:
                    for a in chunk:
                        results.append({
                            "asin": a,
                            "title": f"エラー: {e}",
                            "item_weight": "エラー",
                            "package_weight": "エラー",
                            "url": f"https://www.amazon.co.jp/dp/{a}",
                        })

            self.after(0, lambda: self.on_fetch_complete(results))

        threading.Thread(target=worker, daemon=True).start()

    def on_fetch_complete(self, results):
        self.progress.stop()
        self.btn_fetch.config(state=tk.NORMAL)
        self.btn_csv_input.config(state=tk.NORMAL)

        for r in results:
            self.tree.insert("", 0, values=(
                r["asin"],
                r["title"],
                r["item_weight"],
                r["package_weight"],
                r["url"]
            ))

    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def export_csv(self):
        children = self.tree.get_children()
        if not children:
            messagebox.showinfo("通知", "出力するデータがありません。")
            return

        file_path = filedialog.asksaveasfilename(
            title="CSV出力先の指定",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ASIN", "商品名", "本体重量", "梱包重量", "URL"])
            for item in children:
                writer.writerow(self.tree.item(item, "values"))

        messagebox.showinfo("完了", f"CSVを保存しました:\n{file_path}")


if __name__ == "__main__":
    app = WeightFetcherApp()
    app.mainloop()
