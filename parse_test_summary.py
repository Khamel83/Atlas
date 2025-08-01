import os
import re

SUMMARY_FILE = "test_logs/summary.txt"
NEXT_ACTIONS_FILE = "test_logs/next_actions.txt"

if not os.path.exists(SUMMARY_FILE):
    print(f"[ERROR] {SUMMARY_FILE} not found. Run test_atlas.sh first.")
    exit(1)

with open(SUMMARY_FILE, "r") as f:
    lines = f.readlines()

errors = []
retries = []
todos = []

for line in lines:
    if re.search(r"error", line, re.IGNORECASE):
        errors.append(line.strip())
    if "Retry queue for" in line:
        current = line.strip().split("Retry queue for ")[-1].split(":")[0]
        idx = lines.index(line)
        for retry_line in lines[idx + 1 :]:
            if (
                retry_line.strip() == ""
                or retry_line.startswith("##")
                or retry_line.startswith("---")
            ):
                break
            retries.append(f"{current}: {retry_line.strip()}")
    if re.search(r"TODO|FIXME|not implemented|placeholder", line, re.IGNORECASE):
        todos.append(line.strip())

with open(NEXT_ACTIONS_FILE, "w") as f:
    f.write("# Atlas Next Actions (auto-generated from test summary)\n\n")
    f.write("## Errors\n" + ("\n".join(errors) if errors else "None found.") + "\n\n")
    f.write(
        "## Retries\n" + ("\n".join(retries) if retries else "None found.") + "\n\n"
    )
    f.write("## TODOs\n" + ("\n".join(todos) if todos else "None found.") + "\n")

print("\n[Atlas Test Summary Parser]")
print(f"Errors found: {len(errors)}")
print(f"Retries found: {len(retries)}")
print(f"TODOs found: {len(todos)}")
print(f"See {NEXT_ACTIONS_FILE} for details.\n")
