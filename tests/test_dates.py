"""Tests for Bikram Sambat → Gregorian date normalization."""

import pytest

from lamisema.nlp.dates import bs_year_to_ad, normalize_bs_date


class TestBsYearToAd:
    def test_2081_converts_to_approx_2024(self):
        assert bs_year_to_ad("2081") == 2025  # 2081 - 56 = 2025

    def test_devanagari_year(self):
        result = bs_year_to_ad("२०८१")
        assert result == 2025

    def test_invalid_returns_none(self):
        assert bs_year_to_ad("abc") is None


class TestNormalizeBsDate:
    def test_full_date_ashadh(self):
        result = normalize_bs_date("2081", "असार", "15")
        assert result is not None
        assert "AD (approx)" in result
        assert "2024" in result  # Ashadh falls in AD year 2024

    def test_devanagari_digits(self):
        result = normalize_bs_date("२०८१", "असार", "१५")
        assert result is not None
        assert "AD (approx)" in result

    def test_unknown_month_returns_none(self):
        result = normalize_bs_date("2081", "UnknownMonth", "15")
        assert result is None

    def test_invalid_year_returns_none(self):
        result = normalize_bs_date("abcd", "असार", "15")
        assert result is None

    def test_baishakh_is_month_1(self):
        result = normalize_bs_date("2081", "बैशाख", "1")
        assert result is not None
        assert "-04-" in result  # Baishakh ≈ April
