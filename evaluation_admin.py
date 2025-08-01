import json
import os

import streamlit as st

from helpers.evaluation_utils import EVALUATION_DIR, EvaluationFile

st.set_page_config(layout="wide")
st.title("📝 Evaluation Admin & Feedback UI")


def find_evaluation_files():
    """Finds all .eval.json files in the evaluation directory."""
    eval_files = []
    if not os.path.exists(EVALUATION_DIR):
        return []

    for root, _, files in os.walk(EVALUATION_DIR):
        for file in files:
            if file.endswith(".eval.json"):
                eval_files.append(os.path.join(root, file))
    return eval_files


def display_evaluation_file(file_path):
    """Displays the content of a selected evaluation file and handles feedback."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        st.header(f"Reviewing: `{data.get('source_file', 'N/A')}`")

        # Display the source content if available
        source_path = data.get("source_file")
        if source_path and os.path.exists(source_path):
            with st.expander("Show Source Content"):
                with open(source_path, "r") as sf:
                    st.text(sf.read())

        st.subheader("AI-Generated Evaluations")
        if not data.get("evaluations"):
            st.info("No evaluations have been run on this file yet.")
        else:
            st.json(data["evaluations"])

        st.subheader("User-Submitted Feedback")
        if not data.get("user_feedback"):
            st.info("No user feedback has been submitted for this file yet.")
        else:
            st.json(data["user_feedback"])

        # --- Feedback Form in Sidebar ---
        st.sidebar.header("Submit Feedback")
        if data.get("evaluations"):
            # Let user choose which evaluation to give feedback on
            evaluator_ids = [e["evaluator_id"] for e in data["evaluations"]]
            target_evaluator = st.sidebar.selectbox(
                "Select Evaluation to Correct:", evaluator_ids
            )

            feedback_type = st.sidebar.selectbox(
                "Feedback Type:", ["Rating", "Correction", "Comment"]
            )

            payload = {}
            if feedback_type == "Rating":
                payload["rating"] = st.sidebar.select_slider(
                    "Rate Quality:", ["Good", "Okay", "Bad"]
                )

            payload["comment"] = st.sidebar.text_area(
                "Comment:", key=f"comment_{file_path}"
            )

            if feedback_type == "Correction":
                # Get original text to show it for correction
                original_text = ""
                for e in data["evaluations"]:
                    if e["evaluator_id"] == target_evaluator:
                        original_text = e["result"].get(
                            "summary_text", json.dumps(e["result"])
                        )
                        break
                payload["corrected_text"] = st.sidebar.text_area(
                    "Corrected Text:",
                    value=original_text,
                    height=250,
                    key=f"correction_{file_path}",
                )

            if st.sidebar.button("Submit Feedback", key=f"submit_{file_path}"):
                try:
                    # We need the source file path to initialize EvaluationFile
                    source_file_path = data.get("source_file")
                    if not source_file_path:
                        st.sidebar.error(
                            "Source file path not found in evaluation data. Cannot save feedback."
                        )
                        return

                    eval_file = EvaluationFile(source_file_path=source_file_path)
                    eval_file.add_user_feedback(
                        target_evaluator_id=target_evaluator,
                        feedback_type=feedback_type.lower(),
                        payload=payload,
                    )
                    eval_file.save()
                    st.sidebar.success("Feedback submitted and saved successfully!")
                    st.experimental_rerun()  # Rerun to show the new feedback
                except Exception as e:
                    st.sidebar.error(f"Error saving feedback: {e}")
        else:
            st.sidebar.warning("No evaluations to give feedback on.")

    except Exception as e:
        st.error(f"Failed to load or display evaluation file {file_path}: {e}")


# --- Main App ---
st.header("Select an Evaluation to Review")

evaluation_files = find_evaluation_files()

if not evaluation_files:
    st.warning(f"No evaluation files found in the `{EVALUATION_DIR}` directory.")
    st.info(
        "Run the ingestion pipeline (`python run.py`) to generate content and corresponding evaluation files."
    )
else:
    selected_file = st.selectbox("Choose an evaluation file:", evaluation_files)

    if selected_file:
        display_evaluation_file(selected_file)
