/**
 * Googleスプレッドシート 納品重量自動計算 & 76,500g 打ち止め制御スクリプト
 * 
 * 【機能】
 * 1. ASINが入力された行を自動検知し、サーバー1のDBマスターから重量(g)を即座に取得して転記
 * 2. シート上部の合計重量をリアルタイム更新
 * 3. 合計重量が 76,500g (76.5kg) に到達・超過した場合に警告音・アラート・赤色強調を表示
 */

// サーバー1の重量取得APIエンドポイント
const SERVER_API_URL = "http://160.248.0.217:8088/weight";
const MAX_WEIGHT_LIMIT_G = 76500; // 76.5 kg

/**
 * シート編集時の自動トリガー (onEdit)
 */
function onEdit(e) {
  if (!e || !e.range) return;
  const sheet = e.range.getSheet();
  const row = e.range.getRow();
  const col = e.range.getColumn();

  // ヘッダー行(1〜3行目など)は対象外
  if (row < 4) return;

  // ASINが入力される列（例: 2列目 = B列）
  // ※スキャンされたバーコードからASINが自動変換されて入る列番号を指定（B列なら 2）
  const ASIN_COL = 2;       // B列
  const WEIGHT_COL = 4;     // D列（重量 g を書き込む列）

  if (col === ASIN_COL) {
    const asin = String(e.value || "").trim().toUpperCase();
    if (!asin || asin.length < 10) return;

    // サーバー1のDBマスターへ問い合わせ
    const weightData = fetchWeightFromDB(asin);
    if (weightData && weightData.weight_g !== null) {
      sheet.getRange(row, WEIGHT_COL).setValue(weightData.weight_g);
    } else {
      sheet.getRange(row, WEIGHT_COL).setValue("未登録");
    }

    // 合計重量チェック
    checkTotalWeightLimit(sheet);
  }
}

/**
 * サーバー1からASINの重量(g)を取得
 */
function fetchWeightFromDB(asin) {
  try {
    const url = `${SERVER_API_URL}?asin=${encodeURIComponent(asin)}`;
    const response = UrlFetchApp.fetch(url, {
      method: "get",
      muteHttpExceptions: true
    });

    if (response.getResponseCode() === 200) {
      return JSON.parse(response.getContentText());
    }
  } catch (err) {
    Logger.log("Weight fetch error: " + err);
  }
  return null;
}

/**
 * 合計重量と76,500g制限のチェック＆表示更新
 */
function checkTotalWeightLimit(sheet) {
  const WEIGHT_COL = 4; // D列
  const lastRow = sheet.getLastRow();
  if (lastRow < 4) return;

  // D4から最終行までの重量を合算
  const weights = sheet.getRange(4, WEIGHT_COL, lastRow - 3, 1).getValues();
  let totalWeight = 0;
  for (let i = 0; i < weights.length; i++) {
    const val = Number(weights[i][0]);
    if (!isNaN(val) && val > 0) {
      totalWeight += val;
    }
  }

  // シートの B1 セルに「現在の合計重量」、C1 セルに「ステータス」を表示
  const totalCell = sheet.getRange("B1");
  const statusCell = sheet.getRange("C1");

  totalCell.setValue(`${totalWeight.toLocaleString()} g / 76,500 g`);

  if (totalWeight >= MAX_WEIGHT_LIMIT_G) {
    // 76,500g 到達・超過
    statusCell.setValue("🔴【打ち止め】76,500g 到達！この箱は満杯です");
    statusCell.setBackground("#ffcccc").setFontColor("#cc0000").setFontWeight("bold");
    totalCell.setBackground("#ffcccc").setFontColor("#cc0000").setFontWeight("bold");

    // ポップアップ警告
    SpreadsheetApp.getUi().alert(
      "【重量上限アラート】\n" +
      `現在の合計重量が ${totalWeight.toLocaleString()} g に達しました。\n` +
      "この箱の納品はここで打ち止めにしてください。"
    );
  } else {
    // 余裕あり
    const remaining = MAX_WEIGHT_LIMIT_G - totalWeight;
    statusCell.setValue(`🟢【積込OK】あと ${remaining.toLocaleString()} g 投入可能`);
    statusCell.setBackground("#e6ffed").setFontColor("#008800").setFontWeight("normal");
    totalCell.setBackground("#ffffff").setFontColor("#000000").setFontWeight("bold");
  }
}
