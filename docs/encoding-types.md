# The Nepali PDF Encoding Problem

Understanding why LamiSema exists requires understanding how Nepali PDFs store text — and why getting it wrong is invisible.

---

## Three Encoding Types

Nepali PDFs fall into exactly three categories. Each requires a completely different extraction strategy. Using the wrong one produces silent corruption — no error, no warning.

### 1. Unicode-Native

**Source:** Modern government portals (e.g. mof.gov.np), banks, international organizations, documents produced after ~2010.

**How it works:** Characters are stored as actual Unicode codepoints in the Devanagari block (U+0900–U+097F). The text layer contains real `न`, `े`, `प`, `ा`, `ल` characters.

**Extraction:** Direct text layer extraction via pdfplumber or PyMuPDF. Fast (milliseconds per page), lossless, no OCR needed.

**Detection:** Font encoding is `Identity-H`, `WinAnsiEncoding`, or a standard Unicode CMap. No legacy font names present.

---

### 2. Legacy-Encoded (Preeti / Kantipur / Sagarmatha)

**Source:** Government documents from before ~2010, district offices, many court records, land registry documents, older newspaper archives.

**How it works:** These fonts were created before Unicode existed. They work by **remapping ASCII codepoints** to render as Devanagari glyphs. The font file maps `g` → `न`, `]` → `े`, `k` → `प`, `f` → `ा`, `n` → `ल`. So the word "नेपाल" is stored as the ASCII string `g]kfn`.

On screen, the PDF looks perfect because the rendering engine applies the font map. But in the text layer, the stored bytes are ASCII.

**What happens without encoding detection:**

```
pdfplumber.open("preeti-budget.pdf").pages[0].extract_text()
# → 'g]kfn ;/sf/ sf] cfGtl/s /fh:j'
# Looks like garbage. It IS garbage. No error raised.
```

**Extraction:** The text layer must be completely bypassed. LamiSema renders each page at 300 DPI and runs Tesseract OCR (`nep+eng`). The rendered image accurately shows the Devanagari glyphs, and Tesseract reads them correctly.

**Detection:** PyMuPDF's `page.get_fonts()` returns font metadata including the base font name. LamiSema strips subset prefixes (`ABCDEF+Preeti` → `Preeti`) and checks against a list of 20+ known legacy Nepali font names.

---

### 3. Scanned / Image

**Source:** Physical forms scanned to PDF, old records photographed, faxed documents, field survey forms.

**How it works:** The PDF contains no text layer at all — just a rasterized image of each page. `page.extract_text()` returns an empty string.

**Extraction:** Same as legacy-encoded: render at 300 DPI and run OCR. The difference is detection — no fonts to inspect, just an absence of text.

**Detection:** LamiSema checks the first three pages for any extractable text. If none is found and no legacy fonts are present, the document is classified as scanned.

---

## Why 300 DPI

Tesseract's Devanagari accuracy degrades significantly below 300 DPI. Devanagari characters have complex conjuncts and matras (vowel signs) that sit above, below, and around consonants. At 150 DPI many of these become indistinguishable. At 300 DPI, the distinction between visually similar characters — ग vs ग़, ध vs ब, ी vs ि — becomes reliable.

300 DPI also produces large images (a typical A4 page becomes ~2480×3508 pixels). LamiSema processes them in memory and does not write to disk.

---

## The Silent Failure Problem

The reason this matters is that **no error is raised** when the wrong strategy is applied:

| Scenario | What you see | What actually happened |
|---|---|---|
| Unicode PDF + pdfplumber | Clean Devanagari text | Correct |
| Legacy PDF + pdfplumber | `g]kfn ;/sf/` or similar | Silent corruption |
| Scanned PDF + pdfplumber | Empty string `""` | Silent miss |
| Legacy PDF + Tesseract (no pre-flight) | Correct OCR output | Correct but slow |
| Unicode PDF + Tesseract (no pre-flight) | Mostly correct with OCR errors | Unnecessary degradation |

The last row is why routing matters even when OCR works: running OCR on a clean Unicode PDF introduces character errors that were not in the original document and wastes significant time.

---

## Known Legacy Nepali Fonts

LamiSema's pre-flight detector identifies all of the following:

| Font | Common usage |
|---|---|
| Preeti | Most common; government forms, newspapers |
| Kantipur | Kantipur Media Group publications |
| Sagarmatha | Government documents, older NGO reports |
| Himali | Official government correspondence |
| Himali TT | TrueType variant of Himali |
| PCS Nepali | Public service documents |
| Navjeevan | Religious texts, older publications |
| Narad | Older government records |
| Fontasy Himali | Desktop publishing, older websites |
| Fontasy Himalb | Bold variant of Fontasy Himali |
| Kanjirowa | Regional government documents |
| Kuti | Older academic and research documents |
| Shangrila | Travel and tourism sector documents |
| GuptaLipi | Some district court records |
| Sabdatara | Educational materials |
| Sambhav | Legal documents |
| Everest | Newspaper archives |
| Nepal | Generic legacy font |
| Ratna | Some government publications |
| Devanagari | Generic name used by multiple legacy vendors |

If you encounter a legacy font not in this list, open a GitHub issue with the font name (visible via `pdffonts your-file.pdf`).
