#!/bin/bash
# Run only bedrock-related tests

cd "$(dirname "$0")/.." || exit 1

pytest tests/test_bedrock_kb_handler.py \
       tests/test_bedrock_kb_integration.py \
       tests/test_evaluation_e2e_bedrock.py \
       "$@"
