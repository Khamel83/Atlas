import csv
import json
import os
import re
from collections import Counter, defaultdict

import requests
import streamlit as st

# --- Constants ---
TEST_LOGS_DIR = "test_logs/"
KNOWN_ERRORS_PATH = os.path.join("evaluation", "known_errors.json")

st.title("Test Trace & Error Review")

# --- Helper Functions ---


def list_log_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".json") or filename.endswith(".txt"):
                files.append(os.path.join(root, filename))
    return files


def get_suggestion(key):
    for k, v in SUGGESTIONS.items():
        if k.lower() in key.lower():
            return v
    return ""


# Real LLM-powered explanation via OpenRouter
@st.cache_data
def llm_explanation(error_message):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "Error: `OPENROUTER_API_KEY` not found. Please set it in your `config/.env` file."

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert developer assistant. Explain the following error message from a log file concisely, in simple terms. Identify the likely root cause and suggest a concrete next step for debugging.",
                    },
                    {"role": "user", "content": error_message},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}. Status code: {response.status_code}. Response: {response.text}"
    except Exception as e:
        return f"An unexpected error occurred when calling OpenRouter: {e}"


def load_known_errors():
    """Loads the known error statuses from a JSON file."""
    if os.path.exists(KNOWN_ERRORS_PATH):
        with open(KNOWN_ERRORS_PATH, "r") as f:
            return json.load(f)
    return {}


def save_known_errors(statuses):
    """Saves the known error statuses to a JSON file."""
    os.makedirs(os.path.dirname(KNOWN_ERRORS_PATH), exist_ok=True)
    with open(KNOWN_ERRORS_PATH, "w") as f:
        json.dump(statuses, f, indent=2)


# Advanced error clustering with regex normalization
def cluster_errors(error_lines):
    clusters = defaultdict(list)

    # Regex patterns to identify and normalize common error types
    # The key is a normalized name, the value is a regex to find it.
    # Order matters: more specific patterns should come first.
    patterns = {
        "HTTP Error": re.compile(
            r"(\d{3})\s*(Client Error|Server Error|Forbidden|Not Found|Unauthorized|Internal Server Error)",
            re.IGNORECASE,
        ),
        "File Not Found": re.compile(r"FileNotFoundError", re.IGNORECASE),
        "Permission Error": re.compile(r"PermissionError", re.IGNORECASE),
        "Connection Error": re.compile(
            r"ConnectionError|ConnectionTimeout", re.IGNORECASE
        ),
        "API Key Error": re.compile(r"APIKeyInvalid|Invalid API key", re.IGNORECASE),
        "Rate Limit Error": re.compile(r"RateLimitExceeded", re.IGNORECASE),
        "Transcription Error": re.compile(
            r"Transcription failed|WhisperError", re.IGNORECASE
        ),
        "Generic Exception": re.compile(r"Exception:|Traceback", re.IGNORECASE),
    }

    for line in error_lines:
        found_cluster = False
        for cluster_name, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                # For HTTP errors, make the code part of the key for better grouping
                if cluster_name == "HTTP Error":
                    key = f"HTTP Error: {match.group(1)}"
                else:
                    key = cluster_name
                clusters[key].append(line)
                found_cluster = True
                break

        if not found_cluster:
            # Fallback for unknown errors: strip numbers/hashes and use first few words
            normalized_line = re.sub(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z", "", line
            )  # Timestamp
            normalized_line = re.sub(
                r"[\d\w]{16,}", "<HASH>", normalized_line
            )  # Hashes
            normalized_line = re.sub(r"https?://\S+", "<URL>", normalized_line)  # URLs
            key = " ".join(normalized_line.split()[:5])
            clusters[f"Other: {key}"].append(line)

    return clusters


def generate_csv_export(clusters, statuses):
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Cluster Key", "Count", "Status", "Sample Message"])
    for key, lines in clusters.items():
        status = statuses.get(key, "new/critical")
        writer.writerow([key, len(lines), status, lines[0]])
    return output.getvalue()


def generate_md_export(clusters, statuses):
    md_lines = ["# Error Summary Report", ""]
    for key, lines in clusters.items():
        status = statuses.get(key, "new/critical")
        md_lines.append(f"## Cluster: {key}")
        md_lines.append(f"- **Count:** {len(lines)}")
        md_lines.append(f"- **Status:** {status}")
        md_lines.append("- **Sample Message:**")
        md_lines.append(f"```\n{lines[0]}\n```")
        md_lines.append("")
    return "\n".join(md_lines)


# --- Main App Logic ---

# Initialize session state from persisted file
if "cluster_status" not in st.session_state:
    st.session_state["cluster_status"] = load_known_errors()

log_files = list_log_files(TEST_LOGS_DIR)

if not log_files:
    st.warning(f"No test logs found in {TEST_LOGS_DIR}.")
else:
    selected_log = st.selectbox("Select a test log file:", log_files)
    with open(selected_log, "r") as f:
        if selected_log.endswith(".json"):
            try:
                log_data = json.load(f)
                st.json(log_data)
            except Exception as e:
                st.error(f"Failed to parse JSON: {e}")
                st.text(f.read())
        else:
            log_text = f.read()
            lines = log_text.splitlines()
            error_pattern = re.compile(
                r"error|fail|forbidden|exception|traceback", re.IGNORECASE
            )
            warning_pattern = re.compile(r"skipped", re.IGNORECASE)
            error_lines = [line for line in lines if error_pattern.search(line)]
            warning_lines = [
                line
                for line in lines
                if warning_pattern.search(line) and not error_pattern.search(line)
            ]
            error_count = len(error_lines)
            warning_count = len(warning_lines)
            total_lines = len(lines)
            st.markdown(f"**Total log lines:** {total_lines}")
            st.markdown(f"**Error lines:** {error_count}")
            st.markdown(f"**Warning (skipped) lines:** {warning_count}")

            def group_lines_by_message(lines, group_regex=None):
                groups = defaultdict(list)
                for line in lines:
                    if group_regex:
                        match = group_regex.search(line)
                        key = match.group(0) if match else line
                    else:
                        key = line
                    groups[key].append(line)
                return groups

            error_group_regex = re.compile(
                r"(error|fail|forbidden|exception|traceback|\d{3} [A-Za-z ]+)",
                re.IGNORECASE,
            )
            warning_group_regex = re.compile(r"skipped", re.IGNORECASE)
            error_groups = group_lines_by_message(error_lines, error_group_regex)
            warning_groups = group_lines_by_message(warning_lines, warning_group_regex)

            st.subheader("Error Summary Table")
            if error_groups:
                st.markdown("**Errors by Type/Message:**")
                error_summary = []
                for k, v in error_groups.items():
                    suggestion = get_suggestion(k)
                    if not suggestion:
                        if st.button(f"Ask LLM about: {k}"):
                            explanation = llm_explanation(k)
                            st.info(explanation)
                    error_summary.append(
                        {
                            "Type/Message": k,
                            "Count": len(v),
                            "Suggestion": (
                                suggestion if suggestion else "Ask LLM for help"
                            ),
                        }
                    )
                st.table(error_summary)
            else:
                st.success("No errors found!")

            st.subheader("Warning Summary Table")
            if warning_groups:
                st.markdown("**Warnings by Type/Message:**")
                warning_summary = []
                for k, v in warning_groups.items():
                    suggestion = get_suggestion(k)
                    if not suggestion:
                        if st.button(f"Ask LLM about: {k}"):
                            explanation = llm_explanation(k)
                            st.info(explanation)
                    warning_summary.append(
                        {
                            "Type/Message": k,
                            "Count": len(v),
                            "Suggestion": (
                                suggestion if suggestion else "Ask LLM for help"
                            ),
                        }
                    )
                st.table(warning_summary)
            else:
                st.success("No warnings found!")

            # Error clustering UI with marking
            st.subheader("Error Clusters (by main keyword or prefix)")
            error_clusters = cluster_errors(error_lines)
            if error_clusters:
                for cluster_key, cluster_lines in error_clusters.items():
                    status = st.session_state["cluster_status"].get(
                        cluster_key, "new/critical"
                    )
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(
                            f"**Cluster: {cluster_key}** ({len(cluster_lines)} errors) - Status: `{status}`"
                        )
                    with col2:
                        if st.button(
                            f"Mark as known/ignored", key=f"ignore_{cluster_key}"
                        ):
                            st.session_state["cluster_status"][
                                cluster_key
                            ] = "known/ignored"
                            save_known_errors(st.session_state["cluster_status"])
                            st.experimental_rerun()
                        if st.button(
                            f"Mark as new/critical", key=f"critical_{cluster_key}"
                        ):
                            st.session_state["cluster_status"][
                                cluster_key
                            ] = "new/critical"
                            save_known_errors(st.session_state["cluster_status"])
                            st.experimental_rerun()
                    with st.expander(f"Show examples for {cluster_key}"):
                        for line in cluster_lines[:10]:
                            st.text(line)
                        if len(cluster_lines) > 10:
                            st.text(f"...and {len(cluster_lines) - 10} more")

                # Export buttons
                st.subheader("Export Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="Export to Markdown",
                        data=generate_md_export(
                            error_clusters, st.session_state["cluster_status"]
                        ),
                        file_name=f"{os.path.basename(selected_log)}_error_summary.md",
                        mime="text/markdown",
                    )
                with col2:
                    st.download_button(
                        label="Export to CSV",
                        data=generate_csv_export(
                            error_clusters, st.session_state["cluster_status"]
                        ),
                        file_name=f"{os.path.basename(selected_log)}_error_summary.csv",
                        mime="text/csv",
                    )
            else:
                st.success("No error clusters found!")

            filter_option = st.radio(
                "Show:", ["All", "Errors only", "Warnings only", "Errors + Warnings"]
            )
            if filter_option == "Errors only":
                if error_lines:
                    for line in error_lines:
                        st.markdown(
                            f'<span style="color:red">{line}</span>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("No errors found!")
            elif filter_option == "Warnings only":
                if warning_lines:
                    for line in warning_lines:
                        st.markdown(
                            f'<span style="color:orange">{line}</span>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("No warnings found!")
            elif filter_option == "Errors + Warnings":
                if error_lines or warning_lines:
                    for line in lines:
                        if error_pattern.search(line):
                            st.markdown(
                                f'<span style="color:red">{line}</span>',
                                unsafe_allow_html=True,
                            )
                        elif warning_pattern.search(line):
                            st.markdown(
                                f'<span style="color:orange">{line}</span>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.success("No errors or warnings found!")
            else:
                for line in lines:
                    if error_pattern.search(line):
                        st.markdown(
                            f'<span style="color:red">{line}</span>',
                            unsafe_allow_html=True,
                        )
                    elif warning_pattern.search(line):
                        st.markdown(
                            f'<span style="color:orange">{line}</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.text(line)
