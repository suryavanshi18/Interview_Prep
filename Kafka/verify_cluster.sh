#!/usr/bin/env bash
set -euo pipefail

VM1_IP="${VM1_IP:-10.10.0.11}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-${VM1_IP}:9092}"

echo '== Broker API check =='
docker exec kafka /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}"

echo
echo '== KRaft metadata quorum =='
docker exec kafka /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}" describe --status

echo
echo '== Topics =='
docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}" --list
