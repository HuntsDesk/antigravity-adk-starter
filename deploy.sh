#!/usr/bin/env bash
# Deploy access_triage to Agent Runtime (Gemini Enterprise Agent Platform).
#
# First deployment:
#   PROJECT_ID=your-project-id ./deploy.sh
#
# Update an existing deployment instead of creating a second one with the same name:
#   PROJECT_ID=your-project-id AGENT_ENGINE_ID=1234567890 ./deploy.sh
# (AGENT_ENGINE_ID is the number at the end of the reasoningEngines/ resource name.)
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project ID}"
REGION="${REGION:-us-central1}"
EXTRA=()
if [ -n "${AGENT_ENGINE_ID:-}" ]; then
  EXTRA=(--agent_engine_id="$AGENT_ENGINE_ID")
fi
adk deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="Cymbal Access Triage" \
  ${EXTRA[@]+"${EXTRA[@]}"} \
  access_triage
