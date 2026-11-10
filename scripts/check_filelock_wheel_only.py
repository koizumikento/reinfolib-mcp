"""Verify the repository's uv policy rejects source-only filelock candidates."""

import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        marker = work / "backend-executed"
        # A harmless sentinel backend detects even metadata-hook execution.
        files = {
            "pyproject.toml": (
                '[build-system]\nrequires = []\nbuild-backend = "sentinel"\n'
                'backend-path = ["."]\n[project]\nname = "filelock"\n'
                'version = "0.0.0"\n'
            ),
            "sentinel.py": (
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).touch()\n"
                "raise RuntimeError('source backend must not execute')\n"
            ),
        }
        with tarfile.open(work / "filelock-0.0.0.tar.gz", "w:gz") as archive:
            for name, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(f"filelock-0.0.0/{name}")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        env = os.environ.copy()
        # Test checked-in configuration, not an ambient wheel-only override.
        for name in ("UV_NO_BUILD", "UV_NO_BUILD_PACKAGE", "UV_CONFIG_FILE"):
            env.pop(name, None)
        env["UV_CACHE_DIR"] = str(work / "cache")
        result = subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--python",
                sys.executable,
                "--offline",
                "--no-index",
                "--find-links",
                str(work),
                "--with",
                "filelock==0.0.0",
                "python",
                "-c",
                "pass",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if marker.exists() or result.returncode == 0:
            raise AssertionError("filelock source-build policy was not enforced")
        if "building" not in result.stderr or "disabled" not in result.stderr:
            raise AssertionError(f"Unexpected installation failure: {result.stderr}")
        print("PASS: source-only filelock rejected before backend execution")


if __name__ == "__main__":
    main()
