# OKF Agent Handoff

**Live site:** [okf-agent-handoff.vercel.app](https://okf-agent-handoff.vercel.app) · **Source:** [`/web`](web)

> The live site is a Vite + React landing page that explains the project. The application itself runs locally, so follow the setup steps below to try it.


> **A research prototype exploring whether AI agents can hand off knowledge through an explicit, portable relationship graph rather than relying only on documents or semantic retrieval.**

## Overview

Modern AI systems commonly pass knowledge between agents through documents, summaries, embeddings, or retrieved context.

This project explores a different approach:

**Agent A converts research material into an Open Knowledge Format (OKF) knowledge bundle containing concepts, metadata, provenance, and explicit relationships. Agent B then consumes that bundle and performs multi-hop graph traversal to answer questions.**

The central idea is:

```text
                         RESEARCH MATERIAL
                                |
                                v
                         +--------------+
                         |   Agent A    |
                         | Knowledge    |
                         |   Builder    |
                         +------+-------+
                                |
                                v
                  +-----------------------------+
                  |       OKF KNOWLEDGE         |
                  |           BUNDLE            |
                  |                             |
                  | Concepts                    |
                  | Metadata                    |
                  | Relationships               |
                  | Provenance                  |
                  +--------------+--------------+
                                 |
                                 v
                         +--------------+
                         |   Agent B    |
                         | Knowledge    |
                         |   Consumer   |
                         +------+-------+
                                |
                             Question
                                |
                                v
                      Multi-hop traversal
                                |
                                v
                             Answer
```

---

# What Makes This Different?

This project is **not claiming to invent knowledge graphs or replace RAG**.

The focus is narrower:

> **Can explicit, typed relationships in a portable knowledge bundle improve multi-hop knowledge handoff between agents?**

Traditional semantic retrieval primarily asks:

```text
"What documents are similar to this question?"
```

This project additionally asks:

```text
"How are the concepts connected?"
```

For example:

```text
REST API
    |
    | implemented_using
    v
FastAPI
    |
    | written_in
    v
Python
    |
    | runs_on
    v
Runtime
    |
    | runs_on
    v
Operating System
```

A semantic retriever may retrieve several of these concepts.

However, retrieving the concepts does not necessarily establish the **ordered relationship path** between them.

The OKF representation explicitly stores those relationships.

This creates an important distinction:

### Traditional semantic retrieval

```text
Question
   |
   v
"What documents are similar?"
   |
   v
Relevant documents
```

### OKF-based knowledge retrieval

```text
Question
   |
   v
Relevant concept
   |
   v
Explicit relationship
   |
   v
Next concept
   |
   v
Explicit relationship
   |
   v
Next concept
   |
   v
Answer
```

The goal is therefore not simply to retrieve more information.

The goal is to make the **structure connecting the information explicit and traversable**.

---

# Architecture

```text
                         RESEARCH MATERIAL
                                |
                                v
                         +--------------+
                         |   Agent A    |
                         |   Builder    |
                         +------+-------+
                                |
                                v
                  +-----------------------------+
                  |       OKF KNOWLEDGE         |
                  |           BUNDLE            |
                  |                             |
                  | Concepts                    |
                  | Metadata                    |
                  | Relationships               |
                  | Provenance                  |
                  +--------------+--------------+
                                 |
                                 v
                         +--------------+
                         |   Agent B    |
                         |   Consumer   |
                         +------+-------+
                                |
                             Question
                                |
                                v
                      Multi-hop traversal
                                |
                                v
                             Answer
```

The system is divided into two primary agents.

---

# Agent A — Knowledge Builder

Agent A acts as the **knowledge builder**.

It receives research material and extracts structured concepts.

Each concept can contain:

* name
* type
* description
* tags
* content
* sources
* relationships

For example:

```markdown
## Relationships

- **implemented_using** → [FastAPI](./fastapi.md)
- **uses** → [HTTP](./http.md)
```

Agent A can also update an existing knowledge graph by adding relationships between existing concepts and newly discovered concepts.

This allows the knowledge base to grow incrementally rather than being recreated from scratch.

For example, after multiple runs, Agent A can maintain relationships such as:

```text
REST API --[implemented_using]--> FastAPI

FastAPI --[written_in]--> Python

Python --[runs_on]--> Runtime

Runtime --[runs_on]--> Operating System
```

The result is a structured knowledge artifact rather than a collection of disconnected summaries.

---

# Agent B — Knowledge Consumer

Agent B acts as the **knowledge consumer**.

Given a question, Agent B:

1. identifies the relevant starting concept
2. retrieves the corresponding OKF document
3. follows explicit relationships
4. traverses multiple hops through the graph
5. collects the relationship path
6. generates an answer grounded in the traversed concepts

For example:

### Question

> How does a REST API relate to an operating system?

### Graph traversal

```text
REST API
   |
   | implemented_using
   v
FastAPI
   |
   | written_in
   v
Python
   |
   | runs_on
   v
Runtime
   |
   | runs_on
   v
Operating System
```

Agent B can therefore explain the connection as an explicit chain rather than reconstructing it solely from independently retrieved documents.

---

# OKF Knowledge Representation

The example knowledge graph is stored under:

```text
knowledge_graph_v2/
```

with individual concept documents under:

```text
knowledge_graph_v2/concepts/
```

The current example contains concepts such as:

```text
REST API
FastAPI
Python
Runtime
Operating System
HTTP
TCP
IP
Web Application
Web Framework
Package Manager
Python Package
Dependency
Client
Server
```

Relationships are represented directly inside the concept documents.

Examples include:

```text
REST API --[implemented_using]--> FastAPI

FastAPI --[written_in]--> Python

Python --[runs_on]--> Runtime

Runtime --[runs_on]--> Operating System

REST API --[uses]--> HTTP

HTTP --[uses]--> TCP

TCP --[uses]--> IP
```

This makes the knowledge bundle both **human-readable and machine-traversable**.

The knowledge representation therefore carries more than raw content:

```text
concepts
+
relationships
+
provenance
+
structure
```

---

# Multi-Hop Retrieval

The project includes benchmark questions designed around known relationship paths.

## 1-Hop

```text
REST API
   ↓
FastAPI
```

## 2-Hop

```text
REST API
   ↓
FastAPI
   ↓
Python
```

## 3-Hop

```text
REST API
   ↓
FastAPI
   ↓
Python
   ↓
Runtime
```

## 4-Hop

```text
REST API
   ↓
FastAPI
   ↓
Python
   ↓
Runtime
   ↓
Operating System
```

The benchmark measures whether the required concepts and paths can be recovered as traversal depth increases.

---

# Why Multi-Hop Retrieval Matters

Consider the question:

> How does a REST API relate to an operating system?

The answer is not represented by a single concept.

The relevant chain is:

```text
REST API
    ↓
FastAPI
    ↓
Python
    ↓
Runtime
    ↓
Operating System
```

A system that only retrieves the REST API document has access to the starting point.

A system that retrieves REST API and Operating System documents may find both endpoints.

But neither necessarily means that the system has recovered the **relationship path** between them.

The OKF representation makes the path explicit:

```text
REST API
 --implemented_using-->
FastAPI
 --written_in-->
Python
 --runs_on-->
Runtime
 --runs_on-->
Operating System
```

This is the specific retrieval problem that the benchmark is designed to investigate.

---

# Evaluation

The project evaluates retrieval using several approaches.

## 1. Single-Document Baseline

The baseline retrieves only the most relevant document.

It does not explicitly traverse the knowledge graph.

This provides a simple reference point for comparison.

The current baseline demonstrates the expected limitation:

```text
Question
   ↓
Top document
   ↓
Answer
```

For direct questions, this can work well.

For multi-hop questions, however, a single document may contain only one part of the required path.

---

## 2. Semantic Retrieval

The semantic baseline evaluates Top-K retrieval:

```text
Top-1
Top-3
Top-5
```

The important distinction is between finding relevant documents and recovering an actual relationship path.

For example, a system could retrieve:

```text
REST API
FastAPI
Python
Runtime
Operating System
```

without explicitly recovering:

```text
REST API
    ↓
FastAPI
    ↓
Python
    ↓
Runtime
    ↓
Operating System
```

Retrieving the destination concept therefore does not necessarily mean that the system has discovered **how the concepts are connected**.

---

## 3. OKF Graph Traversal

The OKF system follows explicit relationships between concepts.

This allows the benchmark to measure multi-hop path recovery directly.

The retrieval process is:

```text
Question
   ↓
Starting concept
   ↓
Relationship traversal
   ↓
Next concept
   ↓
Relationship traversal
   ↓
Next concept
   ↓
...
   ↓
Target concept
```

---

# Evaluation Metrics

The benchmark distinguishes three different retrieval properties.

## Document Recall

**Did the system retrieve the concepts required by the expected path?**

This measures concept-level coverage.

---

## Target Reach

**Did the system retrieve the final target concept?**

This determines whether the destination of the expected relationship chain was reached.

---

## Path Recall

**Did the system recover the ordered concepts forming the expected relationship path?**

This is the most important metric for the multi-hop experiment.

For example, finding:

```text
REST API
Operating System
```

does not necessarily mean the system discovered:

```text
REST API → FastAPI → Python → Runtime → Operating System
```

Therefore, target discovery and path discovery are evaluated separately.

---

# Current Benchmark

The current curated benchmark contains questions covering:

* direct concept retrieval
* one-hop relationships
* two-hop relationships
* three-hop relationships
* four-hop relationships

Current questions include:

```text
What is a REST API?

What is FastAPI?

What is Python?

What framework can be used to implement a REST API?

What protocol does a REST API use?

What language is FastAPI written in?

How does a REST API relate to Python?

How does HTTP relate to IP?

How does a REST API relate to IP?

How does a Web Application relate to Python?

How does a REST API relate to an operating system?

How does a server relate to FastAPI?
```

The benchmark is intentionally small and curated at this stage.

Larger and more diverse evaluation datasets are planned.

---

# Current Results

The current OKF retrieval benchmark contains 12 questions and evaluates traversal from depth 0 through depth 4.

## Overall OKF Retrieval

| Traversal Depth | Average Path Recall | Target Reach Rate |
| --------------: | ------------------: | ----------------: |
|               0 |                0.51 |              0.25 |
|               1 |                0.77 |              0.50 |
|               2 |                0.90 |              0.67 |
|               3 |                0.98 |              0.92 |
|               4 |            **1.00** |          **1.00** |

The results show the expected behavior of explicit graph traversal:

* At depth 0, only the starting concept is available.
* As traversal depth increases, more of the expected path becomes recoverable.
* At depth 4, the current benchmark reaches all expected targets and recovers all expected paths.

These results are from the current small curated benchmark and should not be interpreted as a general performance claim.

---

# Baseline Comparison

The single-document semantic baseline currently produces:

```text
Average path recall: 0.51
Target reach rate: 0.42
```

The baseline behaves differently from graph traversal because increasing retrieval depth does not create additional relationship traversal.

For the single-document baseline, the same retrieved document remains the basis of evaluation regardless of the requested graph depth.

This gives a useful comparison:

| Approach                 | Main Mechanism                       | Multi-Hop Path Recovery                     |
| ------------------------ | ------------------------------------ | ------------------------------------------- |
| Single-document baseline | Retrieve one document                | Limited                                     |
| Semantic Top-K           | Retrieve multiple relevant documents | Does not inherently establish ordered paths |
| OKF traversal            | Follow explicit typed relationships  | Explicitly recovers paths                   |

The current results therefore motivate the research question rather than conclusively answering it.

---

# A Concrete Example

Consider:

> **How does a REST API relate to an operating system?**

The expected path is:

```text
REST API
   ↓
FastAPI
   ↓
Python
   ↓
Runtime
   ↓
Operating System
```

The OKF graph explicitly represents:

```text
REST API --[implemented_using]--> FastAPI

FastAPI --[written_in]--> Python

Python --[runs_on]--> Runtime

Runtime --[runs_on]--> Operating System
```

Agent B can then produce an explanation such as:

> A REST API can be implemented using FastAPI. FastAPI is written in Python, Python runs on a runtime, and that runtime runs on an operating system.

The important part is not merely that all five concepts exist.

The important part is that the **relationships connecting them are represented explicitly**.

---

# Project Structure

```text
.
├── README.md
├── .env.example
├── .gitignore
│
├── agent_a.py
├── agent_b.py
│
├── benchmark_questions.json
├── benchmark_baseline.py
├── benchmark_rag.py
├── benchmark_retrieval.py
│
├── research/
│   └── sources.md
│
└── knowledge_graph_v2/
    ├── index.md
    ├── log.md
    └── concepts/
        ├── rest-api.md
        ├── fastapi.md
        ├── python.md
        ├── runtime.md
        ├── operating-system.md
        ├── http.md
        ├── tcp.md
        ├── ip.md
        ├── web-application.md
        ├── web-framework.md
        ├── package-manager.md
        ├── python-package.md
        ├── dependency.md
        ├── client.md
        └── server.md
```

---

# Running the Project

## 1. Clone the repository

```bash
git clone https://github.com/Abhishek2005-Siva/okf-agent-handoff.git
cd okf-agent-handoff
```

## 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure the API key

Create `.env` from the example:

```bash
cp .env.example .env
```

Then add:

```text
NVIDIA_API_KEY=your_api_key_here
```

Do **not** commit `.env`.

---

# Running Agent A

```bash
python agent_a.py
```

Agent A processes the available research material and updates the OKF knowledge bundle.

The generated concepts and relationships are stored in:

```text
knowledge_graph_v2/
```

---

# Running Agent B

```bash
python agent_b.py
```

Agent B loads the knowledge graph and accepts a natural-language question.

Example:

```text
Ask Agent B a question:
How does a REST API relate to an operating system?
```

Agent B then performs multi-hop traversal and reports the relationship path used to generate its answer.

---

# Running the Benchmarks

## OKF Retrieval Benchmark

```bash
python benchmark_retrieval.py
```

This evaluates graph/path retrieval at depths 0 through 4.

---

## Single-Document Baseline

```bash
python benchmark_baseline.py
```

This evaluates retrieval without explicit graph traversal.

---

## Semantic RAG Benchmark

```bash
python benchmark_rag.py
```

This evaluates the semantic retrieval/RAG-style approach used as another comparison point.

---

# Why This Could Matter

As multi-agent systems become more complex, agents increasingly need to exchange knowledge rather than simply exchange messages.

A document-based handoff can communicate information.

A structured knowledge handoff can additionally communicate:

```text
concepts
+
relationships
+
provenance
+
structure
```

This project investigates whether that additional structure can make downstream multi-hop retrieval more reliable.

The longer-term goal is to explore **knowledge handoff as a first-class primitive for multi-agent systems**.

Instead of:

```text
Agent A
   |
   | "Here are some documents."
   v
Agent B
```

the handoff becomes:

```text
Agent A
   |
   | structured knowledge
   v
OKF Knowledge Bundle
   |
   | concepts + relationships + provenance
   v
Agent B
```

This separates the process of **building knowledge** from the process of **consuming and traversing knowledge**.

---

# Research Position

This project should be viewed as an **experimental investigation**, not a claim that explicit knowledge graphs are universally superior to RAG.

The research question is narrower:

> **Does representing agent knowledge as explicit, typed, portable relationships provide an advantage for multi-hop knowledge retrieval and handoff compared with semantic document retrieval alone?**

The benchmark and architecture are designed to investigate that question.

The current results provide an initial demonstration that the OKF representation can recover known multi-hop paths in the curated benchmark.

They do not yet establish general superiority over RAG or semantic retrieval.

---

# Limitations

This is currently a research prototype.

Important limitations include:

* The current benchmark is small and curated.
* Knowledge extraction depends on LLM-generated concepts and relationships.
* Relationship correctness is therefore dependent on extraction quality.
* The current semantic baseline uses TF-IDF rather than a production embedding/vector database.
* The benchmark primarily evaluates retrieval and path recovery rather than broad factual question answering.
* The current experiments do not establish that OKF universally outperforms RAG.
* Larger graphs and more diverse datasets are required for stronger conclusions.
* The current benchmark uses known expected paths, making it primarily an evaluation of controlled multi-hop retrieval rather than unconstrained graph reasoning.

---

# Future Work

Potential directions include:

* larger knowledge graphs
* larger multi-hop benchmarks
* automated relationship validation
* relationship confidence scores
* contradiction detection
* provenance-aware reasoning
* incremental graph updates
* graph versioning
* hybrid semantic retrieval + OKF traversal
* embedding-based semantic baselines
* agent-to-agent knowledge exchange
* decentralized knowledge handoff

A particularly interesting future architecture is:

```text
Question
   |
   v
Semantic Retrieval
   |
   v
Candidate Concepts
   |
   v
OKF Graph Traversal
   |
   v
Valid Relationship Path
   |
   v
Relevant Context
   |
   v
LLM
   |
   v
Answer
```

This would combine the strengths of semantic retrieval and explicit relationship traversal:

```text
Semantic retrieval
        +
Relationship-aware traversal
        =
Hybrid knowledge retrieval
```

---

# Research Roadmap

The project can evolve through several stages:

```text
Stage 1
---------
LLM
 |
 v
Concept extraction
 |
 v
OKF knowledge bundle


Stage 2
---------
OKF bundle
 |
 v
Explicit graph traversal
 |
 v
Multi-hop answer


Stage 3
---------
Semantic retrieval
 |
 v
Candidate concepts
 |
 v
OKF traversal
 |
 v
Validated relationship path
 |
 v
LLM answer


Stage 4
---------
Agent A
 |
 v
Portable knowledge bundle
 |
 +-------------------+
 |                   |
 v                   v
Agent B            Agent C
 |                   |
 v                   v
Queries             Queries
```

The longer-term direction is to investigate whether a standardized structured knowledge handoff can allow different agents to exchange and consume knowledge without requiring them to share the same internal memory or retrieval implementation.

---

# Core Idea in One Diagram

```text
                 AGENT A
                    |
                    | builds
                    v
        +-------------------------+
        |    OKF KNOWLEDGE        |
        |         BUNDLE          |
        |                         |
        | Concepts                |
        | Metadata                |
        | Relationships           |
        | Provenance              |
        +------------+------------+
                     |
                     | handoff
                     v
                 AGENT B
                     |
                     | traverses
                     v
          REST API → FastAPI
                     |
                     v
              FastAPI → Python
                     |
                     v
              Python → Runtime
                     |
                     v
          Runtime → Operating System
                     |
                     v
                   ANSWER
```

---

# License

This project is intended as an open research prototype.
