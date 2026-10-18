# DevPilot AI — System Architecture

## 1. Architecture Goals

- Keep the application modular and testable.
- Separate model reasoning from privileged application operations.
- Require human approval before applying patches and executing repository tests.
- Capture verifiable execution evidence.
- Integrate with Nebius Token Factory and an approved sandbox through replaceable adapters.
- Keep the MVP small enough to complete and demonstrate before the hackathon deadline.

## 2. High-Level Architecture

The application consists of a Next.js frontend, a FastAPI backend, an agent orchestrator, a model gateway, repository-processing services, a patch validator, an isolated execution adapter, and an evidence reporter.

The frontend communicates with the backend over HTTP. The backend orchestrates the workflow and invokes external services through defined interfaces.

The model must not directly control the host operating system or bypass application authorization.

## 3. Component Responsibilities

### Frontend

Responsibilities:
- Accept a repository URL or ZIP archive and task description.
- Display task status and the proposed repair plan.
- Present a patch for review.
- Collect explicit approval or rejection.
- Display actual test results, logs, and limitations.

Technology: Next.js and TypeScript.

### API Layer

Responsibilities:
- Validate incoming requests.
- Create and retrieve tasks.
- Enforce authorization and workflow transitions.
- Expose patch, approval, cancellation, and status operations.
- Return consistent errors.

Technology: FastAPI and Pydantic.

### Repository Ingestion Service

Responsibilities:
- Accept supported repository inputs.
- Validate archive entries and repository paths.
- Reject path traversal and unsafe file types.
- Inventory files and detect supported languages.
- Enforce upload, file-count, and file-size limits.
- Store a task-specific working copy.

Repository content must always be treated as untrusted data.

### Context Builder

Responsibilities:
- Identify files relevant to the reported issue.
- Select bounded source-code excerpts.
- Exclude secrets, generated files, and irrelevant large files where possible.
- Construct a limited model context.
- Record which files were used for analysis.

### Agent Orchestrator

Responsibilities:
- Coordinate analysis, planning, patch generation, and validation.
- Enforce allowed workflow transitions.
- Apply call, token, retry, and time limits.
- Prevent model output from directly authorizing privileged operations.
- Record task progress and errors.

The initial implementation uses an explicit state machine rather than an unrestricted autonomous loop.

### LLM Gateway

Responsibilities:
- Communicate with Nebius Token Factory.
- Use a verified NVIDIA open model available to the account.
- Validate and parse structured model output.
- Handle provider errors, timeouts, and rate limits.
- Keep credentials outside prompts and logs.

The model ID and API configuration must be environment-configurable.

### Patch Engine

Responsibilities:
- Accept proposed unified diffs.
- Validate diff structure and target paths.
- Reject paths outside the task workspace.
- Prevent modifications to protected application files.
- Produce a reviewable patch.
- Apply approved changes only within the isolated working copy.

Patch generation does not imply patch approval.

### Sandbox Adapter

Responsibilities:
- Integrate with the required, verified Nebius Token Factory Sandbox where available.
- Submit approved code and permitted test commands.
- Enforce or request execution limits supported by the sandbox.
- Return execution identifiers, exit codes, logs, and timeout information.
- Handle sandbox failures without falsely reporting success.

A local mock or development runner may support testing during development, but it must not be presented as a completed Nebius sandbox integration.

### Evidence Reporter

Responsibilities:
- Record the command actually executed.
- Record exit status, captured output, and execution duration where available.
- Distinguish passed, failed, timed-out, skipped, and not-run tests.
- Summarize the patch and unresolved issues.
- Ensure every success claim is supported by recorded evidence.

## Persistence — Neon PostgreSQL

Use Neon-hosted PostgreSQL as the primary database.

Responsibilities:
- Persist task metadata and validated state transitions.
- Store task status, repair-attempt counts, and execution summaries.
- Store structured execution evidence where appropriate.
- Keep database access separate from API routes and agent orchestration.

Implementation direction:
- Use SQLAlchemy 2.x for database access.
- Use Alembic for schema migrations.
- Read the connection string from `DATABASE_URL`.
- Keep database credentials out of source control and application logs.
- Use Neon’s recommended connection configuration for the selected deployment environment.

Do not store API keys or unnecessary private repository contents in the database.


## 4. Task State Machine

Supported states:

CREATED
→ REPOSITORY_READY
→ ANALYZING
→ PLAN_READY
→ PATCH_READY
→ AWAITING_APPROVAL
→ VALIDATING
→ TESTING
→ SUCCEEDED

Failure branches:
- Invalid input → REJECTED
- Unsafe or invalid patch → FAILED
- User rejects the patch → REJECTED
- User cancels the task → CANCELLED
- Model, sandbox, or execution error → FAILED or a clearly reported recoverable state

Bounded repair:
- A failed test may trigger REPAIRING.
- The agent may generate another proposed patch, with a maximum of three repair attempts.
- Each revised patch must pass validation and the required approval gate before execution.
- Exhausted attempts end in FAILED with evidence and a clear explanation.

Every state transition must be validated by backend code.

## 5. Request Flow

1. Receive and validate the coding task.
2. Create an isolated task workspace.
3. Ingest and inventory the repository.
4. Select relevant context.
5. Ask the model to analyze the issue.
6. Present a repair plan.
7. Generate and validate a proposed patch.
8. Ask the user to approve or reject it.
9. Submit approved changes to the configured isolated execution environment.
10. Run permitted tests and collect actual results.
11. If appropriate, perform a bounded repair cycle.
12. Generate an evidence-backed report.

## 6. Security Boundaries

- The model cannot independently approve its own patch.
- Repository code cannot execute in the main API process.
- Secrets must not be injected into untrusted test environments.
- Execution must be isolated and resource-limited.
- Network access should be disabled unless explicitly required and safely controlled.
- Archive extraction must defend against path traversal and unsafe entries.
- API endpoints must enforce task ownership and permitted state transitions.
- Logs must redact credentials and avoid unnecessary sensitive source content.
- User input and repository instructions cannot override application security policy.

## 7. Initial Technology Choices

- Frontend: Next.js, TypeScript.
- Backend: Python, FastAPI, Pydantic.
- Testing: pytest.
- Persistence: SQLite.
- Model integration: Nebius Token Factory.
- Model: a verified, eligible NVIDIA open model.
- Execution: a verified Nebius Token Factory Sandbox integration.
- Version control: Git.

No microservices, Kubernetes, vector database, or multi-agent framework is required for the MVP.

## 8. Integration Readiness

Before relying on external services, verify:

- Nebius account registration and authentication.
- API-key creation and available credits or quota.
- An eligible NVIDIA model ID and a successful inference request.
- Sandbox availability, documentation, authentication, and execution interface.
- Supported commands, isolation guarantees, resource limits, and result retrieval.

Use mocks for unit tests, but separately verify the real integrations.

## 9. Deployment Direction

Keep local development straightforward. Select the final hosting arrangement only after checking free-tier limits, backend support, secrets management, and the hackathon's requirements.

The public demo must not expose credentials or permit arbitrary users to execute unrestricted code.

## 10. Architectural Decision

The application will use a modular monolith with explicit service interfaces. This minimizes setup overhead while preserving clear boundaries between API handling, orchestration, model inference, patch validation, sandbox execution, and evidence reporting.