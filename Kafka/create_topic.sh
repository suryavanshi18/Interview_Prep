#!/usr/bin/env bash
set -euo pipefail

TOPIC="${1:-demo-events}"
PARTITIONS="${2:-6}"
REPLICATION_FACTOR="${3:-3}"
VM1_IP="${VM1_IP:-10.10.0.11}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-${VM1_IP}:9092}"

docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}" \
  --create \
  --if-not-exists \
  --topic "${TOPIC}" \
  --partitions "${PARTITIONS}" \
  --replication-factor "${REPLICATION_FACTOR}" \
  --config min.insync.replicas=2

docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}" \
  --describe \
  --topic "${TOPIC}"
