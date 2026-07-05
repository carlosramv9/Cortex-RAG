"""Settings parsing tests.

Regression coverage for the CORS origins parsing bug: pydantic-settings used to
JSON-decode the ``list[str]`` field at the source level and fail on a
comma-separated env value.
"""

from __future__ import annotations

import pytest

from app.config.settings import AppSettings
from app.shared.parsing import parse_str_list


class TestCorsOriginsFromEnv:
    """The env var must load in both comma-separated and JSON formats."""

    def test_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        settings = AppSettings()
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    def test_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_CORS_ORIGINS", '["http://localhost:3000", "http://localhost:8080"]')
        settings = AppSettings()
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    def test_single_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_CORS_ORIGINS", "http://localhost:3000")
        settings = AppSettings()
        assert settings.cors_origins == ["http://localhost:3000"]

    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APP_CORS_ORIGINS", raising=False)
        settings = AppSettings()
        assert settings.cors_origins == ["*"]

    def test_whitespace_is_trimmed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_CORS_ORIGINS", " http://a , http://b ")
        settings = AppSettings()
        assert settings.cors_origins == ["http://a", "http://b"]


class TestParseStrList:
    """The reusable parser handles every accepted input shape."""

    def test_comma_separated(self) -> None:
        assert parse_str_list("a,b,c") == ["a", "b", "c"]

    def test_json_array(self) -> None:
        assert parse_str_list('["a", "b"]') == ["a", "b"]

    def test_list_passthrough(self) -> None:
        assert parse_str_list(["a", "b"]) == ["a", "b"]

    def test_tuple_becomes_list(self) -> None:
        assert parse_str_list(("a", "b")) == ["a", "b"]

    def test_empty_string(self) -> None:
        assert parse_str_list("   ") == []
