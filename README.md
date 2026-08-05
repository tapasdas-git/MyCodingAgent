MyCodeAgent 

MyCodeAgent is an autonomous, agentic task-execution engine and CLI tool designed to automate software feature development, adversarial code reviews, changelog updates, and GitHub Pull Request delivery.

By combining high-reasoning AI models (for code creation and automated security/guideline reviews) with deterministic Python scripting (for Git lifecycle management and changelog generation), MyCodeAgent delivers a controlled task-resolution workflow with minimal token usage and high reliability.

***
💡 Key Features & Architecture

```text
                               ┌────────────────────────────────────────┐
                               │ 1. TASK PICKUP                         │
                               │    Parses 'ready' tasks from TODO.md   │
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  v
                               ┌────────────────────────────────────────┐
                               │ 2. IMPLEMENT TASK (AI Agent)           │
                               │    Isolated workspace creation         │
                               │    Generates code, dependencies & tests│
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  v
                               ┌────────────────────────────────────────┐
                               │ 3. ADVERSARIAL CODE REVIEW (AI Agent)   │
                               │    Inspects diffs vs. guidelines       │
                               │    Verifies 100% test suite pass rate  │
                               │    Scans for security & key leaks      │
                               └─────────┬────────────────────┬─────────┘
                                         │                    │
                                [CHANGES_REQUESTED]        [APPROVED]
                                         │                    │
                                         v                    v
                                  ┌─────────────┐   ┌───────────────────┐
                                  │ HALT PROCESS│   │ 4. UPDATE CHANGELOG│
                                  └─────────────┘   │    Deterministic  │
                                                    │    Python Script  │
                                                    └─────────┬─────────┘
                                                              │
                                                              v
                                                    ┌───────────────────┐
                                                    │ 5. CREATE PULL REQ│
                                                    │    Pushes branch  │
                                                    │    Opens GitHub PR│
                                                    └───────────────────┘

Automated Task Ingestion: Scans TODO.md for structured tasks marked as ready.

Isolated Task Workspaces: Generates feature implementations and unit tests within scoped task directories to avoid cross-task pollution.

Adversarial Code Review: Evaluates pull requests against customized guidelines (codeReviewGuideline.md), test suite execution results, and security scans before approving.

Deterministic Delivery Pipeline: Executes branch creation, changelog tracking, and GitHub PR creation using deterministic Python helpers (saving tokens and eliminating non-deterministic Git errors).

🛠️ Technology Stack & Dependencies
Language & Runtime: Python 3.8+ (Recommended Python 3.11+)

Agent Framework & Runner: Omnigent Core Engine (omnigent)

Version Control & Integration: Git, GitHub CLI (gh)

Testing Frameworks: pytest, Python unittest

Configuration Formats: YAML (.yaml), TOML (.toml), Markdown (.md)

***
📋 Prerequisites

🔧 Installing the Omnigent Core Engine

pip install omnigent

omnigent setup


Before setting up MyCodeAgent in a fresh environment, ensure the following dependencies and tools are installed and configured:

Python 3.8+
Check installation:
python3 --version

Git
Installed and configured with your target repository:
git --version

GitHub CLI (gh)
Required for automated Pull Request creation during the delivery stage.
Authenticate your active session:
gh auth login
gh auth status

Omnigent Binary / Core Runner
Ensure omnigent is installed and accessible in your environment's $PATH:
omnigent --version

***
📁 Project Directory Structure

For MyCodeAgent to locate configuration files and source code correctly, ensure your repository root matches this layout. The CLI loads `coding_agent.yaml` as its active Codex/Omnigent workflow definition; `omnigent_bugfix_workflow.yaml` is not used by the current CLI.

```text
MyCodeAgent/                        # Project Root Directory
├── TODO.md                        # Task queue file containing structured tasks
├── CHANGELOG.md                   # Automated release changelog
├── codeReviewGuideline.md         # Enterprise review & security standards
├── pyproject.toml                 # Package configuration & entry points
├── workflow_runtime.toml          # Model, harness, and timeout runtime settings
├── coding_agent.yaml              # Active Codex/Omnigent workflow stages
├── git_approval.toml             # Approved Git identity & remote repository rules
├── README.md                      # Documentation
├── scripts/
│   └── workflow_helpers.py        # Deterministic Python scripts (Changelog & PR)
└── src/
    └── mycodeagent/
        ├── __init__.py        # Package initialization
        └── __main__.py        # CLI entry point logic


🚀 Quickstart & Installation
Clone the Repository

git clone https://github.com/tapasdas-git/MyCodeAgent.git

cd MyCodeAgent

Create and Activate Virtual Environment

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install MyCodeAgent in Editable Mode

pip install -e .

📖 Usage Guide

### Execute the automated workflow

To pick up the first task marked ready in TODO.md and execute the full pipeline (Implement $\rightarrow$ Review $\rightarrow$ Changelog $\rightarrow$ GitHub PR):

Process task from default TODO.md
mycodeagent submit

Process task from a custom TODO file path
mycodeagent submit --todo /path/to/custom_todo.md

Granular Stage Execution & Troubleshooting
If a task requires step-by-step debugging, individual workflow stages can be executed independently:

Stage 1: Run code implementation for a specific task ID
mycodeagent run TASK-100

Stage 2: Run verification checks & test suites
mycodeagent verify TASK-100

Stage 3: Run adversarial code review against guidelines
mycodeagent review TASK-100

Stage 4: Commit changes, push branch, and create GitHub PR
mycodeagent deliver TASK-100

Direct Script Execution (Human-in-the-Loop Fallback)

To execute changelog updates or GitHub PR generation directly via the deterministic helper scripts:

Append task entry to CHANGELOG.md
python3 scripts/workflow_helpers.py changelog --task-id "TASK-100"

Create feature branch, commit, push, and open Pull Request on GitHub
python3 scripts/workflow_helpers.py pr --task-id "TASK-100" --task-dir "flight_booking"

📝 Defining Tasks in TODO.md

### Coding-agent implementation contract

`mycodeagent` invokes Codex through `coding_agent.yaml`. The task description is the source of truth; the coding agent must translate its architecture and acceptance criteria into implementation, tests, and a reviewable result. For every task, the implementation stage must:

- inspect the referenced repository files before choosing dependencies or APIs;
- keep changes inside the task's stated workspace boundary;
- map every acceptance criterion to at least one test;
- inject external integrations behind interfaces and use fakes/mocks in tests; and
- report the task ID, changed files, acceptance-test evidence, and any unsupported requirement rather than silently substituting an unrelated design.

For an AI-agent task, naming an LLM provider is an implementation requirement. For example, a Groq ReAct feature must include a dynamically configured Groq adapter, validated tool inputs and outputs, and an explicit thought/action/observation loop with a bounded iteration count. A key lookup alone is not an LLM integration. Business-critical checks—such as price, inventory, policy, and booking confirmation—must remain deterministic code and must not rely on model output.

The Omnigent workflow is the outer development pipeline (implement, review, changelog, delivery). It is distinct from any multi-agent runtime that the task asks the coding agent to build.

TASK-100 | ready | high | Build Flight Booking Agent in flight_booking

  Description:
  Implement a flight search and booking module that processes natural language requests.

  Architecture & Boundaries:
Framework: Python 3.11+, Pydantic v2
Isolated Boundary: Source code lives in flight_booking/Coding/, tests in flight_booking/test/
Mocks: Mock external airline APIs for unit tests.

  Acceptance:
Isolated directory flight_booking/ created.
Dependencies defined in flight_booking/Coding/requirements.txt.
All unit tests pass with 100% pass rate.
