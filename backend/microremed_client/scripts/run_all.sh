#!/bin/bash
ENV_NAME=$1
if [ -z "$ENV_NAME" ]; then
  echo "Usage: bash run.sh <env_name> <log_dir> <model> <server_url>"
  exit 1
fi

LOG_DIR=$2
if [ -z "$LOG_DIR" ]; then
  echo "Usage: bash run.sh <env_name> <log_dir> <model> <server_url>"
  exit 1
fi

MODEL=$3
if [ -z "$MODEL" ]; then
  echo "Usage: bash run.sh <env_name> <log_dir> <model> <server_url>"
  exit 1
fi

SERVER_URL=$4
if [ -z "SERVER_URL" ]; then
  echo "Usage: bash run.sh <env_name> <log_dir> <model> <server_url>"
  exit 1
fi

# Create or reuse log directory
mkdir -p "$LOG_DIR"

echo "=== [Init] Environment: $ENV_NAME ==="
echo "=== [Step 1] Stopping any existing chaos experiments ==="
bash scripts/stop_chaos.sh "$ENV_NAME"

# Function to deploy environment (runs in envs/$ENV_NAME)
deploy_env() {
  echo "=== [Deploy] Deploying environment: $ENV_NAME ==="

  curl -X POST $SERVER_URL/deploy_env \
  -H "Content-Type: application/json" \
  -d "{\"env_name\": \"$ENV_NAME\"}"

  return 1
}

# Function to run each experiment
run_experiment() {
  local method=$1
  local difficulty=$2

  echo "=== [Run] Starting $method ($difficulty) ==="
  env PYTHONUNBUFFERED=1 python3 inject_and_remediate.py \
    --experiments 50 \
    --namespace "$ENV_NAME" \
    --wait-interval 10 \
    --injection-timeout 60 \
    --env "$ENV_NAME" \
    --save-path conversations \
    --manifest-path "envs/source-config/${ENV_NAME}-config.yaml" \
    --remediate-method "$method" \
    --experiment-path "experiments/${difficulty}.txt" \
    --model "$MODEL" \
    --server-url "$SERVER_URL" \
    > "${LOG_DIR}/${method}_${difficulty}.log" 2>&1
  echo "=== [Run] Completed $method ($difficulty) ==="
}

# === Full experiment sequence ===
deploy_env
run_experiment "SoloGen" "easy"
deploy_env
run_experiment "ThinkRemed" "easy"
deploy_env
run_experiment "SoloGen" "medium"
deploy_env
run_experiment "ThinkRemed" "medium"
deploy_env
run_experiment "SoloGen" "hard"
deploy_env
run_experiment "ThinkRemed" "hard"

echo "=== ✅ All experiments completed successfully! Logs saved in ${LOG_DIR}/ ==="