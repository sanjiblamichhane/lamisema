"""Tests for PDFPreflightService encoding detection."""

import pytest
from unittest.mock import MagicMock, patch

from lamisema.models import EncodingType, FontInfo
from lamisema.preflight import PDFPreflightService


@pytest.fixture
def svc():
    return PDFPreflightService()


def _make_font(name: str, is_legacy: bool) -> FontInfo:
    return FontInfo(name=name, encoding=None, is_legacy_nepali=is_legacy)


class TestDetermineEncodingType:
    def test_legacy_font_wins_over_text_layer(self, svc):
        fonts = [_make_font("Preeti", True)]
        assert svc._determine_encoding_type(fonts, has_text_layer=True) == EncodingType.LEGACY_ENCODED

    def test_no_text_layer_is_scanned(self, svc):
        fonts = [_make_font("Helvetica", False)]
        assert svc._determine_encoding_type(fonts, has_text_layer=False) == EncodingType.SCANNED

    def test_unicode_native_when_text_layer_present(self, svc):
        fonts = [_make_font("NotoSans", False)]
        assert svc._determine_encoding_type(fonts, has_text_layer=True) == EncodingType.UNICODE_NATIVE

    def test_empty_font_list_with_text_layer(self, svc):
        assert svc._determine_encoding_type([], has_text_layer=True) == EncodingType.UNICODE_NATIVE

    def test_empty_font_list_no_text_layer(self, svc):
        assert svc._determine_encoding_type([], has_text_layer=False) == EncodingType.SCANNED


class TestCollectFonts:
    def test_strips_subset_prefix(self, svc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = [
            (1, "type1", "Type1", "ABCDEF+Preeti", "Preeti", "WinAnsiEncoding", 0)
        ]
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        fonts = svc._collect_fonts(mock_doc)
        assert len(fonts) == 1
        assert fonts[0].name == "Preeti"
        assert fonts[0].is_legacy_nepali is True

    def test_non_legacy_font(self, svc):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = [
            (2, "type1", "Type1", "NotoSansDevanagari", "NotoSansDevanagari", "Identity-H", 0)
        ]
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        fonts = svc._collect_fonts(mock_doc)
        assert fonts[0].is_legacy_nepali is False
