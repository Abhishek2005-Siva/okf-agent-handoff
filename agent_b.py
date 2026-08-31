from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re


# ============================================================
# 1. ENVIRONMENT
# ============================================================

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")

if not api_key:
    raise RuntimeError(
        "NVIDIA_API_KEY is not set."
    )


# ============================================================
# 2. NVIDIA CLIENT
# ============================================================

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# 3. OKF KNOWLEDGE LOCATION
# ============================================================

KNOWLEDGE_DIR = Path("knowledge_graph_v2/concepts")


# ============================================================
# 4. LOAD DOCUMENTS
# ============================================================

def load_documents():

    documents = []

    if not KNOWLEDGE_DIR.exists():

        raise RuntimeError(
            f"Knowledge directory does not exist: "
            f"{KNOWLEDGE_DIR}"
        )

    for file in KNOWLEDGE_DIR.glob("*.md"):

        content = file.read_text(
            encoding="utf-8"
        )

        documents.append({
            "file": file,
            "content": content
        })

    return documents


documents = load_documents()


if not documents:

    raise RuntimeError(
        "No OKF concept documents found."
    )


print(
    f"Loaded {len(documents)} OKF concepts."
)


# ============================================================
# 5. DOCUMENT LOOKUP
# ============================================================

document_map = {}

for document in documents:

    document_map[
        document["file"].stem.lower()
    ] = document


# ============================================================
# 6. EXTRACT CONTENT
# ============================================================

def extract_content(markdown):

    """
    Remove YAML frontmatter and sections that should
    not influence semantic retrieval.
    """

    # Remove YAML frontmatter

    markdown = re.sub(
        r"^---.*?---\s*",
        "",
        markdown,
        flags=re.DOTALL
    )


    # Remove Relationships section

    markdown = re.sub(
        r"## Relationships.*?(?=\n## |\Z)",
        "",
        markdown,
        flags=re.DOTALL
    )


    # Remove Sources section

    markdown = re.sub(
        r"## Sources.*?(?=\n## |\Z)",
        "",
        markdown,
        flags=re.DOTALL
    )


    return markdown.strip()


# ============================================================
# 7. EXTRACT TYPED RELATIONSHIPS
# ============================================================

def extract_relationships(markdown):

    """
    Extract relationships such as:

    - **implemented_using** → [FastAPI](./fastapi.md)

    Returns:

    {
        "relation": "implemented_using",
        "target": "fastapi"
    }
    """

    relationships = []


    # Find Relationships section

    match = re.search(
        r"## Relationships(.*?)(?=\n## |\Z)",
        markdown,
        flags=re.DOTALL
    )


    if not match:

        return relationships


    section = match.group(1)


    # Match relationship lines

    pattern = (
        r"\*\*([^*]+)\*\*"
        r"\s*→\s*"
        r"\[[^\]]+\]"
        r"\(\./([^)]+)\)"
    )


    matches = re.findall(
        pattern,
        section
    )


    for relation, filename in matches:

        target = Path(
            filename
        ).stem.lower()


        relationships.append({

            "relation": relation.strip(),

            "target": target
        })


    return relationships


# ============================================================
# 8. ASK QUESTION
# ============================================================

question = input(
    "\nAsk Agent B a question: "
)


# ============================================================
# 9. CONTENT-ONLY SEMANTIC INDEX
# ============================================================

content_documents = []


for document in documents:

    content_documents.append({

        "file": document["file"],

        "content": extract_content(
            document["content"]
        )

    })


search_texts = [

    document["content"]

    for document in content_documents

]


vectorizer = TfidfVectorizer(
    stop_words="english"
)


matrix = vectorizer.fit_transform(
    search_texts
)


# ============================================================
# 10. INITIAL RETRIEVAL
# ============================================================

question_vector = vectorizer.transform(
    [question]
)


similarities = cosine_similarity(
    question_vector,
    matrix
)[0]


ranked = sorted(

    zip(
        content_documents,
        similarities
    ),

    key=lambda x: x[1],

    reverse=True

)


# IMPORTANT:
# Only ONE starting concept.

TOP_K = 1


initial_results = ranked[:TOP_K]


# ============================================================
# 11. DISPLAY INITIAL RETRIEVAL
# ============================================================

print(
    "\n--- INITIAL CONTENT RETRIEVAL ---"
)


for document, score in initial_results:

    print(
        f"{document['file'].name}"
        f" | relevance={score:.3f}"
    )


# ============================================================
# 12. GRAPH TRAVERSAL
# ============================================================

MAX_HOPS = 4


visited = set()


current_layer = []


layers = {}


# Every actual traversal edge is stored here.

traversal_edges = []


# -----------------------------------------
# Hop 0
# -----------------------------------------

for document, score in initial_results:

    name = document[
        "file"
    ].stem.lower()


    visited.add(name)

    current_layer.append(name)


layers[0] = current_layer.copy()


# -----------------------------------------
# Traverse graph
# -----------------------------------------

for hop in range(
    1,
    MAX_HOPS + 1
):

    next_layer = []


    for source_name in current_layer:

        source_document = document_map.get(
            source_name
        )


        if not source_document:

            continue


        relationships = extract_relationships(
            source_document["content"]
        )


        for edge in relationships:

            target_name = edge[
                "target"
            ]


            if target_name not in document_map:

                continue


            # Record the actual edge.

            traversal_edges.append({

                "hop": hop,

                "source": source_name,

                "relation": edge[
                    "relation"
                ],

                "target": target_name

            })


            # Don't visit a node twice.

            if target_name in visited:

                continue


            visited.add(
                target_name
            )


            next_layer.append(
                target_name
            )


    layers[hop] = next_layer


    current_layer = next_layer


# ============================================================
# 13. DISPLAY GRAPH
# ============================================================

print(
    "\n--- OKF GRAPH TRAVERSAL ---"
)


for hop, names in layers.items():

    print(
        f"\nHop {hop}:"
    )


    if not names:

        print(
            "  none"
        )

        continue


    for name in names:

        print(
            f"  {document_map[name]['file'].name}"
        )


# ============================================================
# 14. DISPLAY EXPLICIT PATH
# ============================================================

print(
    "\n--- EXPLICIT RELATIONSHIP PATH ---"
)


if not traversal_edges:

    print(
        "No relationships discovered."
    )

else:

    for edge in traversal_edges:

        print(
            f"Hop {edge['hop']}: "
            f"{edge['source']} "
            f"--[{edge['relation']}]--> "
            f"{edge['target']}"
        )


# ============================================================
# 15. BUILD PATH FOR AGENT B
# ============================================================

path_context = ""


for edge in traversal_edges:

    source_document = document_map[
        edge["source"]
    ]


    target_document = document_map[
        edge["target"]
    ]


    path_context += (
        f"{source_document['file'].name} "
        f"--[{edge['relation']}]--> "
        f"{target_document['file'].name}\n"
    )


if not path_context:

    path_context = "No relationship path discovered."


# ============================================================
# 16. BUILD KNOWLEDGE CONTEXT
# ============================================================

context_parts = []


for name in visited:

    document = document_map[
        name
    ]


    context_parts.append(
        f"""
SOURCE FILE: {document['file'].name}

{document['content']}
"""
    )


context = "\n\n".join(
    context_parts
)


# ============================================================
# 17. AGENT B
# ============================================================

response = client.chat.completions.create(

    model=MODEL,

    messages=[

        {

            "role": "system",

            "content": """
You are Agent B.

You consume knowledge transferred from another
agent through an Open Knowledge Format knowledge
bundle.

The retrieval system has already performed:

1. Semantic retrieval.
2. OKF relationship traversal.
3. Explicit relationship-path construction.

You must use the provided relationship path when
explaining connections between concepts.

You do NOT have access to:

- Agent A's conversation
- Agent A's reasoning
- Agent A's private memory
- Agent A's original research process

You ONLY have the supplied OKF knowledge and
relationship path.

Rules:

1. Do not invent facts.
2. Do not invent relationships.
3. Use the explicit relationship path when
   describing how concepts are connected.
4. If the requested relationship cannot be
   established from the supplied path, say so.
5. Distinguish direct retrieval from discovered
   concepts.
6. Keep the answer concise.

At the end provide:

Concepts used:
- filename.md
- filename.md

Relationship path:
- A --[relationship]--> B
"""
        },

        {

            "role": "user",

            "content": f"""
QUESTION:

{question}


============================================================
EXPLICIT OKF RELATIONSHIP PATH
============================================================

{path_context}


============================================================
RETRIEVED OKF KNOWLEDGE
============================================================

{context}

============================================================
END KNOWLEDGE
============================================================
"""
        }

    ],

    temperature=0.1,

    max_tokens=1800
)


# ============================================================
# 18. OUTPUT
# ============================================================

print(
    "\n--- AGENT B ANSWER ---\n"
)


print(
    response.choices[0].message.content
)