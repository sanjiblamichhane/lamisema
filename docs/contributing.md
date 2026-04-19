# Contributing

Contributions are welcome. Here is what is most needed.

---

## What to contribute

### 1. Legacy font additions

If you have a Nepali PDF with a font LamiSema does not detect, open an issue with the font name. You can find the font name by running:

```bash
pdffonts your-file.pdf
```

Or with Python:

```python
import fitz
doc = fitz.open("your-file.pdf")
for page in doc:
    for font in page.get_fonts(full=True):
        print(font[3])  # base font name
```

Include a sample PDF (with PII removed) if possible.

Additional regex patterns for Nepali entity types. The v1.2 roadmap tracks these priority types — contributions that implement and test any of them are especially welcome.

**Note:** Since v1.0, LamiSema is language-agnostic. You can also contribute backends for other scripts (e.g. Hindi, English).

Priority Nepali types:
- `WARD_CODE` — वडा नं. X (ward number)
- `VDC_MUNICIPALITY` — गाउँपालिका / नगरपालिका names (753 local units)
- `DISTRICT` — all 77 Nepali districts
...
- `PROVINCE` — 7 province names
- `LAND_PARCEL` — कि.नं. (kittaa number), land categories (ऐलानी, रैकर, गुठी)
- `PERSON_NAME_NE` — Nepali personal names
- `PHONE_NE` — Nepali phone formats
- `COURT_CASE` — मिसिल नं., मुद्दा नं. references
- `GAZETTE_REF` — नेपाल राजपत्र volume and notice numbers
- `GOV_POSITION` — government title patterns (सचिव, महानिर्देशक, etc.)
- Vehicle registration numbers
- National ID numbers (राष्ट्रिय परिचयपत्र)

Patterns belong in `lamisema/nlp/ner.py`. Each new entity type needs a corresponding test in `tests/test_ner.py`.

### 3. Benchmark PDFs

Anonymized Nepali PDFs of each encoding type for the evaluation dataset. See `benchmark/dataset/README.md` for sourcing guidelines. Contact the maintainer before submitting to coordinate dataset logistics.

### 4. BS→AD accuracy

The current Bikram Sambat → AD conversion is approximate (±1 day). Corrections and improvements to the conversion logic in `lamisema/nlp/dates.py` are welcome, especially:

- Edge cases around Nepali New Year (mid-April)
- Correct handling of BS months 10–12 (Magh–Chaitra) year rollover
- Integration of the `nepali-datetime` library for exact conversion

---

## Development setup

```bash
git clone https://github.com/sanjiblamichhane/lamisema
cd lamisema
pip install -e ".[dev]"

# Install Tesseract
brew install tesseract tesseract-lang   # macOS

# Run tests
pytest tests/ -v

# Run linter
ruff check lamisema/ tests/
```

---

## Code standards

- All new code must have docstrings
- All new modules must have at least one test
- New entity types need a test in `tests/test_ner.py`
- New font names must be documented in `docs/encoding-types.md`
- Run `ruff check` before opening a PR — CI will fail otherwise

---

## Pull request checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Linter passes (`ruff check lamisema/ tests/`)
- [ ] New functionality has tests
- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] Documentation updated if behaviour changed
