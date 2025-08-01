#!/bin/bash

set -e

echo "==> Setting up Claude Code global wrapper..."
CLAUDE_BIN="/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/cli.js"

if [ ! -f "$CLAUDE_BIN" ]; then
  echo "❌ Claude Code not found at $CLAUDE_BIN"
  exit 1
fi

# Create global wrapper
sudo tee /opt/homebrew/bin/claude-code >/dev/null <<EOF
#!/bin/bash
exec node "$CLAUDE_BIN" --yes "\$@"
EOF

sudo chmod +x /opt/homebrew/bin/claude-code
echo "✅ claude-code now runs with --yes by default."

echo "==> Setting up Gemini CLI trust mode..."

mkdir -p ~/.gemini

# Create Gemini settings.json with best auto-accept options
tee ~/.gemini/settings.json >/dev/null <<EOF
{
  "autoAccept": true,
  "sandbox": "docker",
  "checkpointing": true
}
EOF

# Create wrapper script for Gemini CLI
sudo tee /opt/homebrew/bin/gemini-yolo >/dev/null <<EOF
#!/bin/bash
exec gemini --trust --yolo "\$@"
EOF

sudo chmod +x /opt/homebrew/bin/gemini-yolo
echo "✅ gemini-yolo created: runs Gemini with --trust and --yolo always."

# Optional: Add aliases to shell
SHELL_RC="$HOME/.zshrc"
if ! grep -q "alias gemini-yolo=" "$SHELL_RC"; then
  echo "alias gemini-yolo='/opt/homebrew/bin/gemini-yolo'" >> "$SHELL_RC"
  echo "✅ alias added to $SHELL_RC (run: source ~/.zshrc)"
fi

echo ""
echo "✅ DONE. Use:"
echo "  claude-code .         # Claude Code in auto-trust mode"
echo "  gemini-yolo code ...  # Gemini CLI with max trust flags"
