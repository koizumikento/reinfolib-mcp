"""Check the published development extra across supported Python versions."""

from importlib.metadata import metadata, requires

import pytest
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


@pytest.mark.parametrize("python_version", ["3.10", "3.11", "3.13"])
def test_hook_dependencies_only_apply_on_python_311_and_later(python_version):
    requirements = [Requirement(value) for value in requires("reinfolib-mcp")]
    environment = {
        **default_environment(),
        "python_version": python_version,
        "python_full_version": f"{python_version}.0",
    }
    for extra in ["", "test", "dev"]:
        selected = {
            item.name
            for item in requirements
            if item.marker is None
            or item.marker.evaluate({**environment, "extra": extra})
        }
        expected = extra == "dev" and python_version != "3.10"
        assert ("pre-commit" in selected) == expected
        assert ("filelock" in selected) == expected


def test_filelock_security_floor_preserves_runtime_python_support():
    requirements = [Requirement(value) for value in requires("reinfolib-mcp")]
    filelock = next(item for item in requirements if item.name == "filelock")
    assert "4.2.3" not in filelock.specifier
    assert "4.2.4" in filelock.specifier
    assert "5.0.0" not in filelock.specifier
    supported = SpecifierSet(metadata("reinfolib-mcp")["Requires-Python"])
    assert "3.10.0" in supported
    assert "3.13.0" in supported
    assert "3.14.0" not in supported
