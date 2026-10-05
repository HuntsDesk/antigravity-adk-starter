#!/usr/bin/env bash
# Deploy access_triage to Agent Runtime (Gemini Enterprise Agent Platform).
# Usage: PROJECT_ID=your-project-id ./deploy.sh
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project ID}"
REGION="${REGION:-us-central1}"
adk deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="Cymbal Access Triage" \
  access_triage
