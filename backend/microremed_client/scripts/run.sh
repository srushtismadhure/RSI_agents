#!/bin/bash
ENV_NAME=$1
if [ -z "$ENV_NAME" ]; then
  echo "Usage: bash run.sh <env_name> <server_url>"
  exit 1
fi

SERVER_URL=$2
if [ -z "SERVER_URL" ]; then
  echo "Usage: bash run.sh <env_name> <server_url>"
  exit 1
fi

bash stop_chaos.sh $ENV_NAME
python3 inject_and_remediate.py \
  --experiments 50 \
  --namespace ${ENV_NAME} \
  --wait-interval 10 \
  --injection-timeout 60 \
  --env ${ENV_NAME} \
  --save-path conversations \
  --manifest-path envs/source-config/${ENV_NAME}-config.yaml \
  --remediate-method SoloGen \
  --experiment-path experiments/easy.txt \
  --model qwen-plus \
  --server-url ${SERVER_URL} \

