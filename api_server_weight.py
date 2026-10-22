"""
【設計メモ】
■ 責務:
  - サーバー1上で動作する、Googleスプレッドシート(GAS)向けの超高速・軽量な重量取得APIサーバー。
  - DBマスターの item_weights テーブルからASINの重量（グラム換算）を検索し、JSON形式で返却する。
  - CORS (Access-Control-Allow-Origin: *) に対応し、ブラウザやGASからの直接リクエストを受け付ける。

■ エンドポイント:
  - GET /weight?asin=B08N5WRWNW
  - 返却形式:
    {
      "status": "ok",
      "asin": "B08N5WRWNW",
      "weight_g": 380.0,
      "title": "商品名",
      "unit": "grams"
    }
"""

import json
import sqlite3
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

DB_PATH = "/home/ubuntu/db-master/data/db_master.sqlite3"


class WeightHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/weight", "/api/weight"):
            qs = urllib.parse.parse_qs(parsed.query)
            asin = qs.get("asin", [None])[0]
            if not asin:
                self._respond(400, {"status": "error", "message": "Missing asin parameter"})
                return

            asin = asin.strip().upper()
            try:
                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5.0)
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT w.item_weight_val, w.package_weight_val, w.unit, a.title
                    FROM item_weights w
                    LEFT JOIN asins a ON w.asin = a.asin
                    WHERE w.asin = ?
                    LIMIT 1;
                """,
                    (asin,),
                )
                row = cur.fetchone()
                conn.close()

                if row:
                    item_w, pkg_w, u, t = row
                    unit = u or "grams"
                    title = t or ""

                    # 代表重量(g)を正確に計算
                    # item_weight_val がすでにある場合は優先
                    weight_val = None
                    if item_w is not None and item_w > 0:
                        # item_w は基本的に grams (例: 380.0)
                        weight_val = round(float(item_w), 1)
                    elif pkg_w is not None and pkg_w > 0:
                        # pkg_w の単位を考慮
                        if "kilo" in str(unit).lower():
                            weight_val = round(float(pkg_w) * 1000, 1)
                        elif "pound" in str(unit).lower() or "lb" in str(unit).lower():
                            weight_val = round(float(pkg_w) * 453.592, 1)
                        else:
                            weight_val = round(float(pkg_w), 1)

                    self._respond(
                        200,
                        {
                            "status": "ok",
                            "asin": asin,
                            "weight_g": weight_val,
                            "item_weight_val": item_w,
                            "package_weight_val": pkg_w,
                            "unit": unit,
                            "title": title,
                        },
                    )
                else:
                    self._respond(
                        404,
                        {
                            "status": "not_found",
                            "asin": asin,
                            "message": "Weight not registered yet",
                        },
                    )
            except Exception as e:
                self._respond(500, {"status": "error", "message": str(e)})

        elif parsed.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"status": "error", "message": "Not found"})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8088), WeightHandler)
    print("Weight API server listening on port 8088...")
    server.serve_forever()
