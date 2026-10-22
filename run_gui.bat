@echo off
chcp 65001 > nul
echo Amazon商品重量取得ツールを起動しています...
python app_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo エラーが発生しました。キーを押して終了してください。
    pause
)
