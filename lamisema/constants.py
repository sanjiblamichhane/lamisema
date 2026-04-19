"""
Shared constants for the LamiSema Nepali PDF extraction engine.

All values here are linguistically grounded — changes should reference
the specific Unicode block, font spec, or BS calendar rule being updated.
"""

from typing import Dict

# Devanagari Unicode block: U+0900 – U+097F
DEVANAGARI_RANGE = (0x0900, 0x097F)

# Fonts that encode Devanagari using ASCII codepoints (legacy pre-Unicode fonts).
# Any PDF containing these fonts MUST go through OCR — never direct text extraction.
# Text layer output from these fonts is silent garbage: "g]kfn" instead of "नेपाल".
#
# To add a new font: open an issue at github.com/sanjiblamichhane/lamisema
# with the font name (from `pdffonts your-file.pdf`) and a sample PDF.
LEGACY_NEPALI_FONTS = {
    # Core legacy fonts — most common in government and media documents
    "Preeti",           # most widely used; government forms, newspapers
    "Sagarmatha",       # government documents, older NGO reports
    "Kantipur",         # Kantipur Media Group publications
    "Himali",           # official government correspondence
    "Himali TT",        # TrueType variant of Himali
    "PCS Nepali",       # public service documents
    "Navjeevan",        # religious texts, older publications
    "Narad",            # older government records
    "Fontasy Himali",   # desktop publishing, older websites
    "Fontasy Himalb",   # bold variant of Fontasy Himali
    "Kanjirowa",        # regional government documents
    "Kuti",             # older academic and research documents
    # Extended font list — community-verified
    "Shangrila",        # travel and tourism sector documents
    "GuptaLipi",        # some district court records
    "Sabdatara",        # educational materials
    "Sambhav",          # legal documents
    "Everest",          # newspaper archives
    "Nepal",            # generic legacy font name used by multiple vendors
    "Ratna",            # some government publications
    "Devanagari",       # generic name used by legacy font vendors (not the Unicode block)
}

# Maps Devanagari digit characters → ASCII digit characters.
# Example: '१' (U+0967) → '1'
DEVANAGARI_DIGIT_MAP = str.maketrans("०१२३४५६७८९", "0123456789")

# Bikram Sambat month names (with common spelling variants) → month number.
# Month 1 = Baishakh (starts mid-April in the Gregorian calendar).
BS_MONTH_NAMES: Dict[str, int] = {
    "बैशाख": 1, "बैसाख": 1,
    "जेठ": 2, "जेष्ठ": 2,
    "असार": 3, "आसाढ": 3, "अषाढ": 3,
    "साउन": 4, "श्रावण": 4,
    "भदौ": 5, "भाद्र": 5,
    "असोज": 6, "आश्विन": 6,
    "कार्तिक": 7,
    "मंसिर": 8, "मार्गशीर्ष": 8,
    "पुष": 9, "पौष": 9,
    "माघ": 10,
    "फागुन": 11, "फाल्गुन": 11,
    "चैत": 12, "चैत्र": 12,
}

# BS months 1–9 (Baishakh–Poush) fall in AD year = BS year - 57.
# BS months 10–12 (Magh–Chaitra) fall in AD year = BS year - 56.
BS_TO_AD_MONTH_OFFSET = 3   # add to BS month (mod 12) to approximate AD month
BS_TO_AD_YEAR_OFFSET = 56   # 2081 BS ≈ 2024/2025 AD

# Nepali organizational entity suffixes used for rule-based NER.
NEPALI_ORG_SUFFIXES = [
    "कार्यालय", "समिति", "विभाग", "मन्त्रालय", "संस्था",
    "प्रतिष्ठान", "निगम", "बोर्ड", "आयोग", "परिषद",
]
