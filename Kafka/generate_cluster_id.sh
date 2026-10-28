#!/usr/bin/env bash
set -euo pipefail

docker run --rm apache/kafka:4.4.0 \
  /opt/kafka/bin/kafka-storage.sh random-uuid
