# CONTRIBUTING

`reinfolib-mcp` への貢献を歓迎します。Issue、ドキュメント修正、バグ修正、機能追加のいずれも歓迎です。

## 連絡先

- プロジェクト管理者メール: `services@straydogman.com`

大きめの変更や仕様相談は、実装前に Issue で方向性を共有してください。

## 貢献の進め方

1. 既存の Issue や README を確認し、重複提案を避ける
2. 変更内容に応じてブランチを切る
3. テストと静的解析を通す
4. 変更理由が分かる形で Pull Request を作成する

## 開発環境

```bash
git clone https://github.com/username/reinfolib-mcp.git
cd reinfolib-mcp

uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

## 事前チェック

Pull Request 前に、少なくとも以下を実行してください。

```bash
uv run pytest
uv run mypy src/reinfolib_mcp
uv run ruff check src/ tests/ examples/
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/
```

## コーディング方針

- Python 3.10 以上を前提にします
- フォーマットは `black`、import 整理は `isort`、lint は `ruff`、型チェックは `mypy` を使用します
- 既存の命名規則と API インターフェースを優先し、互換性を壊す変更は明示してください
- 新機能追加時は、可能な限り `tests/` に対応テストを追加してください

## Pull Request の目安

- 変更の背景と目的が説明されている
- ユーザー影響がある場合は挙動差分が説明されている
- 追加した設定値や環境変数があれば README か PR 説明に記載されている
- 必要に応じて実行コマンドや検証結果が添えられている

## ドキュメント修正

README や `examples/` の更新だけでも歓迎です。コード例を変更する場合は、現在の実装と矛盾しないことを確認してください。
