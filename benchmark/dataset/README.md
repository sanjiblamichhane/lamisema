# Benchmark Dataset

Place PDFs in the appropriate subdirectory based on their encoding type.

```
dataset/
  unicode_native/   # Modern government portals, banks — real Unicode text layer
  legacy_encoded/   # Pre-2010 docs using Preeti, Kantipur, or Sagarmatha fonts
  scanned/          # Physical forms photographed or flatbed-scanned to PDF
```

## Target dataset size (v0.3)

- 50 unicode_native PDFs
- 50 legacy_encoded PDFs
- 50 scanned PDFs

## Sourcing guidelines

- Anonymize any personally identifiable information before committing
- Prefer publicly available government documents (budget reports, policy briefs, gazette)
- Document the source URL in a `sources.csv` file alongside the PDFs
- PDFs must be Nepali-language content to be meaningful for evaluation

## Ground truth

For each PDF added here, create a corresponding `.txt` file in `../ground_truth/`
with the manually transcribed text, and a `.entities.json` file listing the
named entities. See `../ground_truth/README.md` for the exact format.

## Note

PDF files are excluded from git via `.gitignore`. Store the dataset in a shared
location (Google Drive, S3, or a private release asset) and document the access
instructions in `sources.csv`.
