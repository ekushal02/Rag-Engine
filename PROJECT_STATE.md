# PROJECT_STATE.md

Internal ground-truth snapshot. Not for external/resume use — that's what `README.md` is for.
This file records what was actually observed in the repo and via live runs on the date below.
Regenerate/update it rather than trusting it blindly once the code has moved on.

---

## 1. Timestamp and git state

- Snapshot taken: **2026-07-21**
- Branch: `main`
- Last commit: `36613af` "Assets added" (2026-07-06)
- **Everything below reflects uncommitted working-tree changes** — the fixes described in this
  file (per-request keys, ChromaDB path anchoring, `.gitignore` fix, new eval runs, `README.md`
  itself) are not yet committed.

```
 M .env.example
 M .gitignore
 M README.md
 M backend/api/routes/upload.py
 M backend/ingestion/embedder.py
 M backend/ingestion/pipeline.py
 M backend/ingestion/store.py
 M backend/main.py
 D  chroma_db/65f2d5ca-216b-4d15-9d2d-696990ea7489/{data_level0.bin,header.bin,index_metadata.pickle,length.bin,link_lists.bin}
 D  chroma_db/chroma.sqlite3
 M deploy/deploy.sh
 M docker-compose.prod.yml
 M docker-compose.yml
 M eval/parameter_sweep.py
 M eval/results/summary_scores.csv
 M eval/run_eval.py
 M scripts/test_chunker.py
 M scripts/test_extractor.py
 M scripts/test_ingestion.py
?? eval/results/run_baseline_512_64_k5_20260721_194356.csv
?? eval/results/run_cs512_ov32_k3_20260721_195223.csv
?? eval/results/run_final_winner_512_32_k3_20260721_201123.csv
?? eval/results/sweep_run.log
?? eval_data/nist_sp800-145.pdf
```

The old root-level `chroma_db/` binaries are staged for deletion but **not yet committed** — they
still exist in `HEAD` (commit `36613af`). They will actually leave git history only once this is
committed (and even then, old history still has them unless squashed/filtered).

---

## 2. Full architecture inventory

### `backend/`

| File | What it does |
|---|---|
| `main.py` | Convenience entrypoint (`python backend/main.py`) — chdirs into `backend/`, adds it to `sys.path`, then runs the same `api.main:app` via uvicorn with `--reload`. |
| `api/main.py` | FastAPI app factory. Loads `.env`, raises `RuntimeError` at import time if `OPENAI_API_KEY`/`GROQ_API_KEY` are unset, wires up CORS (only `localhost:3000` allowed), mounts `upload`, `query`, `documents` routers, defines `/health` and `/`. |
| `api/models.py` | All Pydantic request/response models: `UploadResponse`, `StatusResponse`, `QueryRequest` (**`k` defaults to 5**), `QueryResponse`, `CitationOut`, `DocumentInfo`, `DocumentListResponse`, `DeleteResponse`. |
| `api/dependencies.py` | In-memory (non-persistent) ingestion-status dict; `resolve_openai_key`/`resolve_groq_key` FastAPI dependencies — header value wins, falls back to server env var, 401s if neither present. |
| `api/routes/upload.py` | `POST /upload` — saves the PDF, runs `ingest_document()` in a thread-pool executor (blocking work off the event loop), returns `UploadResponse`. Does **not** pass `chunk_size`/`chunk_overlap`, so it always uses `ingest_document`'s defaults. Also `GET /status/{doc_id}`. |
| `api/routes/query.py` | `POST /query` and `GET /query/stream` — calls `route_and_retrieve()`, optional `doc_id` post-filter (re-retrieves if the filter empties the result), then `generate()`/`generate_stream()`. Both endpoints compute `complex_k=max(k*3, 15)`. |
| `api/routes/documents.py` | `GET /documents` (lists distinct sources + live chunk counts from Chroma) and `DELETE /documents/{doc_id}`. |
| `api/routes/config.py` | `GET /config/check` — cheap presence/prefix check (`sk-`, `gsk_`) on the two header keys, no live API call. Not mentioned in README. |
| `ingestion/extractor.py` | PyMuPDF (`fitz`) text extraction per page; drops pages with <50 chars. |
| `ingestion/chunker.py` | `RecursiveCharacterTextSplitter` (langchain) chunking, default `chunk_size=1024, chunk_overlap=32`; drops fragments <30 chars and exact-prefix near-duplicates of the previous chunk. |
| `ingestion/embedder.py` | Batches chunks (100/request) through OpenAI `text-embedding-3-small`; builds a **fresh `OpenAI` client per call** from the passed `openai_key` (or env fallback); retries on `RateLimitError` with exponential backoff. |
| `ingestion/pipeline.py` | `ingest_document()` — orchestrates delete-existing → extract → chunk → embed → store → log. Default `chunk_size=1024, chunk_overlap=32`. |
| `ingestion/store.py` | ChromaDB wrapper. `CHROMA_PATH` anchored via `Path(__file__).resolve().parent / "chroma_db"` (overridable by env var). `store_chunks`, `delete_document`, `list_documents`. |
| `ingestion/logger.py` | Appends JSON records to `./ingestion_log.json` (relative to CWD, not anchored like `store.py`). |
| `retrieval/retriever.py` | `embed_query()` + `retrieve()` — direct cosine-similarity ChromaDB search, default `k=5`. |
| `retrieval/hyde.py` | `generate_hypothetical_answer()` (Groq, temp 0.3) then embeds that and queries Chroma; default `k=15`. |
| `retrieval/reranker.py` | Lazy-loaded `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` (module-level singleton `_model`), `rerank()` default `top_n=5`. |
| `retrieval/router.py` | `classify_query()` (Groq LLaMA 3.3 70B, temp 0, 5 max tokens, defaults to "simple" on any unexpected output) and `route_and_retrieve()` (defaults `simple_k=8, complex_k=24, rerank_top_n=5` — these defaults are only used if a caller doesn't override them; both API routes and `run_eval.py` always override `simple_k`/`complex_k` explicitly). |
| `generation/generator.py` | `generate()` / `generate_stream()` — Groq `llama-3.3-70b-versatile`, temp 0.1, max_tokens 1000; `parse_citations()` regex-matches `[C\d+]` and resolves back to the chunk list by position. |
| `generation/prompts.py` | System prompt (citation rules, "don't invent numbers", refusal string) and `build_prompt()` (labels chunks `[C1]`, `[C2]`, ...). |
| `generation/schema.py` | Plain dataclasses `Citation` and `RAGResponse` (not Pydantic) — the internal pipeline contract; converted to Pydantic `CitationOut`/`QueryResponse` at the API boundary. |

### `frontend/`

| File | What it does |
|---|---|
| `app/page.tsx` | Redirects `/` → `/chat`. |
| `app/layout.tsx` | Root layout, Inter font, page metadata. |
| `app/chat/page.tsx` | Main chat UI (404 lines) — orchestrates key-gate, upload zone, document list, streaming query, answer + sources panel. |
| `components/KeySetup.tsx` | Collects OpenAI/Groq keys, writes them via `setStoredKeys()` (sessionStorage). |
| `components/AnswerDisplay.tsx` | Renders the streamed answer text with copy-to-clipboard. |
| `components/SourcesPanel.tsx` | Renders citation cards, scrolls to/highlights the citation matching a hovered `[C_]` badge. |
| `components/DocumentList.tsx` | Lists ingested docs, delete button. |
| `components/UploadZone.tsx` | Drag/drop or click-to-upload PDF, calls `uploadDocument()`. |
| `lib/api.ts` | Fetch wrapper. `authHeaders()` attaches `X-OpenAI-Key`/`X-Groq-Key` from sessionStorage to **every** call (`upload`, `status`, `documents` list/delete, `query/stream`). Manually parses the SSE stream (splits on `\n\n`, looks for `event:`/`data:` lines). |
| `types/index.ts` | TS interfaces mirroring the Pydantic models. |

### `eval/`

| File | What it does |
|---|---|
| `run_eval.py` | `run_pipeline()` (calls `route_and_retrieve` with `complex_k=max(k*3,15)`), `build_ragas_dataset()`, `score_dataset()` (RAGAS, judge = GPT-4.1-mini per file comments elsewhere), `save_results()` (appends to `summary_scores.csv`, writes a per-run `run_*.csv`). `__main__` block runs one hardcoded config: `chunk_size=512, overlap=32, k=3`, label `final_winner_512_32_k3`. |
| `parameter_sweep.py` | Re-ingests all 3 docs per chunk/overlap combo, sweeps `CHUNK_SIZES=[512,1024]` × `OVERLAPS=[32,64]` × `K_VALUES=[3,5,8]` = **12 configs** (the file's own comment says "3 chunk sizes ... = 18 configurations", which is stale/wrong — only 2 chunk sizes are actually in the list). 30s cooldown + 2s pause between runs for the Groq rate limit. Restores the winning config's ingestion at the end. |
| `results/summary_scores.csv` | Append-only run log, see §4. |

### `scripts/`

All are standalone manual-run smoke scripts (`sys.path.append(".")`, run from repo root, not pytest):
`test_extractor.py`, `test_chunker.py`, `test_embedder.py`, `test_ingestion.py`, `test_retrieval.py`,
`test_router.py`, `test_generation.py`, `test_streaming.py` — each exercises one pipeline stage in
isolation, printing output for manual inspection. All PDF-referencing scripts now point at
`eval_data/{sample,sample2,nist_sp800-145}.pdf`; no remaining references to a `Transcripts.pdf` file
anywhere in the repo.

### `deploy/`

| File | What it does |
|---|---|
| `ec2_setup.sh` | One-time EC2 bootstrap: installs Docker + AWS CLI, adds user to the `docker` group. |
| `deploy.sh` | Requires `EC2_PUBLIC_IP` env var (hard `: "${EC2_PUBLIC_IP:?...}"` guard), logs into ECR, builds/tags/pushes backend and frontend images (frontend build bakes in `NEXT_PUBLIC_API_URL` from `EC2_PUBLIC_IP`). Does not itself SSH or run anything on the EC2 box — last line just prints the follow-up command to run manually. |

---

## 3. Config defaults as they actually exist in code

| Setting | Code default | File:line | Matches "recommended" (512/32/3)? |
|---|---|---|---|
| `chunk_size` | **1024** | [backend/ingestion/pipeline.py:14](backend/ingestion/pipeline.py#L14), [backend/ingestion/chunker.py:9](backend/ingestion/chunker.py#L9) | ❌ No — recommended is 512 |
| `chunk_overlap` | 32 | [backend/ingestion/pipeline.py:15](backend/ingestion/pipeline.py#L15) | ✅ Yes |
| `QueryRequest.k` (`/query`) | **5** | [backend/api/models.py:59](backend/api/models.py#L59) | ❌ No — recommended is 3 |
| `k` query param (`/query/stream`) | **5** | [backend/api/routes/query.py:82](backend/api/routes/query.py#L82) | ❌ No — recommended is 3 |
| `complex_k` formula | `max(k * 3, 15)` | [backend/api/routes/query.py:50,91](backend/api/routes/query.py#L50) | ✅ Matches README's `max(3×k, 15)` |
| `rerank_top_n` | 5 | [backend/retrieval/router.py:65](backend/retrieval/router.py#L65) | ✅ Matches README's "top 5" |
| `retrieve()` direct-path `k` | 5 | [backend/retrieval/retriever.py:15](backend/retrieval/retriever.py#L15) | — (overridden by callers) |
| `hyde_retrieve()` `k` | 15 | [backend/retrieval/hyde.py:32](backend/retrieval/hyde.py#L32) | — (overridden by callers) |
| `route_and_retrieve()` `simple_k`/`complex_k` | 8 / 24 | [backend/retrieval/router.py:63-64](backend/retrieval/router.py#L63) | — (both API routes always override these) |

**Real gap:** `POST /upload` ([backend/api/routes/upload.py:52](backend/api/routes/upload.py#L52)) calls
`ingest_document(save_path, openai_key=openai_key)` with no `chunk_size`/`chunk_overlap` args, so
**every document uploaded through the running API is chunked at 1024/32, not the tested-and-recommended
512/32.** The 512/32/3 config only gets applied when `eval/run_eval.py` or `eval/parameter_sweep.py`
is run directly (which call `ingest_document` with explicit params) — never through the live app.
Similarly, `QueryRequest.k` defaults to 5 (the *untuned baseline* k), not 3 — a client has to pass
`"k": 3` explicitly to get the tested configuration. Confirmed live: uploading `sample.pdf` through a
running server just now produced 14 chunks, consistent with the 1024-char default, not the 512-char
recommended size.

---

## 4. Full evaluation history (`eval/results/summary_scores.csv`)

20 rows total. Two distinct corpora, inferred from run timestamps and file mtimes (not from git
history — this repo's history is squashed to a few commits, so this is inference, not forensic
proof):

- **Old corpus (2026-04-09 / 2026-04-16 runs, 16 rows):** almost certainly `sample.pdf` + `sample2.pdf`
  + a third document that the now-removed `Transcripts.pdf` references (since scrubbed from all
  scripts) point to. **Do not compare these numbers to the July rows** — different corpus, different
  index "noise," not an apples-to-apples baseline.
- **Current corpus (2026-07-21 runs, 3 rows):** `sample.pdf` + `sample2.pdf` + `nist_sp800-145.pdf`
  (file dated today). These are the only three rows the README's numbers are drawn from.

| timestamp | label | chunk_size | overlap | k | faithfulness | answer_relevancy | context_precision | context_recall | corpus |
|---|---|---|---|---|---|---|---|---|---|
| 20260409_035634 | baseline_512_64_k5 | 512 | 64 | 5 | 0 | 0 | 0 | 0 | old (failed/empty run — all zeros, likely a crashed or misconfigured run, superseded same day) |
| 20260416_003951 | baseline_512_64_k5 | 512 | 64 | 5 | 0.7756 | 0.684 | 0.5929 | 0.7733 | old |
| 20260416_004421 | cs256_ov32_k3 | 256 | 32 | 3 | 0.6145 | 0.5587 | 0.4747 | 0.5667 | old |
| 20260416_004703 | cs256_ov32_k5 | 256 | 32 | 5 | 0.6567 | 0.5835 | 0.4847 | 0.6067 | old |
| 20260416_010206 | cs512_ov32_k3 | 512 | 32 | 3 | 0.7717 | 0.6997 | 0.6828 | 0.8267 | old |
| 20260416_011000 | cs512_ov32_k5 | 512 | 32 | 5 | 0.7356 | 0.7075 | 0.6587 | 0.76 | old |
| 20260416_011649 | cs512_ov32_k8 | 512 | 32 | 8 | 0.7467 | 0.7017 | 0.6868 | 0.8 | old |
| 20260416_012242 | cs512_ov64_k3 | 512 | 64 | 3 | 0.7956 | 0.6811 | 0.5996 | 0.7867 | old |
| 20260416_012908 | cs512_ov64_k5 | 512 | 64 | 5 | 0.78 | 0.681 | 0.5984 | 0.7867 | old |
| 20260416_013553 | cs512_ov64_k8 | 512 | 64 | 8 | 0.76 | 0.7235 | 0.6276 | 0.7733 | old |
| 20260416_014153 | cs1024_ov32_k3 | 1024 | 32 | 3 | 0.8338 | 0.7075 | 0.6396 | 0.72 | old |
| 20260416_014818 | cs1024_ov32_k5 | 1024 | 32 | 5 | 0.8278 | 0.7361 | 0.644 | 0.8 | old |
| 20260416_015505 | cs1024_ov32_k8 | 1024 | 32 | 8 | 0.8316 | 0.7731 | 0.6551 | 0.88 | old |
| 20260416_020124 | cs1024_ov64_k3 | 1024 | 64 | 3 | 0.7852 | 0.7101 | 0.6591 | 0.7267 | old |
| 20260416_020852 | cs1024_ov64_k5 | 1024 | 64 | 5 | 0.859 | 0.7552 | 0.6722 | 0.8067 | old |
| 20260416_021621 | cs1024_ov64_k8 | 1024 | 64 | 8 | 0.8371 | 0.7614 | 0.6891 | 0.8467 | old |
| **20260721_194356** | **baseline_512_64_k5** | 512 | 64 | 5 | 0.8133 | 0.3895 | 0.3147 | 0.48 | **current — README baseline row** |
| **20260721_195223** | **cs512_ov32_k3** | 512 | 32 | 3 | 0.9833 | 0.5691 | 0.6927 | 0.9 | **current — README tuned row #1** |
| **20260721_201123** | **final_winner_512_32_k3** | 512 | 32 | 3 | 0.9564 | 0.5585 | 0.68 | 0.86 | **current — README tuned row #2** |

The 12 old sweep rows (256–1024 chunk size × 32/64 overlap × 3/5/8 k) are a leftover from an earlier,
larger grid search against the old corpus — not reproduced against the current corpus. If a "real"
exhaustive sweep number is ever wanted, it needs to be re-run against `sample.pdf` + `sample2.pdf` +
`nist_sp800-145.pdf`, since old-corpus scores aren't valid evidence for the current index.

---

## 5. Verified vs. assumed

| Verified (actually run/observed) | Assumed (true by reading code only) |
|---|---|
| `cd backend && uvicorn api.main:app --port 8000` → `curl localhost:8000/health` returned `{"status":"ok"}` HTTP 200 (ran live, 2026-07-21) | `/query` and `/query/stream` end-to-end (not exercised live in this pass — would burn Groq daily tokens; verified only by reading `query.py`, `router.py`, `generator.py`, and the response models) |
| `python backend/main.py` (from repo root) → same `/health` check, HTTP 200 (ran live, 2026-07-21) | Frontend UI (`npm run dev`, actual browser interaction) — not started or clicked through in this pass |
| `POST /upload` with `eval_data/sample.pdf` → `{"doc_id":"sample.pdf","chunk_count":14,"pages":5,"status":"done"}`, HTTP 200 (ran live) — confirms field names, and confirms the 1024-char default is what's actually applied (14 chunks for a 5-page syllabus is consistent with 1024, not 512) | Docker Compose build/run (`docker compose up --build`) — Dockerfiles read and confirmed multi-stage, but the build itself was not executed in this pass |
| `GET /documents` → `{"documents":[...3 docs...],"total":3}`, HTTP 200 (ran live) — field names match `DocumentInfo`/`DocumentListResponse` exactly, no phantom fields | AWS EC2/ECR deployment scripts — read for correctness (guard present, commands look right) but not executed against real AWS infra |
| `eval/results/summary_scores.csv` numbers — read directly and recomputed averages by hand from the raw floats | Groq 100K-tokens/day free-tier figure — cross-checked against Groq's public rate-limits doc (`console.groq.com/docs/rate-limits`) on 2026-07-21, which still lists 100K TPD for `llama-3.3-70b-versatile`; this is a live-docs check, not a live 429 reproduction |
| `git status`, `git log`, `git ls-files`, `.gitignore` diff — read directly | Old-corpus vs. new-corpus split in §4 — inferred from timestamps/mtimes, not from git blame/history (history is squashed) |
| `eval_data/test_set.json` — all 25 entries counted directly (11 `sample.pdf` / 12 `sample2.pdf` / 2 `none`) | — |
| No `Transcripts.pdf` references anywhere in the repo — confirmed via repo-wide grep | — |

---

## 6. Open items

From the README's "Known Limitations" section (still accurate):
- Parameter search is two configs, not an exhaustive grid. **Blocks nothing** — README already discloses this honestly.
- RAGAS judge run-to-run variance (~0.02–0.03/metric). **Blocks nothing** — disclosed.
- Server still requires its own `.env` keys to boot; not a zero-server-credential deployment. **Blocks nothing** — disclosed, and confirmed still true (§3, `api/main.py`'s `RuntimeError` check).
- Groq 100K tokens/day free-tier ceiling. **Blocks nothing** — disclosed, and still accurate per live docs check.

Additional things noticed during this verification pass, not currently mentioned in the README:
- **Blocks the "512/32/3 is the config" claim as currently written:** the live app (`/upload`, `/query`) does not actually run at the recommended 512/32/3 config by default — it defaults to 1024/32 chunking and k=5 retrieval (§3). The README presents 512/32/3 as *the* current config without noting that a user has to pass `k=3` on every query and that ingestion always runs at 1024 chunk size regardless. This is a real discrepancy between "what was tested" and "what ships," not just a disclosed limitation.
- **Blocks the numbers in the Evaluation Results table as currently written:** the baseline average (0.5244) and the "~48% improvement" figure are both arithmetic errors — see the Part A report for this conversation. Correct values: baseline avg ≈ 0.4994, improvement ≈ 55%.
- **Nice-to-have:** `eval/parameter_sweep.py`'s docstring/comment says "3 chunk sizes × 2 overlaps × 3 k values = 18 configurations" but the code only sweeps 2 chunk sizes (12 configs total) — stale comment, not user-facing, low priority.
- **Nice-to-have:** `ingestion/logger.py`'s `LOG_PATH = "./ingestion_log.json"` is relative to CWD, unlike `store.py`'s `CHROMA_PATH` which is anchored to the file's own location — inconsistent, could produce a log file in an unexpected place depending on how the server is started. Not currently causing a visible bug.
- **Nice-to-have:** `/config/check` endpoint (`backend/api/routes/config.py`) exists and isn't mentioned anywhere in the README's API Endpoints section. Not wrong, just undocumented.

---

## 7. Explicit non-claims

Things that are **not** currently true — don't let these creep back in without re-verifying:

- The app does **not** currently run with zero server-side keys — `backend/api/main.py` still hard-`RuntimeError`s at startup if `OPENAI_API_KEY`/`GROQ_API_KEY` aren't set in `.env`, even though per-request headers can override them at call time.
- There is **no continuously-running AWS deployment** right now — `deploy/deploy.sh` builds and pushes images on demand; nothing is currently live on EC2 unless manually started.
- The parameter search backing the README's numbers is **two configurations run to completion against the current corpus** (`baseline_512_64_k5` and two runs of the 512/32/3 config), not an exhaustive grid — the 12-row grid in `summary_scores.csv` is against the **old, different corpus** and isn't valid supporting evidence for the current numbers.
- The live app does **not** default to the "recommended" 512/32/3 configuration — see §3. Only `eval/run_eval.py` applies it, and only when run directly.
- There is currently **no automated test suite** (pytest, CI, etc.) — `scripts/test_*.py` are manual smoke-test scripts you run and read the printed output from, not assertions that pass/fail.
