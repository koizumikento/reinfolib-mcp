# reinfolib-mcp

国土交通省の[不動産情報ライブラリAPI](https://www.reinfolib.mlit.go.jp/help/apiManual/)を、MCPサーバー・CLI・Pythonクライアントから利用するための非公式OSSです。2026年8月20日時点の公開35 APIに対応しています。

## 必要なもの

- Python 3.10〜3.13
- [uv](https://docs.astral.sh/uv/)
- 不動産情報ライブラリで発行されたAPIキー

APIキーは環境変数へ設定します。

```sh
export REINFOLIB_API_KEY="your_api_key"
```

PowerShellでは次のように設定します。

```powershell
$env:REINFOLIB_API_KEY = "your_api_key"
```

## MCPクライアントへ設定

PyPIには未公開です。GitHubから起動してください。

```json
{
  "mcpServers": {
    "reinfolib": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/reinfolib-mcp.git@main",
        "reinfolib-mcp"
      ],
      "env": {
        "REINFOLIB_API_KEY": "your_api_key"
      }
    }
  }
}
```

## 主なMCPツール

| ツール | 用途 |
|---|---|
| `reinfolib_get_api_data` | API IDと公式queryパラメータを指定して公開35 APIを呼び出す |
| `reinfolib_search_real_estate` | 年、四半期、地域から取引価格・成約価格を検索する |
| `reinfolib_get_municipalities` | 都道府県内の市区町村一覧を取得する |
| `reinfolib_get_land_price` | 地価公示・地価調査ポイントを取得する |
| `reinfolib_get_appraisal_info` | 鑑定評価書情報を取得する |
| `reinfolib_get_real_estate_points` | 不動産価格ポイントを取得する |
| `reinfolib_get_urban_planning` | 都市計画区域・用途地域を取得する |
| `reinfolib_get_school_districts` | 小学校区・中学校区を取得する |
| `reinfolib_get_childcare_welfare` | 保育園・幼稚園・福祉施設を取得する |
| `reinfolib_search_facilities` | 学校・医療機関を取得する |
| `reinfolib_get_disaster_risk` | 災害危険区域・液状化傾向を取得する |
| `reinfolib_get_geospatial_data` | 緯度経度から複数の地理データをまとめて取得する |
| `reinfolib_server_status` | APIキー設定と対応API一覧を確認する |

`reinfolib_get_api_data`の`parameters`には[公式API操作説明](https://www.reinfolib.mlit.go.jp/help/apiManual/)と同じパラメータ名を渡します。

```json
{
  "api_id": "XKT026",
  "parameters": {
    "response_format": "geojson",
    "z": 14,
    "x": 14624,
    "y": 6016
  }
}
```

## CLI

```sh
# 取引価格を検索
uvx --from git+https://github.com/koizumikento/reinfolib-mcp.git@main \
  reinfolib-mcp search --year 2015 --quarter 2 --city 13102

# 市区町村一覧
uvx --from git+https://github.com/koizumikento/reinfolib-mcp.git@main \
  reinfolib-mcp municipalities --area 13

# 緯度経度周辺の地価・都市計画情報
uvx --from git+https://github.com/koizumikento/reinfolib-mcp.git@main \
  reinfolib-mcp location --latitude 35.6851 --longitude 139.7514 --year 2025
```

## Python

```python
import asyncio

from reinfolib_mcp import ReinfiolibClient


async def main() -> None:
    async with ReinfiolibClient() as client:
        result = await client.search_real_estate_transactions(
            year=2015,
            quarter=2,
            city="13102",
            price_classification="01",
        )
        print(result)


asyncio.run(main())
```

任意の公開APIは`request_api()`で呼び出せます。未知のAPI ID、廃止済みID、不足・余分なパラメータは送信前に拒否します。

## 対応API

| ID | 内容 |
|---|---|
| XIT001 | 不動産価格（取引価格・成約価格）情報 |
| XIT002 | 都道府県内市区町村一覧 |
| XCT001 | 鑑定評価書情報 |
| XPT001 | 不動産価格情報ポイント |
| XPT002 | 地価公示・地価調査ポイント |
| XKT001〜XKT003 | 都市計画区域、用途地域、立地適正化計画 |
| XKT004〜XKT007 | 小学校区、中学校区、学校、保育園・幼稚園等 |
| XKT010〜XKT011 | 医療機関、福祉施設 |
| XKT013〜XKT025 | 人口、都市計画、施設、地形、防災情報 |
| XKT026〜XKT029 | 洪水、高潮、津波、土砂災害警戒区域 |
| XKT030〜XKT031 | 都市計画道路、人口集中地区 |
| XGT001 | 指定緊急避難場所 |
| XST001 | 災害履歴 |

正確なパラメータ、収録範囲、更新時期は[公式の公開API一覧](https://www.reinfolib.mlit.go.jp/help/apiManual/)を確認してください。

## 開発

```sh
uv sync
uv run pytest -q
uv run ruff check src tests
```

## ライセンスとデータ利用条件

ソフトウェアは[MIT License](LICENSE)で提供します。取得データには、不動産情報ライブラリの[API利用規約](https://www.reinfolib.mlit.go.jp/help/termsOfUse/)が適用されます。

公開サービスで利用する場合は、同規約に従い次のクレジットを表示してください。

> このサービスは、国土交通省の不動産情報ライブラリのAPI機能を使用していますが、提供情報の最新性、正確性、完全性等が保証されたものではありません

このリポジトリおよび作者は国土交通省とは関係ありません。
