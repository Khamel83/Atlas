# Atlas Quick Start Guide

This guide provides the bare minimum steps to get Atlas up and running in 5 minutes.

## 1. Installation

First, clone the repository and install the required Python packages:

```bash
# Clone the repository
git clone https://github.com/your-username/Atlas.git
cd Atlas

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

Next, create a `.env` file from the example template and configure it:

```bash
# Copy the example .env file
cp .env.example .env
```

Now, open the `.env` file in a text editor and at a minimum, set the `DATA_DIRECTORY`.

## 3. Running Atlas

With the configuration in place, you can now run Atlas. To process all content types, use the `--all` flag:

```bash
python3 run.py --all
```

You can also process specific content types:

```bash
# Process articles
python3 run.py --articles

# Process YouTube videos
python3 run.py --youtube

# Process podcasts
python3 run.py --podcasts
```

## 4. Exploring the Web UI

Atlas also includes a web interface for exploring the cognitive amplification features. To use it, you'll need to install the web-specific dependencies:

```bash
pip install -r web/requirements.txt
```

Then, start the web server:

```bash
uvicorn web.app:app --reload --port 8000
```

You can now access the web UI in your browser at [http://localhost:8000/ask/html](http://localhost:8000/ask/html).