"""
不動産情報ライブラリMCP CLI実装

uvx実行パターンに対応したコマンドラインインターフェース
"""

import asyncio
import json
import os
import sys

import click

from .client import ReinfiolibClient
from .exceptions import ReinfiolibAPIError
from .mcp_server import run_server
from .models import Language, ResponseFormat


def get_api_key_from_env() -> str | None:
    """環境変数からAPIキーを取得"""
    return os.getenv("REINFOLIB_API_KEY")


def validate_api_key(api_key: str | None) -> str:
    """APIキーの検証"""
    if not api_key:
        click.echo("エラー: APIキーが設定されていません", err=True)
        click.echo("以下のいずれかの方法でAPIキーを設定してください:", err=True)
        click.echo("1. 環境変数: export REINFOLIB_API_KEY='your_api_key'", err=True)
        click.echo("2. コマンドオプション: --api-key your_api_key", err=True)
        click.echo("3. 対話的設定: プロンプトで入力", err=True)
        raise click.Abort()
    return api_key


@click.group(invoke_without_command=True)
@click.option(
    '--api-key',
    envvar='REINFOLIB_API_KEY',
    help='不動産情報ライブラリAPIキー（環境変数REINFOLIB_API_KEYでも設定可能）'
)
@click.option(
    '--transport',
    default='stdio',
    type=click.Choice(['stdio', 'http', 'sse']),
    help='MCPトランスポート方式（stdio、http、sse）'
)
@click.option(
    '--host',
    default='localhost',
    help='HTTPサーバーのホスト名（transport=http/sseの場合）'
)
@click.option(
    '--port',
    default=8000,
    type=int,
    help='HTTPサーバーのポート番号（transport=http/sseの場合）'
)
@click.version_option(version='0.1.0', prog_name='reinfolib-mcp')
@click.pass_context
def main(
    ctx: click.Context,
    api_key: str | None,
    transport: str,
    host: str,
    port: int
) -> None:
    """
    不動産情報ライブラリMCPツール

    国土交通省の不動産情報ライブラリAPIにアクセスするためのMCPサーバーとCLIツール。
    コマンドが指定されない場合はMCPサーバーとして起動します。

    使用例:
      uvx reinfolib-mcp                    # MCPサーバー起動（stdio）
      uvx reinfolib-mcp --transport http   # HTTPサーバー起動
      uvx reinfolib-mcp search --help      # 検索コマンドのヘルプ
      uvx reinfolib-mcp status             # サーバー状態確認
    """
    # コンテキストにパラメータを保存
    ctx.ensure_object(dict)
    ctx.obj['api_key'] = api_key
    ctx.obj['transport'] = transport
    ctx.obj['host'] = host
    ctx.obj['port'] = port

    # サブコマンドが指定されていない場合はMCPサーバーを起動
    if ctx.invoked_subcommand is None:
        # 対話的APIキー入力（必要に応じて）
        if not api_key:
            if sys.stdin.isatty():  # ターミナルでの実行時のみ
                api_key = click.prompt(
                    'APIキーを入力してください',
                    hide_input=True,
                    confirmation_prompt=False
                )
            else:
                api_key = get_api_key_from_env()

        validated_api_key = validate_api_key(api_key)
        ctx.obj['api_key'] = validated_api_key

        click.echo("不動産情報ライブラリMCPサーバーを起動します...")
        click.echo(f"トランスポート: {transport}")

        if transport != "stdio":
            click.echo(f"サーバーURL: http://{host}:{port}")

        # MCPサーバー起動
        run_server(
            api_key=validated_api_key,
            transport=transport,
            host=host,
            port=port
        )


@main.command()
@click.option(
    '--prefecture',
    required=True,
    help='都道府県コード（01-47）例：東京都=13、大阪府=27'
)
@click.option(
    '--city',
    help='市区町村コード（オプション）例：千代田区=13101'
)
@click.option(
    '--from-date',
    help='取引時期開始（YYYYMMDD形式）例：20230101'
)
@click.option(
    '--to-date',
    help='取引時期終了（YYYYMMDD形式）例：20231231'
)
@click.option(
    '--property-type',
    type=click.Choice(['1', '2', '3']),
    help='不動産種別（1:宅地、2:中古マンション等、3:中古戸建住宅）'
)
@click.option(
    '--language',
    default='ja',
    type=click.Choice(['ja', 'en']),
    help='言語（ja:日本語、en:英語）'
)
@click.option(
    '--limit',
    default=10,
    type=int,
    help='表示件数制限（デフォルト:10）'
)
@click.option(
    '--format',
    'output_format',
    default='table',
    type=click.Choice(['table', 'json', 'csv']),
    help='出力形式（table:表形式、json:JSON、csv:CSV）'
)
@click.pass_context
def search(
    ctx: click.Context,
    prefecture: str,
    city: str | None,
    from_date: str | None,
    to_date: str | None,
    property_type: str | None,
    language: str,
    limit: int,
    output_format: str
) -> None:
    """
    不動産取引価格情報を検索します

    指定した条件で不動産の取引価格情報を検索し、結果を表示します。

    使用例:
      uvx reinfolib-mcp search --prefecture 13 --limit 5
      uvx reinfolib-mcp search --prefecture 27 --city 27100 --from-date 20230101
    """
    api_key = validate_api_key(ctx.obj.get('api_key'))

    async def run_search() -> None:
        try:
            async with ReinfiolibClient(api_key=api_key) as client:
                lang = Language.ENGLISH if language == 'en' else Language.JAPANESE

                result = await client.search_real_estate_transactions(
                    prefecture=prefecture,
                    city=city,
                    from_date=from_date,
                    to_date=to_date,
                    property_type=property_type,
                    response_format=ResponseFormat.JSON,
                    lang=lang
                )

                # 結果表示
                if hasattr(result, 'dict'):
                    data = result.dict()
                else:
                    data = result

                total_count = data.get('total_count', 0)
                transactions = data.get('data', [])

                click.echo(f"検索結果: {total_count}件")

                if not transactions:
                    click.echo("該当するデータがありませんでした。")
                    return

                # 出力形式別の表示
                limited_data = transactions[:limit]

                if output_format == 'json':
                    click.echo(json.dumps(
                        {"total_count": total_count, "data": limited_data},
                        ensure_ascii=False,
                        indent=2
                    ))

                elif output_format == 'csv':
                    import csv
                    import io

                    output = io.StringIO()
                    if limited_data:
                        writer = csv.DictWriter(output, fieldnames=limited_data[0].keys())
                        writer.writeheader()
                        writer.writerows(limited_data)
                        click.echo(output.getvalue())

                else:  # table形式
                    click.echo("\n--- 取引データ ---")
                    for i, transaction in enumerate(limited_data, 1):
                        click.echo(f"\n{i}. {transaction.get('prefecture', '')} {transaction.get('city', '')}")
                        click.echo(f"   価格: {transaction.get('transaction_price', 'N/A'):,}円")
                        click.echo(f"   面積: {transaction.get('area', 'N/A')}㎡")
                        click.echo(f"   取引時期: {transaction.get('transaction_period', 'N/A')}")
                        if transaction.get('building_year'):
                            click.echo(f"   建築年: {transaction.get('building_year')}")

                if total_count > limit:
                    click.echo(f"\n注意: {total_count}件中{limit}件を表示（--limitオプションで調整可能）")

        except ReinfiolibAPIError as e:
            click.echo(f"APIエラー: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"予期しないエラー: {e}", err=True)
            sys.exit(1)

    # 非同期実行
    asyncio.run(run_search())


@main.command()
@click.option(
    '--prefecture',
    required=True,
    help='都道府県コード（01-47）例：東京都=13、北海道=01'
)
@click.option(
    '--language',
    default='ja',
    type=click.Choice(['ja', 'en']),
    help='言語（ja:日本語、en:英語）'
)
@click.option(
    '--format',
    'output_format',
    default='table',
    type=click.Choice(['table', 'json']),
    help='出力形式（table:表形式、json:JSON）'
)
@click.pass_context
def municipalities(
    ctx: click.Context,
    prefecture: str,
    language: str,
    output_format: str
) -> None:
    """
    指定都道府県の市区町村一覧を取得します

    都道府県コードを指定して、配下の全市区町村情報を取得・表示します。

    使用例:
      uvx reinfolib-mcp municipalities --prefecture 13
      uvx reinfolib-mcp municipalities --prefecture 27 --language en
    """
    api_key = validate_api_key(ctx.obj.get('api_key'))

    async def run_municipalities() -> None:
        try:
            async with ReinfiolibClient(api_key=api_key) as client:
                lang = Language.ENGLISH if language == 'en' else Language.JAPANESE

                municipalities_list = await client.get_municipalities(
                    prefecture=prefecture,
                    lang=lang
                )

                if output_format == 'json':
                    data = [m.dict() for m in municipalities_list]
                    click.echo(json.dumps(
                        {"total_count": len(data), "data": data},
                        ensure_ascii=False,
                        indent=2
                    ))
                else:  # table形式
                    click.echo(f"市区町村一覧: {len(municipalities_list)}件")
                    click.echo(f"都道府県: {municipalities_list[0].prefecture_name if municipalities_list else 'N/A'}")
                    click.echo("\n--- 市区町村 ---")

                    for municipality in municipalities_list:
                        click.echo(f"{municipality.city_code}: {municipality.city_name}")
                        if municipality.city_name_en and language == 'en':
                            click.echo(f"  (English: {municipality.city_name_en})")

        except ReinfiolibAPIError as e:
            click.echo(f"APIエラー: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"予期しないエラー: {e}", err=True)
            sys.exit(1)

    # 非同期実行
    asyncio.run(run_municipalities())


@main.command()
@click.option(
    '--latitude',
    type=float,
    required=True,
    help='緯度（例：35.6851）'
)
@click.option(
    '--longitude',
    type=float,
    required=True,
    help='経度（例：139.7514）'
)
@click.option(
    '--zoom',
    default=12,
    type=int,
    help='ズームレベル（1-18、デフォルト:12）'
)
@click.option(
    '--data-types',
    multiple=True,
    default=['land_price', 'urban_planning'],
    type=click.Choice(['land_price', 'urban_planning', 'facilities', 'disaster_risk']),
    help='取得データ種別（複数指定可能）'
)
@click.pass_context
def location(
    ctx: click.Context,
    latitude: float,
    longitude: float,
    zoom: int,
    data_types: list[str]
) -> None:
    """
    指定位置の地理空間データを取得します

    緯度経度を指定して、周辺の不動産・都市計画・施設・災害リスク情報を取得します。

    使用例:
      uvx reinfolib-mcp location --latitude 35.6851 --longitude 139.7514
      uvx reinfolib-mcp location --latitude 35.6851 --longitude 139.7514 --data-types land_price --data-types facilities
    """
    api_key = validate_api_key(ctx.obj.get('api_key'))

    # data_typesがタプルの場合はリストに変換
    if isinstance(data_types, tuple):
        data_types = list(data_types)

    async def run_location() -> None:
        try:
            from .mcp_server import create_mcp_server

            # 一時的にMCPサーバーを作成してツールを使用
            create_mcp_server(api_key)

            # get_geospatial_dataツールを直接呼び出し（簡易実装）
            import math

            # タイル座標計算
            n = 2.0 ** zoom
            tile_x = int((longitude + 180.0) / 360.0 * n)
            lat_rad = math.radians(latitude)
            tile_y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

            click.echo(f"位置情報: 緯度{latitude}, 経度{longitude}")
            click.echo(f"タイル座標: {tile_x}, {tile_y} (ズーム{zoom})")
            click.echo(f"取得データ: {', '.join(data_types)}")
            click.echo("\n--- データ取得中 ---")

            async with ReinfiolibClient(api_key=api_key) as client:
                for data_type in data_types:
                    try:
                        click.echo(f"\n{data_type}:")

                        if data_type == "land_price":
                            result = await client.get_land_price_points(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            features = result.get('features', [])
                            click.echo(f"  地価ポイント: {len(features)}件")

                        elif data_type == "urban_planning":
                            area_result = await client.get_urban_planning_area(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            zone_result = await client.get_land_use_zones(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            area_features = area_result.get('features', [])
                            zone_features = zone_result.get('features', [])
                            click.echo(f"  都市計画区域: {len(area_features)}件")
                            click.echo(f"  用途地域: {len(zone_features)}件")

                        elif data_type == "facilities":
                            schools = await client.get_schools(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            medical = await client.get_medical_facilities(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            school_features = schools.get('features', [])
                            medical_features = medical.get('features', [])
                            click.echo(f"  学校: {len(school_features)}件")
                            click.echo(f"  医療機関: {len(medical_features)}件")

                        elif data_type == "disaster_risk":
                            disaster = await client.get_disaster_risk_areas(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            liquefaction = await client.get_liquefaction_tendency(
                                z=zoom, x=tile_x, y=tile_y
                            )
                            disaster_features = disaster.get('features', [])
                            liquefaction_features = liquefaction.get('features', [])
                            click.echo(f"  災害危険区域: {len(disaster_features)}件")
                            click.echo(f"  液状化発生傾向: {len(liquefaction_features)}件")

                    except ReinfiolibAPIError as e:
                        click.echo(f"  エラー: {e}")

        except Exception as e:
            click.echo(f"予期しないエラー: {e}", err=True)
            sys.exit(1)

    # 非同期実行
    asyncio.run(run_location())


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """
    システム状態とAPI接続を確認します

    APIキーの設定状況やサーバーの健全性を確認します。
    """
    api_key = ctx.obj.get('api_key')

    click.echo("=== 不動産情報ライブラリMCP 状態確認 ===")
    click.echo("バージョン: 0.1.0")
    click.echo(f"APIキー設定: {'✓' if api_key else '✗'}")

    if not api_key:
        click.echo("環境変数REINFOLIB_API_KEYでAPIキーを設定してください")
        return

    async def check_api_connection() -> None:
        try:
            async with ReinfiolibClient(api_key=api_key) as client:
                # 簡単なAPI呼び出しでテスト
                municipalities = await client.get_municipalities("13")  # 東京都
                click.echo(f"API接続: ✓ （テスト取得: {len(municipalities)}件の市区町村）")
                click.echo(f"ベースURL: {client.base_url}")
                click.echo(f"利用可能エンドポイント: {len(client.ENDPOINTS)}種類")

        except ReinfiolibAPIError as e:
            click.echo(f"API接続: ✗ （エラー: {e}）")
        except Exception as e:
            click.echo(f"接続テスト失敗: {e}")

    # 非同期実行
    asyncio.run(check_api_connection())


if __name__ == '__main__':
    main()
