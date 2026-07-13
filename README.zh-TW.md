[English](README.md) | 繁體中文

# KTTV 天氣資料工具

這是一個以 Python 標準函式庫製作的輕量工具，用於取得 KTTV 天氣資料。本儲存庫刻意不包含任何專案專用的地點、憑證、部署設定或營運資料。

## 功能

- 取得即時觀測、預報與地點資訊。
- 支援批次抓取、JSON 輸出，以及排程情境的重複資料略過機制。
- 站點資訊只讀取本機設定檔；憑證只讀取本機環境變數。
- 無須安裝第三方 Python 套件。

## 環境需求

- Python 3.9 以上版本。
- 僅在使用部署輔助工具時需要 `rsync` 與 SSH。

## 本機設定

先建立私有站點設定檔，再把範例中的匿名名稱與座標改成自己的本機資料：

```bash
mkdir -p private
cp sites.example.json private/sites.json
```

在執行環境中設定服務憑證：

```bash
export KTTV_API_KEY='your-local-value'
export KTTV_SECRET_KEY='your-local-value'
```

`private/`、環境檔、狀態檔、日誌與本機操作筆記皆已由 Git 忽略，請勿提交其中內容。

## 快速開始

先執行離線簽章檢查：

```bash
python3 kttv_client.py selftest
```

依本機設定抓取全部站點：

```bash
python3 fetch_weather.py
```

抓取單一自訂站點、取得 JSON，或略過未更新的排程資料：

```bash
python3 fetch_weather.py --site site-a
python3 fetch_weather.py --json
python3 fetch_weather.py --json --dedup
```

如需使用其他私有設定檔路徑：

```bash
python3 fetch_weather.py --sites-file private/another-sites.json
```

批次工具支援 `--site NAME|all`、`--json`、`--dedup` 與 `--state FILE`；預設狀態檔為程式旁 `private/` 目錄中的 `kttv_state.json`。自訂狀態檔請放在 `private/` 或儲存庫外。

若只要單次查詢，可在本機提供值後直接使用 client：

```bash
python3 kttv_client.py realtime <緯度> <經度>
python3 kttv_client.py forecast <緯度> <經度>
python3 kttv_client.py dayforecast <緯度> <經度>
python3 kttv_client.py location <緯度> <經度>
python3 kttv_client.py search <關鍵字>
```

## 網路限制

實際連線受上游網路存取控制影響。依目前開發測試，需透過越南出口 IP 操作；請在目標環境自行驗證連線。

## 部署

以下指令只會預覽，不會複製檔案：

```bash
./deploy.sh user@host:/target/path
```

加上 `--go` 才會實際複製：

```bash
./deploy.sh user@host:/target/path --go
```

部署輔助工具會刻意排除本機站點設定、環境檔、狀態、日誌與私有操作筆記；請在受信任的目標環境另行提供這些資料。

## 專案結構

| 檔案 | 用途 |
| --- | --- |
| `kttv_client.py` | 讀取本機憑證的 KTTV client 與離線簽章檢查。 |
| `fetch_weather.py` | 讀取本機站點設定的批次抓取工具。 |
| `sites.example.json` | 匿名本機設定範本。 |
| `deploy.sh` | 可選用的 rsync 部署輔助工具。 |
| `tests/` | 以標準函式庫撰寫的回歸測試。 |
