#!/bin/bash
echo '🔧 Creating missing files and folders...'
mkdir -p data/raw
touch data/raw/.gitkeep
mkdir -p data/parsed
touch data/parsed/.gitkeep
mkdir -p data/transcripts
touch data/transcripts/.gitkeep
mkdir -p data/collateral
touch data/collateral/.gitkeep
mkdir -p logs
touch logs/.gitkeep
mkdir -p output/articles
touch output/articles/.gitkeep
mkdir -p output/youtube
touch output/youtube/.gitkeep
mkdir -p output/podcasts
touch output/podcasts/.gitkeep
mkdir -p ask
echo "# README.md" > ask/README.md
mkdir -p process
echo "# README.md" > process/README.md
mkdir -p ingest
echo "# README.md" > ingest/README.md
echo "# run.py (empty placeholder)" > run.py
mkdir -p helpers
echo "# config.py (empty placeholder)" > helpers/config.py
echo "✅ Done creating missing files."
