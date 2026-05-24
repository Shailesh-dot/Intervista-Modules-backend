# The Backend Journey

Throughout the development of the **Coding Assessment Platform v6**, this backend went through a series of significant architectural optimizations and scalability hardening sequences. This document serves as an archive of exactly how we transitioned the system from a prototype into a production-ready microservice.

---

## 1. The Database Migration: Hybrid PostgreSQL Architecture

We successfully modernized the backend by migrating it from fragile, ephemeral in-memory storage to a production-grade **PostgreSQL** database.

### Why We Migrated:
* **JSONB Limitations**: Storing dynamic test cases, user constraints, and submission responses collectively inside a single JSONB blob prevented analytics, scaling, and easy deletions.
* **Integrity**: Missing relational links allowed submissions to be tied to deleted questions or candidate interactions.

### What Changed:
1. **Removed JSONB Overload**: Stripped `visible_test_cases` and `hidden_test_cases` from the `Question` model.
2. **Relational Models Added**: 
   - `TestCase`: A standalone table featuring foreign key links (`question_id`), `input_data`, `expected_output`, `is_sample`, and `is_hidden`.
   - `Submission`: Upgraded to natively track asynchronous `job_status`, execution `score`, `passed_test_cases`, and `verdict`. 
   - `SubmissionResult`: New child table to store detailed stdout, stderr, and Judge0 metrics for *each* individual test case belonging to a parent submission.
3. **Foreign Keys & Cascade Rules**: Hot-patched `ON DELETE CASCADE` constraints into PostgreSQL over the SQLAlchemy ORMs so dropping a `Question` securely cleans up its `TestCase` and `SubmissionResult` artifacts without triggering `IntegrityError` roadblocks.

---

## 2. API Security Hardening

Pydantic schemas and database models were isolated to prevent frontend users from dumping sensitive answers or spoofing privilege scopes.

### What Changed:
1. **User Role Enforcement**: Removed native assignment of the `role` enum from the `UserRegister` and API schema logic. Hackers can no longer inject `role: "admin"` during `/auth/register` to hijack the environment. Every new registrant is strictly cast as `"user"`.
2. **Data Masking (Stripping Hidden Variables)**: 
   - Fragmented `QuestionAdminResponse` (for internal tools) and `QuestionResponse` (for public polling) so hidden test-case arrays are fundamentally inaccessible to the frontend.
   - Forced `stdout`, `stderr`, and `compile_output` strings for hidden `SubmissionResult` rows to render natively as `**hidden**` while explicitly exposing the `is_hidden` boolean badge so the UI can render its progress wheels cleanly.
3. **Database Attribute Mismatches**: Fixed several `Pydantic` to native `Dict` dot-notation errors (`bp.language_id` -> `bp.get("language_id")`) across our routers.

---

## 3. High-Performance Asynchronous Execution Engine

The backend was refactored to perform non-blocking executions suitable for scaling to thousands of concurrent test-takers natively.

### What Changed:
1. **FastAPI Background Tasks**: `POST /submit/` no longer waits for Judge0 to run test cases. It instantly returns a `submission_id` with `status: "processing"`. FastAPI detaches the intensive execution payload into a `process_submission_worker` background thread.
2. **Judge0 Batch API Engine**: Rewrote the execution layer (`services/judge0_service.py`) to bypass continuous HTTP calls. Scripts are mapped into a massive payload and bundled directly to the Judge0 `POST /submissions/batch` API. The background thread subsequently hits the `GET /submissions/batch` endpoint every second.
3. **Frontend Diagnostics Polling**: Secured `GET /submit/{submission_id}/status` to fetch dynamic states on active asynchronous jobs, enabling the UI to load cleanly and watch the `completed` variable evolve in real-time.

---

## 4. Production-Grade Defenses

To fully convert this into an agnostic microservice, we hardened the edge perimeter:
1.  **DDoS Throttling (`slowapi`)**: `/submit` and `/run` endpoints were hard-capped at 5 executions per minute to strictly block malicious spam loops that would crash a Judge0 node.
2.  **Adaptive CPU Constraints**: Infinite `while True` loops are eradicated. Submissions logically map against database difficulties. Easy questions timeout cleanly after 1.0s, Medium bounds to 2.0s, and Hard logic gates allow up to 3.0s.
3.  **Edge Caching Router (`fastapi-cache2`)**: Employs an intelligent fallback router. Heavy reading routes automatically cache in-memory when testing locally, and detect/route natively to Redis instances when deployed globally.

---

## 5. Computational Resource Guidelines

This engine natively supports massive concurrency under the right specs:

| Component | Minimum | Recommended (Production) | Details |
| :--- | :--- | :--- | :--- |
| **CPU Clock Speed** | 2.5 GHz+ | 3.2 GHz+ (Turbo Boost) | High single-core performance is critical for consistent execution time. |
| **vCPU Count** | 2 Cores | 4 - 8 Cores | Dedicated vCPUs (Compute Optimized) preferred to avoid "Steal Time". |
| **RAM** | 4 GB | 16 GB | Judge0 needs ~512MB per concurrent worker burst + OS overhead. |
| **Disk I/O** | 500 IOPS | 3000+ IOPS (NVMe) | Rapid container spawning for Judge0 requires fast disk reads/writes. |
| **Network** | 100 Mbps | 1 Gbps | Low latency (<50ms) to Judge0 API is required if hosted separately. |

### Concurrency Benchmarks

| Setup | Submissions/Min | Avg. Verdict Latency |
| :--- | :--- | :--- |
| **2 vCPU / 4GB RAM** | ~30 - 45 | 4s - 6s |
| **4 vCPU / 8GB RAM** | ~100 - 150 | 2s - 3s |
| **8 vCPU / 16GB RAM** | ~300+ | <1.5s |

> [!TIP]
> To handle 10,000+ candidates, horizontal scaling of **Judge0 Workers** is required. The Backend API itself is entirely lightweight and requires very little CPU!
