# Benchmark

## Evaluation Methodology

LamiSema is evaluated against manually transcribed ground truth across three PDF encoding types.

### Dataset Target

| Encoding Type | Count | Source |
|---|---|---|
| `unicode_native` | 50 PDFs | mof.gov.np, opm.gov.np, nnpc.gov.np, World Bank Nepal |
| `legacy_encoded` | 50 PDFs | District offices, court records, pre-2010 government archives |
| `scanned` | 50 PDFs | Physical forms, field survey records, land registry scans |

Ground truth transcription by native Nepali speakers. PII anonymized before storage.

### Metrics

**Character Error Rate (CER)**

```
CER = Levenshtein(hypothesis, reference) / len(reference)
```

Lower is better. 0.0 = perfect match. Capped at 1.0.

**Entity F1**

Precision, Recall, and F1 per entity type (`DATE_BS`, `CURRENCY`, `ORGANIZATION`). Matching is exact surface form (lowercased).

**Date Normalization Accuracy**

Fraction of detected BS dates whose normalized AD value matches ground truth.

### Baseline Comparison

The evaluation script (`benchmark/evaluate.py`) compares three extraction strategies:

| Strategy | Description |
|---|---|
| `pdfplumber_raw` | Raw text extraction — no routing, no OCR fallback |
| `tesseract_raw` | Tesseract on every page — no pre-flight routing |
| `lamisema` | Full LamiSema pipeline with encoding-aware routing |

Run the comparison:

```bash
python benchmark/evaluate.py --baselines
```

---

## Results

> ⚠️ **Formal benchmark results are pending.** The dataset collection and native-speaker transcription are in progress.

Expected to be published here before the v1.1 release. The evaluation script is complete and ready — only the dataset needs to be populated.

### Expected findings

Based on manual spot-checks during development:

- **unicode_native**: LamiSema and raw pdfplumber should be nearly identical (both use text layer). Tesseract will introduce minor OCR errors.
- **legacy_encoded**: Raw pdfplumber will produce ~100% CER (garbage output). LamiSema's OCR routing will produce ~15–30% CER depending on scan quality.
- **scanned**: Raw pdfplumber returns empty string (CER = 1.0). LamiSema and raw Tesseract should be comparable; LamiSema adds NER and confidence scoring on top.

---

## Running the Evaluation

```bash
# Full evaluation against all three encoding types
python benchmark/evaluate.py

# Single encoding type
python benchmark/evaluate.py --type legacy_encoded

# With baseline comparison
python benchmark/evaluate.py --baselines

# Custom dataset location
python benchmark/evaluate.py \
  --dataset-dir /path/to/dataset \
  --gt-dir /path/to/ground_truth
```

### Adding PDFs to the dataset

1. Place PDFs in `benchmark/dataset/<encoding_type>/`
2. Create `benchmark/ground_truth/<pdf_stem>.txt` with manually transcribed text
3. Create `benchmark/ground_truth/<pdf_stem>.entities.json` with ground truth entities
4. Run `python benchmark/evaluate.py`

See `benchmark/ground_truth/README.md` for the exact file format.
