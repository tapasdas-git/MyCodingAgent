python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

cd MyOmnigent

pip install -e .

Step-by-Step Enterprise Implementation Guide

git checkout main
git pull origin main

- [ ] TASK-101 | ready | high | Implement authentication module in auth_service

Exexute

# Uses default TODO.md in the root directory
myomnigent submit

# Or specify a custom TODO file path
myomnigent submit --todo /path/to/custom_todo.md

Command Reference & Troubleshooting

# Execute only the task implementation stage
myomnigent run TASK-101

# Execute verification checks & unit tests
myomnigent verify TASK-101

# Run code review guidelines check against implementation diff
myomnigent review TASK-101

# Execute Git commit, push, and Pull Request creation
myomnigent deliver TASK-101

Direct Script Execution (HITL Fallback)

# Append changelog entry deterministically
python3 scripts/workflow_helpers.py changelog --task-id "TASK-101"

# Create feature branch, push, and open GitHub PR
python3 scripts/workflow_helpers.py pr --task-id "TASK-101" --task-dir "auth_service"