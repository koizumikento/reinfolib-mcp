# 不動産情報ライブラリMCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

国土交通省の[不動産情報ライブラリAPI](https://www.reinfolib.mlit.go.jp/help/apiManual/)を使用したModel Context Protocol (MCP) サーバーとPythonライブラリです。不動産価格、地価、都市計画、施設、災害リスク情報などの地理空間データに簡単にアクセスできます。

## 特徴

- 🏠 **包括的な不動産データ**: 取引価格、地価公示・調査、鑑定評価書情報
- 🗺️ **地理空間データ**: GeoJSON・バイナリベクトルタイル（PBF）形式対応
- 🏛️ **都市計画情報**: 用途地域、都市計画区域、地区計画などの制限情報
- 🏫 **周辺施設情報**: 学校、医療機関、図書館、駅など30種類の施設データ
- ⚠️ **災害リスク情報**: 災害危険区域、液状化発生傾向、地すべり防止地区
- 🤖 **MCP対応**: Claude Desktop、Cursorなどから直接利用可能
- 🚀 **uvx実行**: インストール不要でCLIツールとして実行
- 🧪 **型安全**: Pydanticによる厳密なデータ検証
- ⚡ **非同期処理**: httpxベースの高速APIクライアント

## クイックスタート

### 1. MCPサーバーとして使用（推奨）

#### uvxで即座に起動

```bash
# APIキーを環境変数で設定
export REINFOLIB_API_KEY="your_api_key_here"

# MCPサーバーを起動
uvx reinfolib-mcp
```

#### Claude Desktopで使用

`config.json`に以下を追加:

```json
{
  "mcpServers": {
    "reinfolib": {
      "command": "uvx",
      "args": ["reinfolib-mcp"],
      "env": {
        "REINFOLIB_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

設定完了後、Claudeに以下のように話しかけられます：

- "東京都千代田区の不動産価格を調べて"
- "渋谷駅周辺の学校と医療機関の情報を取得"
- "新宿区の災害リスク情報を確認して"
- "大阪市の地価動向を分析"

### 2. CLIツールとして使用

```bash
# 不動産価格検索
uvx reinfolib-mcp search --prefecture 13 --city 13101 --limit 5

# 市区町村一覧取得
uvx reinfolib-mcp municipalities --prefecture 13

# 位置指定でのデータ取得
uvx reinfolib-mcp location --latitude 35.6851 --longitude 139.7514

# システム状態確認
uvx reinfolib-mcp status
```

### 3. Pythonライブラリとして使用

```python
import asyncio
from reinfolib_mcp import ReinfiolibClient, Language

async def main():
    async with ReinfiolibClient(api_key="your_api_key") as client:
        # 東京都の市区町村一覧
        municipalities = await client.get_municipalities("13", Language.JAPANESE)
        print(f"東京都の市区町村数: {len(municipalities)}")
        
        # 不動産取引価格検索
        transactions = await client.search_real_estate_transactions(
            prefecture="13",
            city="13101",
            from_date="20230101",
            to_date="20231231"
        )
        print(f"取引件数: {transactions.total_count}")

asyncio.run(main())
```

## インストール

### uvx実行（推奨）

```bash
# 直接実行（インストール不要）
uvx reinfolib-mcp --help
```

### GitHubからuvでインストール

```bash
uv tool install git+https://github.com/koizumikento/reinfolib-mcp
```

### pipインストール

```bash
pip install reinfolib-mcp
```

### 開発版インストール

```bash
git clone https://github.com/koizumikento/reinfolib-mcp.git
cd reinfolib-mcp
uv venv
source .venv/bin/activate  # Linux/Mac
# または .venv\Scripts\activate  # Windows
uv pip install -e ".[dev]"
```

## APIキーの取得

1. [不動産情報ライブラリ](https://www.reinfolib.mlit.go.jp/)にアクセス
2. [API利用申請](https://www.reinfolib.mlit.go.jp/help/apiManual/)ページで申請
3. 取得したAPIキーを環境変数に設定:

```bash
export REINFOLIB_API_KEY="your_api_key_here"
```

## 利用可能なAPI（30種類）

### 不動産価格情報

- **XIT001**: 不動産価格（取引価格・成約価格）情報取得
- **XIT002**: 都道府県内市区町村一覧取得
- **XIT003**: 鑑定評価書情報
- **XIT004**: 不動産価格情報のポイント (点)
- **XIT005**: 地価公示・地価調査のポイント（点）

### 都市計画決定GISデータ

- **XKT001**: 都市計画区域/区域区分
- **XKT002**: 用途地域
- **XKT003**: 立地適正化計画
- **XKT004**: 防火・準防火地域
- **XKT005**: 地区計画
- **XKT006**: 高度利用地区

### 国土数値情報（施設情報）

- **XKT007-010**: 学校関連（小学校区、中学校区、学校、保育園・幼稚園等）
- **XKT011-012**: 医療・福祉（医療機関、福祉施設）
- **XKT020**: 駅別乗降客数
- **XKT022**: 図書館
- **XKT023**: 市区町村役場及び集会施設等

### 災害・防災情報

- **XKT021**: 災害危険区域
- **XKT025**: 大規模盛土造成地マップ
- **XKT026**: 地すべり防止地区
- **XKT027**: 急傾斜地崩壊危険区域
- **XKT028**: 地形区分に基づく液状化の発生傾向図

### その他

- **XKT013**: 将来推計人口250mメッシュ
- **XKT024**: 自然公園地域

## MCPツール一覧

| ツール名 | 説明 | 主要パラメータ |
|---------|------|---------------|
| `reinfolib_search_real_estate` | 不動産取引価格検索 | prefecture, city, from_date, to_date |
| `reinfolib_get_municipalities` | 市区町村一覧取得 | prefecture, language |
| `reinfolib_get_land_price` | 地価情報取得 | zoom_level, tile_x, tile_y |
| `reinfolib_get_urban_planning` | 都市計画情報取得 | zoom_level, tile_x, tile_y, info_type |
| `reinfolib_search_facilities` | 周辺施設検索 | zoom_level, tile_x, tile_y, facility_type |
| `reinfolib_get_disaster_risk` | 災害リスク情報取得 | zoom_level, tile_x, tile_y, risk_type |
| `reinfolib_get_geospatial_data` | 統合地理空間データ取得 | latitude, longitude, data_types |
| `reinfolib_server_status` | サーバー状態確認 | なし |

## 使用例

### 基本的な検索

```python
# 東京都千代田区の2023年の不動産取引
uvx reinfolib-mcp search \
  --prefecture 13 \
  --city 13101 \
  --from-date 20230101 \
  --to-date 20231231 \
  --property-type 1 \
  --limit 10
```

### 地理座標での検索

```python
# 東京駅周辺の包括的データ取得
uvx reinfolib-mcp location \
  --latitude 35.6851 \
  --longitude 139.7514 \
  --zoom 12 \
  --data-types land_price \
  --data-types urban_planning \
  --data-types facilities \
  --data-types disaster_risk
```

### プログラムでの高度な利用

```python
from reinfolib_mcp import ReinfiolibClient, ResponseFormat

async def analyze_area(lat, lon):
    async with ReinfiolibClient() as client:
        # タイル座標計算
        import math
        z = 12
        n = 2.0 ** z
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        
        # 各種データを並行取得
        land_price, schools, medical, disaster = await asyncio.gather(
            client.get_land_price_points(z, x, y, ResponseFormat.GEOJSON),
            client.get_schools(z, x, y, ResponseFormat.GEOJSON),
            client.get_medical_facilities(z, x, y, ResponseFormat.GEOJSON),
            client.get_disaster_risk_areas(z, x, y, ResponseFormat.GEOJSON)
        )
        
        return {
            "land_price_points": len(land_price.get("features", [])),
            "schools": len(schools.get("features", [])),
            "medical_facilities": len(medical.get("features", [])),
            "disaster_areas": len(disaster.get("features", []))
        }
```

詳細な使用例は [`examples/`](./examples/) ディレクトリを参照してください。

## サポートする出力形式

- **JSON**: 構造化データ、統計分析に適用
- **GeoJSON**: 地理空間データ、地図可視化に適用  
- **PBF** (バイナリベクトルタイル): 高速描画、大容量データに適用

## 開発

### 開発環境セットアップ

```bash
git clone https://github.com/koizumikento/reinfolib-mcp.git
cd reinfolib-mcp

# uv環境作成
uv venv
source .venv/bin/activate

# 開発依存関係インストール
uv pip install -e ".[dev]"

# pre-commitフック設定
pre-commit install
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src/reinfolib_mcp --cov-report=html

# 型チェック
uv run mypy src/reinfolib_mcp

# コードフォーマット
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/

# リンティング
uv run ruff check src/ tests/ examples/
```

### MCPサーバーテスト

```bash
# 開発版MCPサーバー起動
uvx --from . reinfolib-mcp --transport http --port 3000

# 別ターミナルでテスト
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 貢献

プルリクエストやIssueは歓迎します。貢献前に [CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。
問い合わせ先は `services@straydogman.com` です。

## 関連リンク

- [不動産情報ライブラリ公式サイト](https://www.reinfolib.mlit.go.jp/)
- [API操作説明](https://www.reinfolib.mlit.go.jp/help/apiManual/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Claude Desktop](https://claude.ai/desktop)

## トラブルシューティング

### よくある問題

**Q: APIキーエラーが発生します**
A: 以下を確認してください：

- 環境変数`REINFOLIB_API_KEY`が正しく設定されているか
- APIキーが有効期限内であるか
- API利用申請が承認されているか

**Q: MCPサーバーに接続できません**
A: 以下を試してください：

- `uvx reinfolib-mcp status` でサーバー状態を確認
- Claude Desktop設定の再読み込み
- ファイアウォール設定の確認

**Q: データが取得できません**
A: 以下を確認してください：

- 指定した都道府県・市区町村コードが正しいか
- 日付形式がYYYYMMDD形式になっているか
- タイル座標が有効範囲内か

**Q: レート制限に達しました**
A: 以下を試してください：

- リクエスト間隔を空ける
- データ取得範囲を小さくする
- 非同期クライアントで適切なレート制限を設定

### サポート

- GitHub Issues: バグレポート・機能要求
- Discussions: 質問・使用方法の相談
- Email: <services@straydogman.com>（プロジェクト管理者）

---

**⭐ このプロジェクトが役立つ場合は、GitHubでスターをお願いします！**
