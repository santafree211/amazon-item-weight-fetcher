"""
【設計メモ】
■ 責務:
  - サーバー1 (WEBARENA Indigo) への SSH 接続、コマンド実行、および SQLite DB に対するリモートクエリ/更新の実行。
  - SSH通信とリモートSQL実行に特化し、ビジネスロジックは持たない。

■ 入力:
  - host, user, key_path, db_path
  - sql (str): 実行したいSQL文
  - params (tuple/list): パラメータ（必要な場合）

■ 出力:
  - execute_query: 取得行リスト (List[Dict[str, Any]])
  - execute_update: 変更件数または成功ステータス
"""

import json
import os
import subprocess
from typing import Any, Dict, List, Optional


class RemoteServer1Client:
    """サーバー1へのSSHリモートDB接続クライアント"""

    def __init__(
        self,
        host: str = "160.248.0.217",
        user: str = "ubuntu",
        key_path: str = r"C:\Users\user\.ssh\indigo.pem",
        db_path: str = "/home/ubuntu/db-master/data/db_master.sqlite3",
    ):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.db_path = db_path

    def run_ssh_command(self, bash_cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """SSH経由で任意のBashコマンドを実行（Windows cp932 エンコード問題を回避するため utf-8 / errors=replace 指定）"""
        cmd = [
            "ssh",
            "-i", self.key_path,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"{self.user}@{self.host}",
            bash_cmd,
        ]
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        stdout_str = p.stdout.decode("utf-8", errors="replace")
        stderr_str = p.stderr.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=p.returncode,
            stdout=stdout_str,
            stderr=stderr_str,
        )

    def init_weight_table(self) -> None:
        """サーバー1上のDBマスターに重量管理用テーブル (item_weights) を作成"""
        sql = """
        CREATE TABLE IF NOT EXISTS item_weights (
            asin TEXT PRIMARY KEY,
            item_weight TEXT,
            item_weight_val REAL,
            package_weight TEXT,
            package_weight_val REAL,
            unit TEXT,
            fetched_at TEXT DEFAULT (datetime('now', 'localtime')),
            status TEXT DEFAULT 'ok',
            FOREIGN KEY (asin) REFERENCES asins(asin) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_item_weights_fetched ON item_weights(fetched_at);
        """
        bash_cmd = f"sqlite3 -cmd '.timeout 10000' {self.db_path} \"{sql}\""
        res = self.run_ssh_command(bash_cmd)
        if res.returncode != 0:
            raise RuntimeError(f"テーブル作成失敗: {res.stderr}")

    def fetch_pending_asins(self, limit: Optional[int] = None) -> List[str]:
        """
        重量が未取得のASINリストをサーバー1から抽出して返却。
        item_weights に未登録の asins を取得。
        """
        # asins テーブル全体(66万件)ではなく、巡回対象である purchase_targets (約6万件) を対象とする
        # 読み取りロック競合を避けるため read-only URI を使用
        limit_clause = f"LIMIT {limit}" if limit else ""
        sql = f"""
        SELECT p.asin
        FROM purchase_targets p
        LEFT JOIN item_weights w ON p.asin = w.asin
        WHERE w.asin IS NULL
        {limit_clause};
        """
        bash_cmd = f"sqlite3 -cmd '.timeout 10000' file:{self.db_path}?mode=ro \"{sql}\""
        res = self.run_ssh_command(bash_cmd, timeout=60)
        if res.returncode != 0:
            raise RuntimeError(f"ASIN取得失敗: {res.stderr}")

        asins = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return asins

    def upsert_weights(self, records: List[Dict[str, Any]]) -> None:
        """
        取得できた重量データをサーバー1の item_weights に一括UPSERT反映
        """
        if not records:
            return

        sql_statements = []
        for r in records:
            asin = r["asin"].replace("'", "''")
            iw = (r.get("item_weight") or "").replace("'", "''")
            pw = (r.get("package_weight") or "").replace("'", "''")
            iw_val = r.get("item_weight_val")
            pw_val = r.get("package_weight_val")
            unit = (r.get("primary_weight_unit") or "").replace("'", "''")
            status = "error" if r.get("item_weight") in ("エラー", "取得不可") else "ok"

            iw_val_str = str(iw_val) if iw_val is not None else "NULL"
            pw_val_str = str(pw_val) if pw_val is not None else "NULL"

            stmt = f"""
            INSERT INTO item_weights (asin, item_weight, item_weight_val, package_weight, package_weight_val, unit, status, fetched_at)
            VALUES ('{asin}', '{iw}', {iw_val_str}, '{pw}', {pw_val_str}, '{unit}', '{status}', datetime('now', 'localtime'))
            ON CONFLICT(asin) DO UPDATE SET
                item_weight = excluded.item_weight,
                item_weight_val = excluded.item_weight_val,
                package_weight = excluded.package_weight,
                package_weight_val = excluded.package_weight_val,
                unit = excluded.unit,
                status = excluded.status,
                fetched_at = excluded.fetched_at;
            """
            sql_statements.append(stmt.strip())

        full_sql = "BEGIN TRANSACTION;\n" + "\n".join(sql_statements) + "\nCOMMIT;"
        bash_cmd = f"sqlite3 -cmd '.timeout 10000' {self.db_path} \"{full_sql}\""
        res = self.run_ssh_command(bash_cmd, timeout=60)
        if res.returncode != 0:
            raise RuntimeError(f"UPSERT失敗: {res.stderr}")
