# DevPilot AI — Product Requirements Document

## 1. Product Overview

DevPilot AI is an AI-powered coding agent that analyzes an existing code repository, identifies a user-described software issue, proposes a code patch, validates the patch, executes permitted tests in an isolated environment, and presents evidence-backed results.

The product prioritizes safe code changes, reproducible testing, and transparent reporting.

## 2. Problem Statement

Developers spend time understanding unfamiliar repositories, locating bugs, creating fixes, and checking whether those fixes work. AI-generated code may appear correct while containing errors, breaking existing behavior, or claiming tests passed without actually running them.

DevPilot AI aims to connect code analysis, patch generation, controlled execution, and test evidence in one workflow.

## 3. Target Users

- Developers debugging existing projects.
- Students learning from real codebases.
- Small development teams reviewing AI-generated fixes.
- Hackathon judges evaluating practical agentic engineering.

## 4. Core User Journey

1. The user submits a supported GitHub repository URL or ZIP archive and describes a coding task.
2. DevPilot AI validates the input and inventories the repository.
3. The agent selects relevant files and analyzes the issue.
4. The agent produces a concise repair plan.
5. The agent generates a proposed patch.
6. The user reviews and approves or rejects the patch.
7. The system validates the patch and runs permitted tests in an isolated execution environment.
8. If tests fail, the agent may attempt a bounded repair.
9. The system displays the final patch, actual test results, execution logs, and remaining limitations.

## 5. MVP Features

### P0 — Required

- Submit a coding task with a repository and issue description.
- Accept public GitHub repositories or ZIP uploads, subject to input limits.
- Safely inventory files and identify relevant source files.
- Analyze repository context using an eligible NVIDIA open model through Nebius Token Factory.
- Generate a structured repair plan.
- Generate a reviewable unified diff.
- Validate patch paths and reject unsafe changes.
- Require explicit approval before applying a proposed patch or executing project tests.
- Execute permitted tests through the approved sandbox integration.
- Capture actual command, exit code, output, and timeout status.
- Display evidence-backed results without fabricating successful tests.
- Provide a bounded repair loop with a maximum of three attempts.
- Include automated tests, setup documentation, and a working demonstration.

### P1 — Add if time permits

- Live task progress.
- Clear patch preview and changed-file summary.
- Example repositories for repeatable demonstrations.
- Downloadable patch and execution report.
- Improved error handling and task history.

### Out of Scope for the MVP

- Autonomous production deployments.
- Unrestricted shell or operating-system access.
- Automatic commits or pushes to user repositories.
- Multi-agent orchestration.
- Support for every programming language and build system.
- Guaranteed resolution of every issue.

## 6. Safety and Trust Requirements

- Treat repository contents and issue descriptions as untrusted input.
- Never expose API keys or environment secrets to model prompts or test commands.
- Reject path traversal and unsafe archive entries.
- Never execute repository code on the main application process.
- Require approval before patch application and test execution.
- Enforce sandbox time and resource limits where supported.
- Bound model calls, repair attempts, and task execution time.
- Distinguish passed, failed, timed-out, skipped, and not-run tests.
- Never report a test as passed unless its execution result confirms success.
- Preserve the original repository and make proposed changes reviewable.

## 7. Technical Direction

- Frontend: Next.js and TypeScript.
- Backend: Python and FastAPI.
- Validation: Pydantic.
- Persistence: Neon-hosted PostgreSQL, accessed through SQLAlchemy 2.x with Alembic migrations.
- Model integration: Nebius Token Factory with a verified, eligible NVIDIA open model.
- Execution: Nebius Token Factory Sandbox if access and compatibility are confirmed.
- Development tests: pytest and mocked model responses.
- Version control: Git and GitHub.

The execution layer must use an adapter so sandbox integration can be tested independently. Local development execution is not considered proof that the required hackathon sandbox integration works.

## 8. Success Criteria

- A user can submit a supported repository and coding task.
- The agent produces a reviewable plan and patch.
- Unsafe paths and invalid patches are rejected.
- User approval is enforced at the required workflow stages.
- Test outcomes are based on real execution evidence.
- Failure and timeout scenarios are handled clearly.
- A repeatable demo demonstrates the full supported workflow.
- The public repository includes setup instructions, an open-source license, tests, and a short demo video.

## 9. Constraints and Assumptions

- The target hackathon deadline is October 30, 2026.
- Development must remain practical on a Windows laptop.
- Paid coding assistants and paid infrastructure are not assumed to be available.
- Nebius credentials, model availability, sandbox access, quotas, and applicable hackathon requirements must be verified before relying on them.
- Any unavailable integration must be reported honestly; mocks alone do not establish production integration readiness.

## 10. Definition of Done

The MVP is complete when the core workflow works end to end on a controlled example repository, critical security tests pass, model and sandbox integrations have been verified, and the demo accurately represents the implemented capabilities.