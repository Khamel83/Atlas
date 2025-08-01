import datetime
import os
import random
import time

LOG_DIR = "test_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# --- Dimensions for Synthetic Log Generation ---

LOG_LEVELS = ["INFO", "INFO", "INFO", "WARNING", "ERROR", "DEBUG"]
CONTEXTS = [
    "ArticleFetcher",
    "PodcastIngestor",
    "YoutubeDownloader",
    "TranscriptionService",
    "MainPipeline",
]
HTTP_ERRORS = [
    "403 Forbidden",
    "404 Not Found",
    "500 Internal Server Error",
    "401 Unauthorized",
]
FILE_ERRORS = [
    "FileNotFoundError: /data/input.csv",
    "PermissionError: /app/config.yaml",
]
API_ERRORS = [
    "APIKeyInvalid: Your API key has expired.",
    "RateLimitExceeded: 200 requests/min",
]
SUCCESS_MESSAGES = [
    "Successfully processed item",
    "Ingestion complete for source",
    "Transcript downloaded",
    "Metadata saved",
]
WARNING_MESSAGES = [
    "Skipped item due to existing record",
    "Retrying in 5s",
    "Configuration value 'X' is deprecated",
]


def generate_log_line():
    """Generates a single, realistic log line from a combination of dimensions."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    level = random.choice(LOG_LEVELS)
    context = random.choice(CONTEXTS)

    if level == "ERROR":
        error_type = random.choice([HTTP_ERRORS, FILE_ERRORS, API_ERRORS])
        message = random.choice(error_type)
    elif level == "WARNING":
        message = random.choice(WARNING_MESSAGES)
    else:
        message = random.choice(SUCCESS_MESSAGES)

    return f"{timestamp} [{level}] [{context}] {message}"


def generate_log_file(filename="synthetic_log.txt", num_lines=500):
    """Generates a complete log file with a mix of message types."""
    path = os.path.join(LOG_DIR, filename)
    print(f"Generating synthetic log file with {num_lines} lines at: {path}")

    with open(path, "w") as f:
        for _ in range(num_lines):
            f.write(generate_log_line() + "\n")
            time.sleep(0.005)  # Simulate time passing between log entries

    print("Log generation complete.")


if __name__ == "__main__":
    generate_log_file(filename="synthetic_log_1.txt", num_lines=200)
    generate_log_file(filename="synthetic_log_2_more_errors.txt", num_lines=300)
    # Make the second log have more prominent errors
    with open(os.path.join(LOG_DIR, "synthetic_log_2_more_errors.txt"), "a") as f:
        for _ in range(50):
            level = "ERROR"
            context = "ArticleFetcher"
            message = random.choice(HTTP_ERRORS)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            f.write(f"{timestamp} [{level}] [{context}] {message}\n")

    print("\nDone creating synthetic logs.")
