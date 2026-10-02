"""
OKF Agent Handoff — interactive explorer
Run:  streamlit run streamlit_app/app.py

Loads the OKF knowledge bundle in knowledge_graph_v2/ and lets you explore it the way
Agent B does: pick a starting concept, follow typed relationships hop by hop, and see
which concepts and paths become reachable. Needs no API key. Optionally, paste an OpenAI or
NVIDIA (free) key to have an LLM answer from the reached concepts, like Agent B does.
"""
import json
import re
from collections import deque
from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = ROOT / "knowledge_graph_v2" / "concepts"
QUESTIONS_FILE = ROOT / "benchmark_questions.json"
MAX_HOPS = 4
ACCENT = "#6d5ef5"

# Both providers speak the OpenAI API; NVIDIA's free hosted models just use another base URL.
PROVIDERS = {
    "NVIDIA (free)": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-nano-3-30b-a3b",
                   "mistralai/mistral-large-2-instruct"],
        "hint": "nvapi-…  (free key at build.nvidia.com)",
    },
    "OpenAI": {
        "base_url": None,
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
        "hint": "sk-…",
    },
}

st.set_page_config(page_title="OKF Agent Handoff", page_icon="🕸️", layout="wide")


# ── Loading and parsing (same rules as benchmark_retrieval.py) ──────────────────────

def _frontmatter(markdown: str) -> dict:
    match = re.match(r"^---\s*(.*?)\s*---", markdown, flags=re.DOTALL)
    meta = {}
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    return meta


def _body(markdown: str) -> str:
    """Concept text without frontmatter, relationships and sources."""
    markdown = re.sub(r"^---.*?---\s*", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"## Relationships.*?(?=\n## |\Z)", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"## Sources.*?(?=\n## |\Z)", "", markdown, flags=re.DOTALL)
    return markdown.strip()


def _relationships(markdown: str) -> list[tuple[str, str]]:
    match = re.search(r"## Relationships(.*?)(?=\n## |\Z)", markdown, flags=re.DOTALL)
    if not match:
        return []
    pattern = r"\*\*([^*]+)\*\*\s*→\s*\[[^\]]+\]\(\./([^)]+)\)"
    return [
        (relation.strip(), Path(filename).stem.lower())
        for relation, filename in re.findall(pattern, match.group(1))
    ]


@st.cache_data
def load_bundle() -> dict:
    concepts = {}
    for file in sorted(CONCEPTS_DIR.glob("*.md")):
        text = file.read_text(encoding="utf-8")
        name = file.stem.lower()
        meta = _frontmatter(text)
        concepts[name] = {
            "title": meta.get("title", name),
            "description": meta.get("description", ""),
            "body": _body(text),
            "edges": _relationships(text),
        }
    for concept in concepts.values():
        concept["edges"] = [(r, t) for r, t in concept["edges"] if t in concepts]
    return concepts


@st.cache_resource
def tfidf_index(names: tuple, texts: tuple):
    vectorizer = TfidfVectorizer(stop_words="english")
    return vectorizer, vectorizer.fit_transform(texts)


def pick_start(question: str, concepts: dict) -> str:
    names = tuple(concepts)
    vectorizer, matrix = tfidf_index(names, tuple(concepts[n]["body"] for n in names))
    scores = cosine_similarity(vectorizer.transform([question]), matrix)[0]
    return names[int(scores.argmax())]


# ── Graph logic ───────────────────────────────────────────────────────────────────

def traverse(concepts: dict, start: str, hops: int) -> dict[str, int]:
    """Breadth-first walk along outgoing relationships. Returns concept -> hop level."""
    level = {start: 0}
    frontier = [start]
    for hop in range(1, hops + 1):
        nxt = []
        for node in frontier:
            for _, target in concepts[node]["edges"]:
                if target not in level:
                    level[target] = hop
                    nxt.append(target)
        frontier = nxt
        if not frontier:
            break
    return level


def shortest_path(concepts: dict, source: str, target: str, undirected: bool):
    adjacency = {n: [] for n in concepts}
    for node, concept in concepts.items():
        for relation, tgt in concept["edges"]:
            adjacency[node].append((tgt, relation, "→"))
            if undirected:
                adjacency[tgt].append((node, relation, "←"))
    queue, seen = deque([(source, [])]), {source}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for nxt, relation, arrow in adjacency[node]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [(node, relation, arrow, nxt)]))
    return None


def to_dot(concepts: dict, highlight: dict[str, int] | None = None, path_edges=None) -> str:
    path_edges = {(a, b) for a, _, _, b in path_edges or []} | {(b, a) for a, _, _, b in path_edges or []}
    lines = [
        "digraph G {",
        'rankdir=LR; bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#8b93a7", fillcolor="#f3f4f8", fontcolor="#1a1d24"];',
        'edge [fontname="Helvetica", fontsize=9, color="#8b93a7", fontcolor="#5b6270"];',
    ]
    for name, concept in concepts.items():
        extra = ""
        if highlight is not None and name in highlight:
            extra = f', fillcolor="{ACCENT}", fontcolor="white", color="{ACCENT}"'
        elif highlight is not None:
            extra = ', fillcolor="#e9eaf0", fontcolor="#9aa1b3"'
        lines.append(f'"{name}" [label="{concept["title"]}"{extra}];')
    for name, concept in concepts.items():
        for relation, target in concept["edges"]:
            on_path = (name, target) in path_edges
            style = f', color="{ACCENT}", penwidth=2.2, fontcolor="{ACCENT}"' if on_path else ""
            lines.append(f'"{name}" -> "{target}" [label="{relation}"{style}];')
    lines.append("}")
    return "\n".join(lines)


def path_text(concepts: dict, path, source: str) -> str:
    parts = [concepts[source]["title"]]
    for _, relation, arrow, nxt in path:
        parts.append(f"—{relation}{arrow}")
        parts.append(concepts[nxt]["title"])
    return " ".join(parts)


def ask_llm(concepts: dict, level: dict[str, int], question: str, start: str) -> str:
    """Answer from the reached concepts and the typed relationships among them (Agent B style)."""
    from openai import OpenAI

    cfg = PROVIDERS[st.session_state.get("llm_provider", "NVIDIA (free)")]
    lines = [f"Question: {question}", f"Starting concept: {concepts[start]['title']}", "", "Concepts reached:"]
    for name, hop in sorted(level.items(), key=lambda kv: kv[1]):
        lines.append(f"- [{hop} hop] {concepts[name]['title']}: {concepts[name]['description']}")
    lines += ["", "Relationships among them:"]
    for name in level:
        for relation, target in concepts[name]["edges"]:
            if target in level:
                lines.append(f"- {concepts[name]['title']} --{relation}--> {concepts[target]['title']}")
    lines += ["", "Answer using only the concepts and relationships above. State the relationship "
              "path you followed. If the answer is not in them, say so."]
    client = OpenAI(api_key=st.session_state["llm_key"], base_url=cfg["base_url"])
    response = client.chat.completions.create(
        model=st.session_state["llm_model"],
        messages=[{"role": "user", "content": "\n".join(lines)}],
        temperature=0,
        max_tokens=600,
    )
    return (response.choices[0].message.content or "").strip()


# ── Pages ─────────────────────────────────────────────────────────────────────────

def tab_explore(concepts: dict) -> None:
    st.subheader("Traverse the graph")
    st.caption("Agent B's retrieval: start at a concept, follow typed relationships hop by hop.")
    left, right = st.columns([1, 1])
    question = left.text_input("Ask a question (optional)", placeholder="What framework can implement a REST API?")
    default = pick_start(question, concepts) if question.strip() else "rest-api"
    names = list(concepts)
    start = right.selectbox(
        "Starting concept",
        names,
        index=names.index(default) if default in names else 0,
        format_func=lambda n: concepts[n]["title"],
        key=f"start-{default}",
    )
    if question.strip():
        left.caption(f"Best TF-IDF match for your question: **{concepts[default]['title']}**")
    hops = st.slider("Hops to follow", 0, MAX_HOPS, 2)
    level = traverse(concepts, start, hops)
    st.graphviz_chart(to_dot(concepts, highlight=level), width="stretch")
    rows = [
        {"hop": hop, "concept": concepts[n]["title"], "description": concepts[n]["description"]}
        for n, hop in sorted(level.items(), key=lambda kv: kv[1])
    ]
    st.markdown(f"**{len(level)} of {len(concepts)} concepts reachable within {hops} hop(s)**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.markdown("**Answer with an LLM**")
    if not question.strip():
        st.caption("Type a question above, then answer it from the concepts reached.")
    elif not st.session_state.get("llm_key"):
        st.caption("Paste an OpenAI or NVIDIA (free) key in the sidebar to enable this.")
    elif st.button("Answer from these concepts"):
        with st.spinner("Asking the model…"):
            try:
                st.markdown(ask_llm(concepts, level, question, start))
            except Exception as exc:  # noqa: BLE001
                st.error(f"LLM error: {exc}")


def tab_path(concepts: dict) -> None:
    st.subheader("Find a relationship path")
    st.caption("The ordered path between two concepts, which similarity search alone does not give you.")
    names = list(concepts)
    c1, c2, c3 = st.columns([2, 2, 1])
    source = c1.selectbox("From", names, index=names.index("rest-api") if "rest-api" in names else 0,
                          format_func=lambda n: concepts[n]["title"])
    target = c2.selectbox("To", names, index=names.index("operating-system") if "operating-system" in names else 0,
                          format_func=lambda n: concepts[n]["title"])
    undirected = c3.toggle("Ignore direction", value=False)
    path = shortest_path(concepts, source, target, undirected)
    if path is None:
        st.warning("No path along the stated relationships. Try ‘Ignore direction’.")
        st.graphviz_chart(to_dot(concepts), width="stretch")
        return
    st.success(f"{len(path)} hop(s): " + path_text(concepts, path, source))
    on_path = {source} | {nxt for *_, nxt in path}
    st.graphviz_chart(to_dot(concepts, highlight={n: 0 for n in on_path}, path_edges=path),
                      width="stretch")


def tab_concepts(concepts: dict) -> None:
    st.subheader("Concept browser")
    names = list(concepts)
    name = st.selectbox("Concept", names, format_func=lambda n: concepts[n]["title"])
    concept = concepts[name]
    st.markdown(f"### {concept['title']}")
    st.caption(concept["description"])
    st.markdown(concept["body"].split("\n", 1)[1] if concept["body"].startswith("#") else concept["body"])
    out_col, in_col = st.columns(2)
    out_col.markdown("**Outgoing relationships**")
    for relation, target in concept["edges"]:
        out_col.markdown(f"- *{relation}* → {concepts[target]['title']}")
    if not concept["edges"]:
        out_col.caption("None")
    in_col.markdown("**Incoming relationships**")
    incoming = [(n, r) for n, c in concepts.items() for r, t in c["edges"] if t == name]
    for source, relation in incoming:
        in_col.markdown(f"- {concepts[source]['title']} → *{relation}*")
    if not incoming:
        in_col.caption("None")


def tab_benchmark(concepts: dict) -> None:
    st.subheader("Path recall by traversal depth")
    st.caption("Each benchmark question has a start concept and an expected path. "
               "Recall is the share of the expected path recovered (in order) at each depth.")
    if not QUESTIONS_FILE.exists():
        st.info("benchmark_questions.json not found.")
        return
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    summary, detail = [], []
    for depth in range(MAX_HOPS + 1):
        recalls, reached = [], []
        for q in questions:
            expected = [n.lower() for n in q["expected_path"]]
            got = traverse(concepts, q["start_node"].lower(), depth)
            found = 0
            for node in expected:
                if node in got:
                    found += 1
                else:
                    break
            recalls.append(found / len(expected))
            reached.append(expected[-1] in got)
        summary.append({"depth": depth,
                        "average path recall": round(sum(recalls) / len(recalls), 2),
                        "target reach rate": round(sum(reached) / len(reached), 2)})
    df = pd.DataFrame(summary).set_index("depth")
    c1, c2 = st.columns([1, 1])
    c1.dataframe(df, width="stretch")
    c2.line_chart(df)
    st.caption(f"{len(questions)} curated questions. A small benchmark, not a general performance claim.")
    with st.expander("Questions"):
        st.dataframe(pd.DataFrame([{"type": q.get("type", ""), "question": q["question"],
                                    "expected path": " → ".join(q["expected_path"])} for q in questions]),
                     hide_index=True, width="stretch")


def main() -> None:
    with st.sidebar:
        st.title("🕸️ OKF Agent Handoff")
        st.write("Can AI agents hand off knowledge through an explicit, portable relationship graph?")
        st.caption("Agent A builds an OKF bundle. Agent B walks it. Exploring needs no key; "
                   "an LLM answer is optional.")
        provider = st.selectbox("LLM provider", list(PROVIDERS), key="llm_provider")
        st.text_input("API key (optional)", type="password", key="llm_key",
                      placeholder=PROVIDERS[provider]["hint"],
                      help="Only used for the optional LLM answer. Kept in this session only.")
        st.selectbox("Model", PROVIDERS[provider]["models"], key="llm_model")
        st.divider()
        st.markdown("[Source on GitHub](https://github.com/Abhishek2005-Siva/okf-agent-handoff)")
        st.markdown("[Landing page](https://okf-agent-handoff.vercel.app)")

    if not CONCEPTS_DIR.exists() or not any(CONCEPTS_DIR.glob("*.md")):
        st.error("No OKF concepts found in knowledge_graph_v2/concepts.")
        return
    concepts = load_bundle()

    st.title("OKF knowledge bundle explorer")
    st.caption(f"{len(concepts)} concepts · {sum(len(c['edges']) for c in concepts.values())} typed relationships")
    explore, path, browse, bench = st.tabs(["Traverse", "Find a path", "Concepts", "Benchmark"])
    with explore:
        tab_explore(concepts)
    with path:
        tab_path(concepts)
    with browse:
        tab_concepts(concepts)
    with bench:
        tab_benchmark(concepts)


main()
