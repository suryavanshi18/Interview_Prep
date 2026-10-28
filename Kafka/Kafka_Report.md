
# 3-Node Kafka KRaft Cluster Deployment and Troubleshooting Report

## 1. Objective

The goal is to deploy a highly available Apache Kafka cluster across three Linux virtual machines using Docker and Kafka KRaft mode, without ZooKeeper.

Each VM runs one Kafka process with both roles:

```text
broker + controller
```

Final environment:

```text
VM1
IP      : 192.168.181.138
Node ID : 1
Role    : broker, controller

VM2
IP      : 192.168.181.65
Node ID : 2
Role    : broker, controller

VM3
IP      : 192.168.181.91
Node ID : 3
Role    : broker, controller
```

All three nodes belong to the same Kafka cluster:

```text
CLUSTER_ID=F7glpWZ4TMyuSVXzi4avhg
```

The KRaft controller quorum is:

```text
1@192.168.181.138:9093
2@192.168.181.65:9093
3@192.168.181.91:9093
```

Kafka uses:

```text
9092 → Broker/client communication
9093 → KRaft controller communication
```

---

# 2. Final Architecture

```text
                    KRaft Controller Quorum
                         TCP 9093

       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼

     VM1                VM2                VM3
192.168.181.138     192.168.181.65     192.168.181.91
   Node 1              Node 2              Node 3

Broker + Controller  Broker + Controller  Broker + Controller
     :9092               :9092               :9092
     :9093               :9093               :9093

       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                    Kafka Cluster
                          │
              ┌───────────┴───────────┐
              │                       │
          Producer                 Consumer
```

One of the three controllers becomes the active KRaft controller leader.

In the final verified state:

```text
LeaderId: 1
```

Therefore VM1 was the current controller leader.

VM2 and VM3 were controller followers.

Controller leadership can change automatically if the leader fails.

---

# 3. Kafka Docker Configuration

Each machine should use the same Docker Compose definition but a different `NODE_ID` and `NODE_IP`.

Important Kafka settings:

```yaml
KAFKA_PROCESS_ROLES: "broker,controller"

KAFKA_LISTENERS: "BROKER://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093"

KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "BROKER:PLAINTEXT,CONTROLLER:PLAINTEXT"

KAFKA_INTER_BROKER_LISTENER_NAME: "BROKER"

KAFKA_CONTROLLER_LISTENER_NAMES: "CONTROLLER"

KAFKA_CONTROLLER_QUORUM_VOTERS: "1@192.168.181.138:9093,2@192.168.181.65:9093,3@192.168.181.91:9093"

KAFKA_DEFAULT_REPLICATION_FACTOR: "3"

KAFKA_MIN_INSYNC_REPLICAS: "2"

KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "3"

KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "3"

KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "2"
```

VM1 should advertise:

```text
BROKER://192.168.181.138:9092
```

VM2:

```text
BROKER://192.168.181.65:9092
```

VM3:

```text
BROKER://192.168.181.91:9092
```

---

# 4. Step 1 — Generate One Cluster ID

Generate the Kafka cluster ID only once.

Example:

```bash
docker run --rm apache/kafka:4.4.0 \
  /opt/kafka/bin/kafka-storage.sh random-uuid
```

The resulting value must be used on all three machines.

In this deployment:

```text
F7glpWZ4TMyuSVXzi4avhg
```

Therefore:

```text
VM1 → F7glpWZ4TMyuSVXzi4avhg
VM2 → F7glpWZ4TMyuSVXzi4avhg
VM3 → F7glpWZ4TMyuSVXzi4avhg
```

Never generate a separate cluster ID for each VM.

Verify it with:

```bash
docker inspect kafka \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep CLUSTER_ID
```

---

# 5. Step 2 — Configure Node IDs

Each node must have a unique ID.

VM1:

```text
KAFKA_NODE_ID=1
```

VM2:

```text
KAFKA_NODE_ID=2
```

VM3:

```text
KAFKA_NODE_ID=3
```

Node IDs must match the IDs configured in:

```text
KAFKA_CONTROLLER_QUORUM_VOTERS
```

---

# 6. Step 3 — Prepare Kafka Storage

Kafka's Docker image runs using:

```text
uid=1000(appuser)
gid=1000(appuser)
```

One major issue encountered during deployment was:

```text
java.nio.file.AccessDeniedException:
/tmp/kraft-combined-logs/__cluster_metadata-0
```

The Kafka Docker volume was owned by:

```text
UID 0
GID 0
```

while Kafka ran as:

```text
UID 1000
GID 1000
```

This prevented Kafka from creating the KRaft metadata directory.

## Diagnose storage permissions

Find the volume:

```bash
docker volume ls
```

In this environment:

```text
kafka_kafka_data
```

Inspect ownership:

```bash
docker run --rm \
  -v kafka_kafka_data:/data \
  alpine \
  sh -c 'ls -ldn /data && ls -lan /data'
```

Problematic output:

```text
drwxr-xr-x ... 0 0 ... /data
```

This means:

```text
owner UID = 0
group GID = 0
```

## Fix the volume

Run on each Kafka VM:

```bash
docker run --rm \
  -v kafka_kafka_data:/data \
  alpine \
  sh -c 'chown -R 1000:1000 /data && chmod -R u+rwX /data'
```

Verify:

```bash
docker run --rm \
  -v kafka_kafka_data:/data \
  alpine \
  ls -ldn /data
```

Expected:

```text
1000 1000
```

This fix was required independently on VM1, VM2, and VM3.

---

# 7. Error: AccessDeniedException

Observed error:

```text
Formatting metadata directory /tmp/kraft-combined-logs

java.nio.file.AccessDeniedException:
/tmp/kraft-combined-logs/__cluster_metadata-0
```

Diagnosis:

```text
Kafka container
      │
      │ UID 1000
      ▼
Kafka volume
      │
      │ owned by UID 0
      ▼
Kafka cannot create metadata
      │
      ▼
Kafka exits/restarts
```

Resolution:

```bash
chown -R 1000:1000
```

on the Kafka Docker volume.

The following messages were also present:

```text
Mismatched values for property jdk.module.addmods
Disabling optimized module handling
```

These JVM CDS/AOT warnings were not the fatal problem.

The actual fatal problem was:

```text
AccessDeniedException
```

Always troubleshoot the final exception/root cause rather than assuming the first warning is responsible.

---

# 8. Step 4 — Configure Firewall

Both ports must be reachable between Kafka nodes.

```text
9093 → controller-to-controller communication
9092 → broker/client and broker communication
```

Using firewalld:

```bash
sudo firewall-cmd --permanent --add-port=9092/tcp
sudo firewall-cmd --permanent --add-port=9093/tcp
sudo firewall-cmd --reload
```

Verify:

```bash
sudo firewall-cmd --list-ports
```

Expected:

```text
9092/tcp
9093/tcp
```

For a more secure production deployment, restrict `9093` to only the Kafka nodes instead of exposing it generally.

---

# 9. Test Controller Connectivity

From VM1:

```bash
nc -vz 192.168.181.65 9093
nc -vz 192.168.181.91 9093
```

From VM2:

```bash
nc -vz 192.168.181.138 9093
nc -vz 192.168.181.91 9093
```

From VM3:

```bash
nc -vz 192.168.181.138 9093
nc -vz 192.168.181.65 9093
```

Expected:

```text
Connected to <IP>:9093
```

If it says:

```text
Connection refused
```

the remote Kafka service is probably not listening.

If it times out, investigate:

```text
firewall
routing
security groups
network ACLs
```

---

# 10. Step 5 — Start Kafka

On each VM:

```bash
docker compose up -d
```

Verify container:

```bash
docker ps | grep kafka
```

Healthy state:

```text
Up ... (healthy)
```

If the container shows:

```text
Up 3 seconds
```

despite having been created many minutes earlier, check whether it is repeatedly restarting:

```bash
docker inspect kafka \
  --format 'RestartCount={{.RestartCount}} Status={{.State.Status}} ExitCode={{.State.ExitCode}}'
```

---

# 11. Check Kafka Listening Ports

Run:

```bash
sudo ss -lntp | grep -E '9092|9093'
```

Healthy combined broker/controller node:

```text
*:9092 LISTEN
*:9093 LISTEN
```

Interpretation:

```text
9093 present, 9092 missing
```

usually indicates the KRaft controller listener has started but broker initialization has not completed.

This occurred during our deployment.

---

# 12. Error: Broker Port 9092 Not Available

Initial verification produced:

```text
Connection to node -1 (/192.168.181.138:9092)
could not be established.
```

At that time:

```text
9093 → LISTENING
9092 → NOT LISTENING
```

Kafka logs showed:

```text
MetadataLoader ...
we still don't know the high water mark yet
```

and:

```text
Connection to node 2 (/192.168.181.65:9093)
could not be established
```

This indicated that the controller quorum was not yet healthy.

The sequence was:

```text
Controller listener starts
        │
        ▼
KRaft attempts quorum formation
        │
        ▼
controller communication fails
        │
        ▼
metadata cannot catch up
        │
        ▼
broker initialization waits
        │
        ▼
9092 unavailable
```

After fixing controller connectivity, broker initialization continued successfully.

---

# 13. Signs of Successful Broker Startup

Successful Kafka logs included:

```text
Successfully registered broker 1
```

followed by:

```text
The broker has caught up.
Transitioning from STARTING to RECOVERY.
```

then:

```text
The broker has been unfenced.
Transitioning from RECOVERY to RUNNING.
```

followed by:

```text
Endpoint BROKER is now READY.
```

and:

```text
Awaiting socket connections on 0.0.0.0:9092.
```

finally:

```text
Transition from STARTING to STARTED
```

These are excellent indicators of a healthy broker.

---

# 14. Verify Effective Kafka Configuration

Use:

```bash
docker inspect kafka \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E 'NODE_ID|CLUSTER_ID|QUORUM|LISTENERS|ADVERTISED'
```

Example for VM3:

```text
KAFKA_CONTROLLER_QUORUM_VOTERS=
1@192.168.181.138:9093,
2@192.168.181.65:9093,
3@192.168.181.91:9093

KAFKA_ADVERTISED_LISTENERS=
BROKER://192.168.181.91:9092

KAFKA_LISTENERS=
BROKER://0.0.0.0:9092,
CONTROLLER://0.0.0.0:9093

KAFKA_NODE_ID=3

CLUSTER_ID=F7glpWZ4TMyuSVXzi4avhg
```

This command is particularly useful because it confirms what Docker actually passed to Kafka rather than what is merely written in `.env`.

---

# 15. Step 6 — Verify KRaft Quorum

Run from any Kafka machine:

```bash
docker exec kafka \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-controller 192.168.181.138:9093 \
  describe --status
```

Final healthy output:

```text
ClusterId:              F7glpWZ4TMyuSVXzi4avhg
LeaderId:               1
LeaderEpoch:            21505
HighWatermark:          ...
MaxFollowerLag:         0
MaxFollowerLagTimeMs:   0

CurrentVoters:
1 → 192.168.181.138:9093
2 → 192.168.181.65:9093
3 → 192.168.181.91:9093
```

Key indicators:

```text
CurrentVoters = all 3 nodes
MaxFollowerLag = 0
```

This means all controllers are synchronized.

Current controller leader:

```text
LeaderId=1
```

Therefore VM1 was the current KRaft controller leader.

---

# 16. Understand KRaft Majority

With three controllers:

```text
N = 3
majority = 2
```

Therefore:

```text
VM1 UP
VM2 UP
VM3 DOWN

→ cluster can continue
```

But:

```text
VM1 UP
VM2 DOWN
VM3 DOWN

→ no controller majority
```

A three-controller quorum can tolerate one controller failure.

---

# 17. Step 7 — Create Kafka Topic

Topic created:

```text
demo-events
```

Command:

```bash
VM1_IP=192.168.181.138 \
./scripts/create_topic.sh demo-events 6 3
```

Result:

```text
PartitionCount:       6
ReplicationFactor:    3
min.insync.replicas:  2
unclean.leader.election.enable=false
```

Leadership distribution:

```text
Partition 0 → Leader 2
Partition 1 → Leader 3
Partition 2 → Leader 1
Partition 3 → Leader 2
Partition 4 → Leader 1
Partition 5 → Leader 3
```

This provides a balanced distribution:

```text
Broker 1 → 2 partition leaders
Broker 2 → 2 partition leaders
Broker 3 → 2 partition leaders
```

---

# 18. Verify Topic Replicas

Example:

```text
Partition: 0
Leader: 2
Replicas: 2,3,1
Isr: 2,3,1
```

Meaning:

```text
Broker 2 → leader
Broker 3 → follower
Broker 1 → follower
```

All three brokers are in ISR.

ISR means:

```text
In-Sync Replicas
```

Healthy state:

```text
Replicas = 1,2,3
ISR      = 1,2,3
```

for every partition.

---

# 19. Why Replication Factor 3 and Min ISR 2

Configuration:

```text
replication.factor = 3
min.insync.replicas = 2
producer acks = all
```

Normal state:

```text
Broker 1 ✅
Broker 2 ✅
Broker 3 ✅

ISR = 3
```

One broker fails:

```text
Broker 1 ✅
Broker 2 ✅
Broker 3 ❌

ISR = 2
```

Kafka can continue accepting writes.

Two brokers fail:

```text
Broker 1 ✅
Broker 2 ❌
Broker 3 ❌

ISR = 1
```

Kafka refuses writes when producer uses:

```text
acks=all
```

because `min.insync.replicas=2`.

This prioritizes durability over availability.

---

# 20. Step 8 — Producer Setup

Producer can run on any machine that can reach:

```text
192.168.181.138:9092
192.168.181.65:9092
192.168.181.91:9092
```

Configure:

```bash
export KAFKA_BOOTSTRAP_SERVERS="192.168.181.138:9092,192.168.181.65:9092,192.168.181.91:9092"
```

Run:

```bash
python producer.py \
  --topic demo-events \
  --count 20
```

In testing, the producer successfully ran on VM3.

---

# 21. Step 9 — Consumer Setup

The consumer can similarly run on any application machine with broker connectivity.

Example:

```bash
export KAFKA_BOOTSTRAP_SERVERS="192.168.181.138:9092,192.168.181.65:9092,192.168.181.91:9092"
```

Run:

```bash
python consumer.py \
  --topic demo-events \
  --group-id demo-consumer-group
```

During testing:

```text
Producer → VM3
Consumer → VM1
```

Messages were successfully produced and consumed.

This confirmed that Kafka's data plane was operating across different VMs.

---

# 22. Producer Connection Flow

The producer does not permanently send everything to the first bootstrap broker.

The bootstrap list is only used for initial discovery:

```text
Producer
   │
   ▼
192.168.181.138:9092
192.168.181.65:9092
192.168.181.91:9092
   │
   ▼
receives cluster metadata
   │
   ▼
discovers partition leaders
   │
   ├── Partition 0 → Broker 2
   ├── Partition 1 → Broker 3
   ├── Partition 2 → Broker 1
   └── ...
```

The producer then talks directly to the correct partition leader.

---

# 23. Useful Producer Settings

Reliable producer configuration:

```python
{
    "bootstrap.servers": "...",
    "acks": "all",
    "enable.idempotence": True,
    "compression.type": "zstd"
}
```

`acks=all` works together with:

```text
min.insync.replicas=2
```

for durability.

---

# 24. Consumer Offset Strategy

Consumer configuration:

```python
"enable.auto.commit": False
```

After processing:

```python
process_message(msg)

consumer.commit(
    message=msg,
    asynchronous=False
)
```

This provides an at-least-once processing pattern.

If processing fails, do not commit the offset.

Kafka can then deliver the message again.

---

# 25. Final VM3 Diagnosis

At one stage VM1 repeatedly showed:

```text
node 3 being disconnected
```

Later VM3 showed:

```text
Awaiting socket connections on 0.0.0.0:9092
```

and:

```text
Transition from STARTING to STARTED
Kafka Server started
```

Connectivity tests from VM1 succeeded:

```bash
nc -vz 192.168.181.91 9093
nc -vz 192.168.181.91 9092
```

Both connected successfully.

The final quorum status showed:

```text
CurrentVoters = 1,2,3
MaxFollowerLag = 0
```

and recent VM3 logs showed no:

```text
disconnected
error
fatal
```

Therefore the earlier VM3 problem was resolved.

---

# 26. Recommended Troubleshooting Order

When Kafka fails, use the following sequence instead of debugging randomly.

```text
1. Docker container running?
          │
          ▼
2. Volume writable?
          │
          ▼
3. Controller port 9093 listening?
          │
          ▼
4. Controllers reachable from each other?
          │
          ▼
5. KRaft quorum healthy?
          │
          ▼
6. Broker registered/unfenced?
          │
          ▼
7. Broker port 9092 listening?
          │
          ▼
8. Brokers mutually reachable?
          │
          ▼
9. Topic replicas/ISR healthy?
          │
          ▼
10. Producer/consumer test
```

---

# 27. Troubleshooting Command Checklist

### Container

```bash
docker ps | grep kafka
```

### Restart count

```bash
docker inspect kafka \
  --format 'RestartCount={{.RestartCount}} Status={{.State.Status}} ExitCode={{.State.ExitCode}}'
```

### Recent errors

```bash
docker logs --since 5m kafka | \
grep -Ei 'disconnected|error|fatal|exception'
```

### Full recent logs

```bash
docker logs --tail 200 kafka
```

### Listening ports

```bash
sudo ss -lntp | grep -E '9092|9093'
```

### Controller connectivity

```bash
nc -vz <VM_IP> 9093
```

### Broker connectivity

```bash
nc -vz <VM_IP> 9092
```

### Kafka environment

```bash
docker inspect kafka \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
grep -E 'NODE_ID|CLUSTER_ID|QUORUM|LISTENERS|ADVERTISED'
```

### Quorum

```bash
docker exec kafka \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-controller 192.168.181.138:9093 \
  describe --status
```

### Topics

```bash
docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server 192.168.181.138:9092 \
  --list
```

### Topic health

```bash
docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server 192.168.181.138:9092 \
  --describe \
  --topic demo-events
```

---

# 28. Error Diagnosis Matrix

| Symptom | Likely Problem | Check | Fix |
|---|---|---|---|
| `AccessDeniedException` under `kraft-combined-logs` | Volume ownership | `ls -ldn /data` | `chown -R 1000:1000` |
| Container constantly restarting | Kafka startup failure | `RestartCount`, logs | Fix underlying Kafka error |
| `9093` not listening | Controller not initialized | `ss -lntp` | Check config/storage |
| `9093` listening but `9092` missing | Broker initialization incomplete | Kafka logs | Check quorum |
| `could not connect to node X:9093` | Controller network/firewall issue | `nc -vz IP 9093` | firewall/network |
| `could not connect ... :9092` | Broker not ready/reachable | `ss`, `nc` | wait/fix broker |
| `we still don't know the high water mark` | Metadata quorum not synchronized | quorum status | Fix controller connectivity |
| Node repeatedly disconnected | Network, controller unavailable or startup incomplete | `nc`, node logs | Fix remote node |
| `CurrentVoters` missing a node | Controller not joined | quorum status | Node/config/network |
| `MaxFollowerLag > 0` continuously | Controller follower behind | quorum status/logs | network/disk/load |
| ISR missing one broker | Replica unavailable/lagging | topic describe | investigate broker |
| ISR < `min.insync.replicas` | Writes unavailable with `acks=all` | topic describe | restore broker |
| Producer cannot connect | 9092/firewall/advertised listener | `nc`, inspect env | fix listener/firewall |
| Broker advertises wrong IP | Clients connect to invalid address | inspect environment | fix `advertised.listeners` |

---

# 29. HA Failure Test

After establishing a healthy cluster, test failover.

Start producer and consumer continuously.

Then stop VM2 Kafka:

```bash
docker stop kafka
```

Describe the topic from VM1:

```bash
docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server 192.168.181.138:9092 \
  --describe \
  --topic demo-events
```

Before failure:

```text
ISR = 1,2,3
```

After VM2 stops:

```text
ISR = 1,3
```

Partitions previously led by broker 2 should elect another in-sync replica as leader.

Producer/consumer traffic should continue because:

```text
replication factor = 3
min ISR = 2
```

Restart VM2:

```bash
docker start kafka
```

Wait for it to catch up.

Then topic description should eventually return to:

```text
ISR = 1,2,3
```

---

# 30. Recommended Monitoring

For production, monitor at least:

```text
Broker availability
Controller leader
Controller quorum follower lag
Under-replicated partitions
ISR changes
Offline partitions
Producer request latency
Consumer lag
Disk usage
Disk latency
Network throughput
JVM heap/GC
Broker restart count
```

Particularly important alerts are:

```text
UnderReplicatedPartitions > 0

OfflinePartitionsCount > 0

ISR shrinking repeatedly

Controller changes repeatedly

Disk > 80%

Consumer lag continuously increasing
```

---

# 31. Production Improvements

The current environment uses:

```text
PLAINTEXT
```

for both broker and controller communication.

For a production environment, add:

```text
TLS
SASL authentication or mTLS
```

Do not expose:

```text
9092
9093
```

to the public Internet.

Port `9093` should ideally only be accessible between Kafka nodes.

Use persistent VM disks for Kafka data rather than ephemeral storage.

Also configure:

```text
NTP/time synchronization
monitoring
alerting
log rotation
disk capacity planning
```

For larger or more critical Kafka deployments, consider separating:

```text
controller nodes
```

from:

```text
broker nodes
```

rather than running:

```text
process.roles=broker,controller
```

on every machine.

---

# 32. Final Verified State

The final cluster state was:

```text
Cluster ID:
F7glpWZ4TMyuSVXzi4avhg

Controller leader:
Node 1 / VM1

Controller voters:
1 → 192.168.181.138
2 → 192.168.181.65
3 → 192.168.181.91

MaxFollowerLag:
0

Kafka brokers:
VM1 ✅
VM2 ✅
VM3 ✅

Topic:
demo-events

Partitions:
6

Replication factor:
3

Min ISR:
2

All replicas in ISR:
✅

Producer on VM3:
✅

Consumer on VM1:
✅

Cross-VM message delivery:
✅
```

Therefore the resulting cluster is a functioning three-node Kafka KRaft cluster with controller quorum redundancy, broker redundancy, replicated topic storage, and working producer/consumer traffic.

# 33. Operational Quick Reference

For day-to-day checking, these five commands are enough to diagnose most problems:

```bash
# 1. Container
docker ps | grep kafka

# 2. Errors
docker logs --since 5m kafka | \
grep -Ei 'error|fatal|exception|disconnected'

# 3. Listeners
sudo ss -lntp | grep -E '9092|9093'

# 4. KRaft health
docker exec kafka \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-controller 192.168.181.138:9093 \
  describe --status

# 5. Topic replication health
docker exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server 192.168.181.138:9092 \
  --describe \
  --topic demo-events
```

Healthy cluster indicators:

```text
container = healthy

9092 = listening
9093 = listening

CurrentVoters = 1,2,3

MaxFollowerLag = 0

all partitions have a leader

ISR contains all expected replicas
```

If these conditions are satisfied, the Kafka cluster is generally healthy.
