## Troubleshooting AI analysis

### `ytce analyze` fails with `File not found: ./comments.csv`

`questions.yaml` controls where comments are loaded from:

- Update `input.path` to a real file you have (CSV/JSONL/Parquet), or
- Run from a directory where `./comments.csv` exists.

Tip: the repo includes test data under `data/` (e.g. `data/test_comments.csv`).

---

### My CSV uses different column names (e.g. `cid`, `body`)

Set the mapping in `questions.yaml`:

```yaml
input:
  path: "./my_comments.csv"
  format: csv
  id_field: cid
  text_field: body
```

---

### `ytce analyze` fails with “Missing API key”

For real runs you need an API key:
- pass `--api-key ...`, or
- set `OPENAI_API_KEY` in your environment

To run without network calls (mock mode):

```bash
ytce analyze questions.yaml --dry-run -o out.csv
```

---

### Parquet load fails (ImportError about pandas)

Parquet support requires extra deps:
- `pandas`
- `pyarrow`

Install them, or use CSV/JSONL instead.

---

### Model output is not valid JSON / task validation fails

Symptoms:
- `InvalidResponseError`
- errors like “Unknown comment_id” or “Value not in allowed labels”

Mitigations:
- reduce `--batch-size` (smaller prompts / lower error rate)
- ensure labels/scales in `questions.yaml` are correct
- re-run in `--dry-run` to validate plumbing first


