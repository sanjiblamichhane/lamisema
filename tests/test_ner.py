"""Tests for rule-based Nepali NER."""

import pytest

from lamisema.nlp import ner


class TestCurrencyNER:
    def test_rupee_devanagari_digits(self):
        entities = ner.extract_entities("रु. १२,५०० को बजेट")
        currency = [e for e in entities if e.entity_type == "CURRENCY"]
        assert len(currency) == 1
        assert "12500" in currency[0].normalized

    def test_npr_ascii(self):
        entities = ner.extract_entities("NPR 50,000 allocated")
        currency = [e for e in entities if e.entity_type == "CURRENCY"]
        assert len(currency) == 1
        assert "50000" in currency[0].normalized


class TestOrganizationNER:
    def test_mantralaya_detected(self):
        entities = ner.extract_entities("अर्थ मन्त्रालयले निर्देशन दियो")
        orgs = [e for e in entities if e.entity_type == "ORGANIZATION"]
        assert len(orgs) >= 1
        assert "मन्त्रालय" in orgs[0].text

    def test_karyalaya_detected(self):
        entities = ner.extract_entities("जिल्ला प्रशासन कार्यालय")
        orgs = [e for e in entities if e.entity_type == "ORGANIZATION"]
        assert any("कार्यालय" in o.text for o in orgs)


class TestNERConfidence:
    def test_full_date_confidence_is_high(self):
        entities = ner.extract_entities("२०८१ साल असार १५")
        dates = [e for e in entities if e.entity_type == "DATE_BS"]
        if dates:
            assert dates[0].confidence >= 0.85

    def test_currency_confidence(self):
        entities = ner.extract_entities("रु. ५०,०००")
        currency = [e for e in entities if e.entity_type == "CURRENCY"]
        if currency:
            assert currency[0].confidence >= 0.80
