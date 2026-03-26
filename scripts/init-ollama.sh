#!/bin/sh
set -e

echo '🥔 Waiting for Ollama to be ready...'
until curl -sf http://ollama:11434/api/tags > /dev/null 2>&1; do sleep 2; done

MODEL_NAME="${LLM_MODEL:-qwen2.5-coder:14b}"
echo "🥔 Pulling model $MODEL_NAME..."

curl -s http://ollama:11434/api/pull -d "{\"name\":\"$MODEL_NAME\"}"

echo '🥔 Model ready! Potato is powered up.'
