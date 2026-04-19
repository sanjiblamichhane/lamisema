# Ground Truth Files

One `.txt` and one `.entities.json` file per PDF in `../dataset/`.
File stems must match exactly: `budget-2081.pdf` → `budget-2081.txt` + `budget-2081.entities.json`

## Text file format (`*.txt`)

Plain UTF-8 text. Manually transcribed by a native Nepali speaker.
Preserve paragraph breaks. Do not normalize punctuation or digits —
keep Devanagari digits and danda (।) as they appear in the source.

## Entity file format (`*.entities.json`)

JSON array. Each element has:

```json
[
  {
    "text": "२०८१ साल असार १५",
    "entity_type": "DATE_BS",
    "normalized": "~2024-06-29 AD (approx)"
  },
  {
    "text": "रु. १२,५००",
    "entity_type": "CURRENCY",
    "normalized": "NPR 12500"
  },
  {
    "text": "अर्थ मन्त्रालय",
    "entity_type": "ORGANIZATION",
    "normalized": null
  }
]
```

Valid `entity_type` values: `DATE_BS`, `CURRENCY`, `ORGANIZATION`

## Transcription guidelines

- Transcribe what is printed, not what is meant
- For scanned documents with unclear characters, mark as `[unclear]`
- Do not correct spelling errors in the source document
- Ground truth text files are excluded from git via `.gitignore`
  — store alongside the PDFs in the shared dataset location
