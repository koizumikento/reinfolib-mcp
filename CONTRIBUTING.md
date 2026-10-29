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
git clone https://github.com/koizumikento/reinfolib-mcp.git
cd reinfolib-mcp

uv sync --frozen --extra dev
```

サーバー・開発環境ともに Python 3.11〜3.13 が必要です。dnspython の修正版
`>=2.9.0,<3` を使用するため、Python 3.10 はサポートしません。
`pre-commit` と `filelock>=4.2.4,<5` は引き続き開発用 extra のみの依存です。
pre-commit を通常の開発環境から分離する場合は、次のように設定します。

```bash
# Python 3.11 の開発・テスト環境
uv sync --frozen --extra dev --python 3.11
uv run --frozen --extra dev --python 3.11 pytest

# pre-commit 用の独立した Python 3.11 環境（.venv は変更しない）
UV_PROJECT_ENVIRONMENT=.cache/pre-commit uv sync --frozen --extra dev --python 3.11
UV_PROJECT_ENVIRONMENT=.cache/pre-commit uv run --frozen --extra dev --python 3.11 pre-commit --version
```

現在このリポジトリには `.pre-commit-config.yaml` がないため、hook の登録・実行は
その設定を用意してから行います。pre-commit が作成する個々の Python hook 環境では
依存関係が別途インストールされ、プロジェクトの `uv.lock` は自動適用されません。
hook 自体のバージョンと依存関係は別途管理してください。

## 事前チェック

Pull Request 前に、少なくとも以下を実行してください。

```bash
uv run --frozen --extra dev pytest
uv run --frozen --extra dev mypy src/reinfolib_mcp
uv run --frozen --extra dev ruff check src/ tests/ examples/
uv run --frozen --extra dev black --check src/ tests/ examples/
uv run --frozen --extra dev isort --check-only src/ tests/ examples/
```

## コーディング方針

- Python 3.11 以上、3.14 未満を前提にします
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
