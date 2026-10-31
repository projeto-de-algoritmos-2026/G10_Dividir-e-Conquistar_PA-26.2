# Issue 3 — IO Layer and Validation Plan

## Top-Level Overview

**Goal:** Build the data-loading and validation layer for RankLab, turning valid JSON files into
typed Python domain objects (`Ranking`, `ScoringMatrix`) and rejecting every malformed input with
a precise, actionable error message.

**Scope:**
- Create `src/ranklab/domain/` with dataclass models.
- Create `src/ranklab/io/` with readers that parse, validate, and return domain objects.
- Add a test suite under `tests/` using pytest.
- Wire the readers into the CLI so the example files can be loaded end-to-end.

**Out of scope:** Algorithm implementations (Issue 4), output formatting beyond error messages,
any format other than JSON v1.

**Approach:** Work layer-by-layer — domain models first, then validation errors, then the readers,
then tests, then CLI wiring — so each layer depends only on already-completed work.

---

## Sub-Tasks

---

### Sub-Task 1 — Project scaffolding and test setup

**Intent:** Create the directory skeleton and wire pytest as a dev dependency, so every
subsequent sub-task has a place to land and can be verified immediately.

**Expected Outcomes:**
- `src/ranklab/domain/__init__.py`, `src/ranklab/io/__init__.py`, and `tests/` exist.
- `pyproject.toml` declares `pytest` under `[project.optional-dependencies] dev`.
- Running `pytest` (with no tests yet) exits 0 with "no tests collected".

**Todo List:**
1. Create `src/ranklab/domain/__init__.py` (empty).
2. Create `src/ranklab/io/__init__.py` (empty).
3. Create `tests/__init__.py` (empty) and `tests/` directory.
4. Add `[project.optional-dependencies]` section to `pyproject.toml` with `dev = ["pytest>=8"]`.
5. Add `[tool.pytest.ini_options]` section pointing `testpaths = ["tests"]`.
6. Reinstall in editable mode (`pip install -e ".[dev]"`) and confirm `pytest --collect-only` works.

**Relevant Context:**
- `pyproject.toml` — add the two new sections.
- No existing test infrastructure; the repo uses standard-library only so far.

**Status:** [x] done

---

### Sub-Task 2 — Domain models (`Ranking` and `ScoringMatrix`)

**Intent:** Define the "common model" that the rest of the application works with after a file
has been validated. These dataclasses are the contract between IO and algorithms; they must be
fully typed and carry only clean, validated data.

**Expected Outcomes:**
- `src/ranklab/domain/models.py` exports `RankingItem`, `Ranking`, `Criterion`, `MatrixItem`, `ScoringMatrix`.
- All classes are frozen dataclasses (immutable after construction).
- Types match the contract: positions are `int`, values are `float`, directions are a `Literal` or `enum`.
- No validation logic lives here — models are plain data containers.

**Todo List:**
1. Create `src/ranklab/domain/models.py`.
2. Define `Direction` as a `str` enum with members `HIGHER_IS_BETTER` and `LOWER_IS_BETTER`.
3. Define `RankingItem(item_id: str, position: int)` as a frozen dataclass.
4. Define `Ranking(ranking_id, name, origin, items: tuple[RankingItem, ...])` as a frozen dataclass.
   - `items` is stored sorted by `position` ascending.
5. Define `Criterion(criterion_id, name, direction: Direction, unit: str)` as a frozen dataclass.
6. Define `MatrixItem(item_id: str, values: dict[str, float])` as a frozen dataclass.
7. Define `ScoringMatrix(matrix_id, name, origin, criteria: tuple[Criterion, ...], items: tuple[MatrixItem, ...])` as a frozen dataclass.
8. Export all public names from `src/ranklab/domain/__init__.py`.

**Relevant Context:**
- `docs/contratos-dados.md` — field names and semantics.
- `examples/ranking.json` and `examples/matriz.json` — concrete examples.

**Status:** [x] done

---

### Sub-Task 3 — Validation error type

**Intent:** Create a dedicated exception class (`RankLabError`) that carries structured
information (file name, field path, human-readable reason). All reader errors will raise this
type, making it trivial for the CLI and tests to catch and format them.

**Expected Outcomes:**
- `src/ranklab/io/errors.py` exports `RankLabError`.
- `RankLabError` stores `filename`, `field_path` (e.g. `"items[1].values.custo"`), and `reason`.
- `str(error)` produces the format mandated by the data contract:
  `"{filename}: {field_path}: {reason}"`.
- When `field_path` is absent (top-level file errors), the format is `"{filename}: {reason}"`.

**Todo List:**
1. Create `src/ranklab/io/errors.py`.
2. Define `RankLabError(Exception)` with `__init__(self, filename, reason, field_path=None)`.
3. Implement `__str__` to produce the mandated format.
4. Export `RankLabError` from `src/ranklab/io/__init__.py`.
5. Write a small unit test in `tests/test_errors.py` verifying both format variants.

**Relevant Context:**
- Error format specified in `docs/contratos-dados.md` §"Precisão e erros":
  `"matriz.json: items[1].values.custo: valor ausente"`.

**Status:** [x] done

---

### Sub-Task 4 — Ranking reader and validator

**Intent:** Implement the function that takes a file path (or raw dict from `json.load`), runs
all ranking-specific validations, and returns a `Ranking` domain object.

**Expected Outcomes:**
- `src/ranklab/io/readers.py` exports `load_ranking(path: str | Path) -> Ranking`.
- All checks listed below raise `RankLabError` with precise `field_path`:
  - Missing required top-level fields (`format_version`, `ranking_id`, `name`, `origin`, `items`).
  - Unsupported `format_version` (anything other than `1`).
  - `items` is not a non-empty list.
  - Any item missing `item_id` or `position`.
  - `position` is not a positive integer (no floats, no strings, no non-positive values).
  - Duplicate `item_id` values.
  - Duplicate `position` values.
  - Positions are not exactly the set `{1, …, n}` (gaps or out-of-range values).
- Valid files return a `Ranking` with items sorted by position.

**Todo List:**
1. Create `src/ranklab/io/readers.py` with a private `_validate_ranking(data, filename)` helper and the public `load_ranking` function.
2. Implement JSON file loading (handle `FileNotFoundError`, `json.JSONDecodeError` as `RankLabError`).
3. Implement each validation check listed above, raising `RankLabError` with the appropriate `field_path`.
4. On success, construct and return `Ranking` from validated data.

**Relevant Context:**
- `docs/contratos-dados.md` §"Ranking estrito".
- `examples/ranking.json` — must load cleanly.
- `src/ranklab/domain/models.py` — target types.

**Status:** [x] done

---

### Sub-Task 5 — Scoring matrix reader and validator

**Intent:** Implement the function that loads and validates a scoring matrix file, returning a
`ScoringMatrix` domain object.

**Expected Outcomes:**
- `src/ranklab/io/readers.py` also exports `load_matrix(path: str | Path) -> ScoringMatrix`.
- All checks below raise `RankLabError`:
  - Missing required top-level fields (`format_version`, `matrix_id`, `name`, `origin`, `criteria`, `items`).
  - Unsupported `format_version`.
  - `criteria` is not a non-empty list.
  - Any criterion missing `criterion_id`, `name`, `direction`, or `unit`.
  - `direction` is not `"higher_is_better"` or `"lower_is_better"`.
  - Duplicate `criterion_id` values.
  - `items` is not a non-empty list.
  - Any item missing `item_id` or `values`.
  - Duplicate `item_id` values.
  - Any item's `values` is missing a declared criterion or contains an extra criterion.
  - Any value is not a finite real number (rejects `null`, booleans, strings, missing keys).
- Valid files return a `ScoringMatrix`.

**Todo List:**
1. Add `_validate_matrix(data, filename)` helper and `load_matrix` function to `src/ranklab/io/readers.py`.
2. Implement JSON file loading shared logic (reuse or call the same file-open helper from the ranking reader).
3. Implement all validation checks, raising `RankLabError` with field paths like `"criteria[0].direction"` and `"items[2].values.qualidade"`.
4. On success, construct and return `ScoringMatrix` from validated data.

**Relevant Context:**
- `docs/contratos-dados.md` §"Matriz de pontuação" and §"Precisão e erros".
- `examples/matriz.json` — must load cleanly.

**Status:** [x] done

---

### Sub-Task 6 — Comparative item-set validation

**Intent:** Implement the cross-ranking check from the data contract: when two rankings are
compared, they must contain exactly the same set of `item_id`s.

**Expected Outcomes:**
- `src/ranklab/io/readers.py` exports `assert_same_item_set(ranking_a, ranking_b)`.
- Raises `RankLabError` (or a `ValueError`) with a message naming the symmetric difference when the sets differ.
- Raises nothing when the sets are identical.

**Todo List:**
1. Add `assert_same_item_set(a: Ranking, b: Ranking) -> None` to `src/ranklab/io/readers.py`.
2. Compute the symmetric difference of `item_id` sets from both rankings.
3. If non-empty, raise `RankLabError` listing the differing IDs (e.g. `"rankings differ in item_ids: {id1, id2}"`).
4. Export from `src/ranklab/io/__init__.py`.

**Relevant Context:**
- `docs/contratos-dados.md` §"Ranking estrito": "Ao comparar dois rankings, ambos devem conter exatamente o mesmo conjunto de `item_id`."

**Status:** [x] done

---

### Sub-Task 7 — Test suite

**Intent:** Write pytest tests that cover the happy path (example files load cleanly) and the
main error paths (each category of invalid input raises `RankLabError` with the right message).

**Expected Outcomes:**
- `tests/test_ranking_reader.py` — valid load of `examples/ranking.json`, plus tests for every
  validation category (missing fields, bad position types, gaps, duplicates).
- `tests/test_matrix_reader.py` — valid load of `examples/matriz.json`, plus tests for every
  validation category.
- `tests/test_item_set.py` — matching and mismatched ranking pairs.
- All tests pass with `pytest`.

**Todo List:**
1. Create `tests/test_ranking_reader.py`:
   - Happy path: load `examples/ranking.json` and assert the returned `Ranking` fields.
   - Error paths: one test per validation rule.
2. Create `tests/test_matrix_reader.py`:
   - Happy path: load `examples/matriz.json` and assert the returned `ScoringMatrix` fields.
   - Error paths: one test per validation rule.
3. Create `tests/test_item_set.py`:
   - Happy path: two identical item sets.
   - Error path: symmetric difference of one ID.
4. Run `pytest` and confirm all tests pass.

**Relevant Context:**
- `examples/ranking.json` and `examples/matriz.json` — use these as fixture files.
- All readers and error types from previous sub-tasks.

**Status:** [x] done

---

### Sub-Task 8 — CLI wiring

**Intent:** Update the CLI so users can actually load a file from the command line and either see
a success summary or a clear error. This satisfies the acceptance criterion "exemplos documentados
podem ser carregados pela aplicação."

**Expected Outcomes:**
- `ranklab load-ranking <path>` prints a one-line summary (ranking_id, n items) on success, or
  prints the `RankLabError` message and exits non-zero on failure.
- `ranklab load-matrix <path>` does the same for matrices.
- `ranklab --info` still works.
- The updated help text lists the two new sub-commands.

**Todo List:**
1. Add `load-ranking` and `load-matrix` sub-commands to `build_parser()` in `src/ranklab/cli.py`.
2. In `main()`, dispatch to `load_ranking` / `load_matrix`, catching `RankLabError` and printing
   its string representation to stderr, then returning exit code 1.
3. On success, print a human-readable summary line to stdout and return 0.
4. Manually verify: `ranklab load-ranking examples/ranking.json` and `ranklab load-matrix examples/matriz.json`.

**Relevant Context:**
- `src/ranklab/cli.py` — existing skeleton to extend.
- `src/ranklab/io/readers.py` — functions to call.
- `src/ranklab/io/errors.py` — exception to catch.

**Status:** [x] done
