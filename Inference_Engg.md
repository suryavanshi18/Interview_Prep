# How to Prep for a Technical Interview Using Claude: On-Device AI Edition

A practical guide built from a real interview cycle — covering how to use Claude
to build a structured study guide from scratch, and how to re-derive your own
past work rigorously enough to defend it in a final round.

---

## Part 1: Building a From-Scratch Study Guide with Claude

### The Problem with Scattered Resources

The default prep instinct is to open ten tabs — a Medium post on quantization,
a GitHub README on ONNX Runtime, a blog about KV caching — and bookmark them
all. This creates the illusion of coverage. In reality, each source uses
different terminology, different levels of depth, and different assumed knowledge.
You end up re-learning the same concept three times from three partial
explanations, and you never build a single coherent mental model.

The better approach: **use Claude to build one living document** that you keep
revising as your understanding deepens. One source, your terminology, your level
of detail.

---

### How to Structure the Conversation

Don't ask Claude to "explain on-device AI." That produces a survey, not a study
guide. Instead, drive it like a curriculum — start from the constraint that
makes everything else necessary, then build outward.

**A useful starting prompt pattern:**

> "I'm preparing for a systems design interview on on-device AI inference. I want
> to build a single study guide I can keep revising. Let's go topic by topic.
> Start with [TOPIC]. For each topic: explain the core concept, why it matters
> for on-device specifically, the key trade-offs, and one or two concrete
> examples. Don't summarize — go deep enough that I could explain this to
> another engineer."

Then work through each section below.

---

### Section 1: Model-Side Constraints — Quantization

**The core idea:** floating-point weights (fp32, fp16) are expensive in memory
and compute. Quantization replaces them with lower-precision integers (int8,
int4), reducing memory footprint and often improving latency on hardware with
fast integer units.

**Why it matters on-device:** a 7B parameter model in fp16 is ~14 GB. In int4
it's ~3.5 GB. On a phone or edge device with 6–8 GB of shared RAM, that's the
difference between running and not running.

**The trade-offs to internalize:**

- **int8** — roughly 2× memory reduction, minimal accuracy loss on most tasks.
  Well-supported by hardware. The safe default.
- **int4** — roughly 4× reduction, noticeable accuracy degradation on
  reasoning-heavy tasks. Requires careful calibration data. Worth it only when
  memory is severely constrained.
- **Quantization-aware training (QAT)** vs **post-training quantization (PTQ)**:
  QAT produces better models but requires retraining; PTQ applies quantization
  after the fact — faster to deploy, more accessible.

**The question to be ready for:** "You have 6 GB of RAM and a 7B model. What
do you do?" Answer: int4 quantization + model offloading strategy + possibly
a smaller model family (3B or 1B) as a fallback. Know why you'd choose each.

**How to use Claude here:**

> "Explain post-training quantization for LLMs. I want to understand: how does
> calibration work, what's actually happening numerically when you go from fp16
> to int8, and what failure modes look like in practice — not just theory."

---

### Section 2: Inference Engines and Execution Providers

**The core idea:** an inference engine takes a model (in ONNX, safetensors,
or another format) and executes it on hardware. The "execution provider" is
the plugin that maps abstract graph operations to hardware-specific
implementations.

**The main engines to understand:**

| Engine | Primary use case | Key execution providers |
|--------|-----------------|------------------------|
| ONNX Runtime | Cross-platform, CPU/GPU | CUDA, DirectML, CoreML, CPU |
| Core ML | Apple silicon | ANE (Neural Engine), GPU, CPU |
| TensorRT | NVIDIA GPUs | CUDA only |
| llama.cpp | LLMs on CPU/Metal/CUDA | Metal, CUDA, CPU |

**Why execution providers matter:** the same ONNX model runs on different
hardware via different providers. ONNX Runtime picks the best available provider
at runtime — but "best" is context-dependent. An NPU provider might be fastest
for a standard vision model but unsupported for a custom operator. The engine
falls back down the chain.

**The insight interviewers want:** you understand that the runtime's job is
**graph optimization + hardware dispatch**, not just "running the model." Know
that operator fusion (combining conv+relu into one kernel), constant folding,
and memory planning happen at the engine level, not the model level.

---

### Section 3: Hardware Fallback Chains

**The chain on modern devices:**

```
NPU (fastest, most efficient, most limited)
  ↓  if operator unsupported or model too large
GPU / Metal (fast, flexible, high memory bandwidth)
  ↓  if VRAM insufficient or driver issue
CPU (slowest, most compatible, no memory ceiling issue)
  ↓  NEVER silently
Cloud (different latency, privacy, and cost model)
```

**Why the chain matters:** NPUs are optimized for specific operator patterns
(typically standard conv/attention blocks). Novel architectures, custom ops,
or very large models may not fit. The engine must decide: partial NPU execution,
or full fallback? Partial execution has overhead from data transfer between
compute units.

**The critical design principle — cloud fallback must be explicit:**
Silent fallback to cloud is an antipattern. It breaks:
- **Privacy guarantees** — users may have chosen on-device specifically for
  privacy. Silent cloud means silent data upload.
- **Latency contracts** — cloud latency is ~10–100× on-device. If a feature
  promises on-device speed and silently goes to cloud, the UX is broken.
- **Offline functionality** — the whole point of on-device is network
  independence.

Cloud should be a deliberate user-facing choice, not an implementation detail.

**How to use Claude here:**

> "Walk me through what actually happens when ONNX Runtime falls back from
> CUDA to CPU. What triggers the fallback, what overhead does it introduce,
> and what should a well-designed system surface to the application layer when
> this happens?"

---

### Section 4: Memory Management

**KV-cache growth:** the key-value cache stores the attention representations
for all previous tokens in a conversation. It grows linearly with context
length and is re-used on each generation step to avoid recomputing past tokens.
On a 7B model with a 4K context window, the KV cache can occupy 1–2 GB
depending on precision and architecture.

**What to know:**
- KV cache is per-session, not per-model. Two concurrent sessions need two caches.
- When the context window fills, you must truncate (drop oldest tokens),
  summarize, or reject the request. There's no free option.
- PagedAttention (vLLM's key innovation) manages KV cache in variable-size
  blocks rather than contiguous memory, reducing fragmentation and allowing
  more concurrent sessions.

**Model swapping:** when you have more models than fit in memory, you need a
policy. The sensible default is LRU eviction — evict the least-recently-used
loaded model when memory pressure requires it. Key trade-offs:

- **Eviction latency:** model loading is slow (30–90 seconds for a 7B model).
  A cache miss is expensive. Design to minimize misses.
- **Warm vs cold workers:** a warm worker has the model loaded and is ready
  to serve. A cold worker needs to load first. The pool should aim to keep
  predicted-soon models warm. Prediction can be as simple as "the model I
  just served is likely to be requested again soon."
- **Proactive eviction:** don't wait for OOM. Evict idle models after a
  configurable timeout. Graceful eviction beats OOM-forced eviction.

---

### Section 5: Streaming — How Tokens Actually Get to the Client

**The naive wrong approach:** generate all tokens, then send the response.
Users see nothing for 10–30 seconds, then the whole response appears. Terrible
UX, and it buffers the full response in memory before the client sees anything.

**The right approach:** token-by-token streaming via SSE or IPC.

**Server-Sent Events (SSE):**
- HTTP/1.1 compatible, unidirectional (server → client)
- Each token is pushed as a small event: `data: {"token": "the"}\n\n`
- The client renders tokens as they arrive
- Connection stays open until generation completes or the client disconnects

**IPC (inter-process communication):**
- When the inference worker is a separate process, it writes tokens to a shared
  queue or pipe
- The API server reads from the queue and forwards to the SSE stream
- This decouples generation speed from network delivery speed

**The design detail that matters:** client disconnection. If the user closes the
tab, the SSE connection drops. The server must detect this and signal the worker
to stop generating. Otherwise the worker runs to completion, wasting compute on
tokens nobody will read. This is the difference between a well-designed streaming
system and one that burns resources silently.

---

### Section 6: Concurrency and Fair-Share Scheduling

**The problem:** you have a single inference worker that can serve one request
at a time. Multiple requests arrive. How do you schedule them?

**FIFO is the naive answer** — first in, first out. It's simple and fair in
one sense (order of arrival), but it lets a single long background job block
all interactive requests.

**Weighted round-robin** is the better answer for mixed workloads:
- Assign weights to request classes (interactive = 10, background = 1)
- The scheduler picks the next request proportional to weight
- A background job gets 1 slot for every 10 interactive slots
- Interactive requests never wait more than ~10 background tokens before
  getting their turn

**Other approaches worth knowing:**
- **Priority queues** — always serve the highest-priority request next.
  Simple but can starve low-priority work indefinitely.
- **Preemption** — pause a running generation to serve a higher-priority
  request. Complex to implement (requires saving/restoring KV cache state)
  but gives the best interactive latency.
- **Deadline scheduling** — each request has a maximum acceptable latency;
  the scheduler ensures deadlines are met or fails the request explicitly.

**The question underneath the scheduling question:** what does "fair" mean in
your system? Fair to users, fair to request classes, or fair to the hardware?
These give different answers. Know which one you're optimizing for.

---

### Section 7: Process Architecture — Supervisor/Worker Pattern

**The fundamental insight:** inference workers crash. GPU OOM errors, NaN
propagation, CUDA driver faults — these aren't bugs to fix, they're the
expected failure mode of running large models on constrained hardware. Design
for it.

**The architecture:**

```
┌─────────────────────────────┐
│  API Server (stable)         │  ← owns client connections, routing, queuing
│  never touches GPU memory    │
└────────────┬────────────────┘
             │  IPC (pipe / socket / shared memory)
    ┌────────┴────────┐
    │                 │
┌───▼────┐       ┌────▼───┐
│Worker A│       │Worker B│   ← each in its own process
│Model X │       │Model Y │   ← each owns GPU memory
└────────┘       └────────┘
```

**Why separate processes, not threads:**
- A GPU OOM error or segfault in a thread kills the whole process
- Python's GIL limits thread-level parallelism anyway
- Process boundaries are the right isolation unit for GPU memory

**Crash recovery logic:**

1. Worker crashes → server detects via exit signal or missed heartbeat
2. Server marks worker as unavailable, queued requests get a retryable error
3. Server restarts worker with exponential backoff (don't restart-loop instantly)
4. After N crashes in M minutes → mark model as unhealthy, stop retrying,
   surface an error to the operator

**"Crash-free by design" means:** the API server is crash-free. Workers are
allowed to crash and are expected to recover. The system's stability guarantee
is at the server level, not the worker level.

---

### Section 8: Classic Backend Fundamentals

These came up in the final round and are often underweighted in ML-focused prep.

**Idempotency:** an operation is idempotent if running it multiple times
produces the same result as running it once. Inference is naturally
non-idempotent (temperature sampling gives different outputs). If your client
retries a request after a timeout, it might get a different response —
or trigger the same long-running inference twice. Solutions:
- Request IDs that deduplicate on the server side
- Deterministic sampling (temperature=0) for requests where consistency matters

**Retries and backoff:** when a worker crashes mid-request, the client should
retry. But naive immediate retry (a "thundering herd") can overwhelm a
recovering worker. Exponential backoff with jitter is the standard answer:
wait 1s, then 2s, then 4s, with random jitter to spread load.

**Partial failure:** what happens if a request fails after 50 tokens have been
streamed? The client has partial output. The right answer depends on the use
case — surface the failure clearly, let the client decide whether to retry from
scratch or display partial output with a warning. Never pretend the failure
didn't happen.

**Timeouts at every layer:** set a timeout at the client, at the API server,
and on the inference call. Without all three, a slow worker can hold a
connection open indefinitely, exhausting server resources.

---

## Part 2: Re-Deriving Your Own Past Work

### Why This Matters More Than You Expect

Describing what you built is easy. Defending why you built it that way — and
what you'd change now — is what separates candidates who shipped things from
candidates who understand them.

Final rounds in systems roles routinely work like this: the interviewer takes
your resume or past project, picks one decision you made, and asks:
- Why that approach over the alternatives?
- What did you consider and reject?
- What would you do differently with hindsight?
- What would break at 10× scale?

The preparation for this isn't practicing answers — it's doing the analysis
honestly, before the interview, on your own work.

### The Framework: Three Questions Per Decision

Go through every significant decision in your past projects and answer:

**1. What did I actually decide and why?**
Not the polished retrospective — the actual reason. "We used X because it
was faster to implement" is an honest answer. "We used X because it was
the best tool" is not useful.

**2. What did I consider and not choose?**
If you can only name one option, you didn't make a decision — you made a
default. Interviewers can tell the difference. Know at least two alternatives
and be able to articulate why you didn't choose them.

**3. What would I change now?**
Showing that you've learned from what you built is more impressive than
claiming your original decisions were optimal. "I'd change X because I now
understand Y" demonstrates growth and intellectual honesty.

### Applied to On-Device AI Projects

If you built or worked on an inference system, an ML pipeline, or anything
involving model deployment, run through:

- **Model format choice:** why ONNX vs CoreML vs llama.cpp? What did the
  choice constrain downstream?
- **Memory budget decisions:** did you profile actual memory usage or estimate?
  What happened when you were wrong?
- **Error handling:** what did you do when inference failed? What should you
  have done?
- **Latency vs quality:** did you make any quantization or batching decisions
  for latency? What did you give up?
- **Monitoring:** how did you know when something was wrong in production?

### The Uncomfortable Questions to Prepare For

These are the ones that separate strong candidates:

- "You said you chose X for performance. Did you actually measure it against Y?"
- "What would happen to this system if traffic doubled overnight?"
- "If you were starting this over, what's the first thing you'd do differently?"
- "What's the biggest mistake you made on this project?"

Prepare honest answers. Interviewers asking these questions have usually
built similar systems themselves. Vague or defensive answers are immediately
obvious. Specific, honest answers — even about failures — build credibility.

---

## The Four Takeaways

**1. Treat on-device AI as a systems problem first.**
The interesting interview questions are about failure handling, memory
management, and concurrency. Model architecture almost never comes up.
Optimize your prep accordingly.

**2. Know your own past work cold.**
Interviewers pulling apart your project decisions is a real format.
Spend as much prep time on your own work as on new material.

**3. Build one consolidated resource, keep revising it.**
A single study guide you understand beats a dozen articles you've skimmed.
Use Claude to build it topic by topic, in your own words, at your depth.

**4. Design for crashes, not around them.**
"What happens when this fails?" is almost always the real question
underneath the surface one. If your answer is "it shouldn't fail," that's
not an answer.

---

*This guide was built from prep for an on-device AI systems design interview.
The architecture described in Part 1 directly informed the take-home submitted
at the start of this document.*




OpenAI

This round consists of two Coding problems + System Design. Both problems are built on common question types, but the constraints are quite unconventional—not exactly the same as the OpenAI original questions circulating online.

Coding First Problem:
Number Guessing, but with Delayed Feedback  
Problem Requirements: There's a hidden number. You submit guesses via an API, and the API tells you whether your guess is too high or too low. Unlike the classic version, the feedback here is delayed by one round. When you submit your guess for this round, the feedback you receive corresponds not to this submission, but to the previous round's submission. The request and response are offset by one beat.  
Analysis: The real difficulty lies in maintaining four states simultaneously: the current search range, what was guessed in the previous round, which submission the feedback received in this round actually corresponds to, and how to narrow the range for the next round while issuing a new guess. It's very easy to mix up the "just-guessed number" with the "just-returned comparison result" as if they belong to the same round. It's recommended to first draw a timeline to clarify the misalignment between requests and responses, then proceed to write the code.

Coding Second Problem:
Still a binary search-related follow-up  
Problem Requirements  

Analysis: This is very common in Senior Screens. If you get stuck on the state machine or boundary handling in the first question, the interviewer usually won't give you a chance for the follow-up. In terms of time allocation, it's more reliable to first deliver a delayed feedback version that can run and whose logic you can clearly explain, rather than jumping straight to finding the optimal number of queries from the start.

System Design:
Real-Time Device Power Consumption Monitoring and Control  


Problem Requirements: Design a platform to monitor power consumption data from multiple devices in real time, and adjust the devices' operating status or management methods based on usage conditions.  
Analysis: The core is to clearly explain it in three layers: the collection and transmission layer where devices continuously report data, the real-time judgment layer in the backend for ingestion and evaluation, and the execution layer for safely issuing control instructions after power consumption changes—especially covering how to handle boundary cases like jitter, false triggers, and device offline. The interviewer wants to see if you can clearly articulate the feedback loop from "observing" to "automatically adjusting device status."

## Projects
1.) Self-Hosted Inference Cluster
Build: Multi-node GPU cluster serving an open model with vLLM or SGLang, health checks, and a public latency report.
Why: Talk is cheap. A live cluster is the portfolio.

2.) Cost-Per-Token Dashboard
Build: TTFT, ITL, GPU util (DCGM) and $ per 1M tokens by model, tenant and route.
Why: Infra without FinOps is just expensive uptime.

3.) Queue-Based GPU Autoscaler
Build: KEDA (or equivalent) scaling on queue depth, with cold-start mitigation and spot fallback.
Why: Idle GPUs kill startups. Slow scale kills users.

4.) Continuous Batching Load Test
Build: Traffic generator that stresses continuous batching, KV cache limits and saturation points.
Why: You don’t know your serving stack until it breaks under load.

5.) Model Weight Delivery System
Build: Safetensors registry + sharded weights + CDN/lazy loading for fast node bring-up.
Why: Cold starts are often a storage problem pretending to be a compute problem.

6.) Multi-Model AI Gateway
Build: Routing, retries, fallbacks, rate limits and per-tenant token budgets across 2–3 serving backends.
Why: Production isn’t one endpoint. It’s a traffic policy.

7.) Quantized Serving Bakeoff
Build: Same model in FP16 vs AWQ/FP8; publish quality vs latency vs VRAM tradeoffs.
Why: Optimization without benchmarks is cosplay.

8.) Secure Multi-Tenant Inference Layer
Build: Tenant isolation, keyed access, sandboxed tool/exec paths, audit logs.
Why: One noisy neighbor (or leak) ends the B2B deal.

9.) Checkpointed Distributed Training Job
Build: Ray or Spój/Slurm job with FSDP/tensor parallel, fault injection, and resume-from-checkpoint.
Why: Training infra is judged on recovery not the happy path.

10.) Speculative Decoding Prototype
Build: Draft + target model path with prefix caching / chunked prefill; measure accepted-token rate.
Why: Speed wins are product features when you own the stack.

11.) GPU Partitioning Lab
Build: MIG (or equivalent) slices with fair scheduling, resource limits, and contention tests.
Why: Real clusters share silicon. You must prove fairness under pressure.

12.) Triton / Custom Kernel Path
Build: One hot path accelerated (attention, sampling or tokenizer-adjacent) with before/after metrics.
Why: Senior infra energy = knowing when frameworks aren’t enough.

13.) Observability Spine for Non-Determinism
Build: Traces for queue time, prefill, decode, cache hits, errors alerts on drift and cost spikes.
Why: You can’t page what you can’t see.

