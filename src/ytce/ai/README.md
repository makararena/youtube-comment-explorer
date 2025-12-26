## AI module overview (`ytce.ai`)

This folder is a **standalone AI analysis engine** for text comments. It is designed to work on any comment source (YouTube, CSV exports, etc.) and produce **structured, CSV-ready** results.

### What you can do

- Load comments from **CSV / JSONL / Parquet**
- Define analysis tasks in `questions.yaml` (classification + scoring)
- Run analysis in batches using an LLM (or `--dry-run` mock mode)
- Export results to a **flat CSV** (one row per comment)

---

## Architecture (layers)

### Domain (`domain/`)
Pure immutable data models (no I/O, no API calls):
- `Comment`: input comment object
- `TaskConfig`, `TaskType`: describes *what* to compute
- `TaskResult`, `EnrichedComment`, `AnalysisResult`: normalized outputs

### Input (`input/`)
Parsers + validators:
- `input/job.py`: loads `questions.yaml` into `JobSpec`
- `input/comments.py`: loads comments from file **and respects `InputConfig` mapping** (`id_field`, `text_field`, `format`)

### Prompts (`promts/`)
Prompt compiler (note the directory name typo is intentional for now):
- Builds deterministic prompts per `TaskType`
- Enforces a strict JSON output shape

### Models (`models/`)
LLM adapters:
- `OpenAIAdapter`: real OpenAI calls (requires `openai` package + API key)
- `MockAdapter`: used when `RunConfig.dry_run=True` (no network calls)

### Tasks (`tasks/`)
Task executors (pure execution logic, no file I/O):
- Compile prompts → call model → parse/validate JSON → return `TaskResult`

### Runner (`runner/`)
Orchestrator:
- Loads comments (via `InputConfig`)
- Batches comments (`RunConfig.batch_size`)
- Runs all tasks across all batches
- Merges into `EnrichedComment` and returns `AnalysisResult`

### Output (`output/`)
CSV export:
- Flattens results into columns like `{task_id}_value` and `{task_id}_confidence`

---

## The `questions.yaml` contract

`questions.yaml` is the job definition file. Example:

```yaml
version: 1
input:
  path: "./comments.csv"
  format: csv
  id_field: cid
  text_field: body

custom_prompt: ""

tasks:
  # Translation example
  - id: translation_ru
    type: translation
    question: "Translate this comment to Russian, preserving meaning and tone."
    target_language: "Russian"

  # Sentiment analysis
  - id: sentiment
    type: multi_class
    question: "What is the sentiment of this comment?"
    labels: ["positive", "neutral", "negative"]

  # Toxicity scoring
  - id: toxicity
    type: scoring
    question: "How toxic is this comment?"
    scale: [0.0, 1.0]
```

### Supported task types

- `translation` → `value` is a translated text string (requires `target_language`)
- `binary_classification` → `value` is a string from 2 labels
- `multi_class` → `value` is a string from N labels
- `multi_label` → `value` is a list of labels (optionally `max_labels`)
- `scoring` → `value` is a float inside `scale`

---

## How to run

### CLI (recommended)

The CLI command is:

```bash
ytce analyze questions.yaml -o results.csv --dry-run
```

For a real run, provide an API key:

```bash
export OPENAI_API_KEY="..."
ytce analyze questions.yaml -o results.csv --model gpt-4.1-nano
```

### Python (direct)

```python
from ytce.ai.input.job import load_job
from ytce.ai.domain.config import RunConfig
from ytce.ai.runner import run_analysis
from ytce.ai.output import write_csv_from_analysis_result

job = load_job("questions.yaml")
run_cfg = RunConfig(model="gpt-4.1-nano", api_key="...", batch_size=20, dry_run=True)

result = run_analysis(job, run_cfg)
write_csv_from_analysis_result(result, "results.csv")
```

---

## Common pitfalls / debugging

- **Your CSV columns don’t match**: set `input.id_field` and `input.text_field` correctly in `questions.yaml`.
- **No `ytce analyze` command**: should exist; if not, you’re on an older version.
- **Missing OpenAI dependency**: install `openai` (or run with `--dry-run`).
- **Model returns invalid JSON**: task executors validate output and will error. Try smaller `batch_size` and/or stricter prompts.

---

## Data flow (end-to-end)

1. `load_job()` reads `questions.yaml` → `JobSpec`
2. `run_analysis()` loads comments using `InputConfig`
3. For each task:
   - batch comments
   - `tasks.execute_task()` → prompt → model → JSON → `TaskResult`
4. Merge results into `EnrichedComment`
5. Export with `output.write_csv_*()`


