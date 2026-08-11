from __future__ import annotations

from importlib import util
from pathlib import Path

import pytest


def _load_service_module():
    service_path = Path(__file__).resolve().parents[1] / "Coding" / "service.py"
    spec = util.spec_from_file_location("greeting_service.service", service_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load service module")

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


service = _load_service_module()


def test_greet_returns_expected_message_for_valid_name():
    assert service.greet("Ada") == "Hello, Ada!"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_greet_rejects_blank_names(value: str):
    with pytest.raises(ValueError, match="must not be empty"):
        service.greet(value)


@pytest.mark.parametrize("value", [None, 123, object()])
def test_greet_rejects_non_string_input(value):
    with pytest.raises(TypeError, match="must be a string"):
        service.greet(value)
