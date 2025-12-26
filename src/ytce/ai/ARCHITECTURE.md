## AI Architecture

This document explains the runtime flow and the responsibilities of each layer.

### High-level goal

Given:
- a set of comments
- a list of tasks (questions) describing *what* to compute

Produce:
- one `EnrichedComment` per input comment, with one `TaskResult` per task
- exportable to CSV for analysis

---

## Key domain contracts

### `TaskConfig` (`domain/task.py`)

Defines *what* to compute:
- `id`: stable key (used in CSV column names)
- `type`: task type (`binary_classification`, `multi_class`, `multi_label`, `scoring`)
- `question`: user intent
- task-specific constraints (`labels`, `max_labels`, `scale`)

### `TaskResult` (`domain/result.py`)

Normalized output per comment per task:
- `value`: `str | List[str] | float`
- `confidence`: optional `float`

### `EnrichedComment` (`domain/result.py`)

One row of output:
- `id`, `text`
- `metadata`: passthrough info like author/channel/votes
- `results`: `{task_id: TaskResult}`

### `AnalysisResult` (`domain/result.py`)

Collection-level output:
- `enriched_comments`: list of `EnrichedComment`
- stats (comment count, task count)

---

## Runtime flow (end-to-end)

### 1) Load job spec (`input/job.py`)

`load_job("questions.yaml")` → `JobSpec` containing:
- `input: InputConfig`
- `tasks: List[TaskConfig]`
- `custom_prompt: Optional[str]`

### 2) Load comments (`input/comments.py`)

`load_comments_from_config(job.input)` loads comments and maps fields using:
- `input.format`
- `input.id_field`
- `input.text_field`

This is critical when your data uses non-standard columns (e.g. `cid` + `body`).

### 3) Orchestrate (`runner/analysis.py`)

`run_analysis(job, run_config)`:
- creates a `ModelAdapter` using `create_adapter(...)`
- splits comments into batches (`run_config.batch_size`)
- for each task:
  - runs the executor on every batch
  - accumulates `{comment_id -> TaskResult}` across batches
- merges all task results into `EnrichedComment`
- returns `AnalysisResult`

### 4) Execute tasks (`tasks/`)

For each batch:
- compile prompt (`promts.compile_prompt`)
- call model (`model.generate`)
- parse JSON (`tasks.base.parse_json_response`)
- validate against `TaskConfig` (`tasks.base.validate_result_item`)
- convert into `TaskResult` objects

### 5) Export (`output/`)

`write_csv_from_analysis_result(result, "results.csv")`:
- flattens each comment into a row
- writes columns:
  - `id`, `text`, optional metadata columns
  - `{task_id}_value`, `{task_id}_confidence` for every task


