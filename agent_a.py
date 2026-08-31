from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import re


# ============================================================
# 1. LOAD ENVIRONMENT
# ============================================================

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")

if not api_key:
    raise RuntimeError(
        "NVIDIA_API_KEY is not set. "
        "Make sure it exists in your .env file."
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
# 3. RESEARCH TOPIC
# ============================================================

topic = """
Build a small knowledge base about modern web APIs and
Python web development.

The knowledge base MUST contain these concepts:

1. REST API
2. FastAPI
3. Python
4. Runtime
5. Operating System
6. HTTP
7. TCP
8. IP
9. Web Application
10. Web Framework
11. Package Manager
12. Python Package
13. Dependency
14. Client
15. Server

Create meaningful relationships between these concepts.

Important relationship chains should include:

REST API
→ FastAPI
→ Python
→ Runtime
→ Operating System

REST API
→ HTTP
→ TCP
→ IP

Web Application
→ Web Framework
→ FastAPI
→ Python

Python
→ Package Manager
→ Python Package
→ Dependency

Client
→ HTTP
→ REST API

Server
→ Web Application
→ Web Framework

The knowledge should describe the concepts accurately
and create explicit relationships between them.

Do not create random relationships merely to make the
graph larger. Relationships must be semantically meaningful.
"""


# ============================================================
# 4. PATHS
# ============================================================

BUNDLE_DIR = Path("knowledge_graph_v2")

CONCEPTS_DIR = BUNDLE_DIR / "concepts"

RESEARCH_FILE = Path(
    "research/sources.md"
)


# ============================================================
# 5. CREATE DIRECTORIES
# ============================================================

BUNDLE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CONCEPTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 6. HELPERS
# ============================================================

def safe_filename(name):
    """
    Convert a concept name into a safe filename.

    Examples:

        REST API
        -> rest-api

        Operating System
        -> operating-system

        HTTPS/TLS
        -> https-tls
    """

    return re.sub(
        r"[^a-z0-9]+",
        "-",
        name.lower()
    ).strip("-")


def normalize_name(name):
    """
    Normalize a concept name for comparison.
    """

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        name.lower()
    ).strip()


def clean_json_output(raw_output):
    """
    Remove accidental markdown code fences.
    """

    raw_output = raw_output.strip()

    if raw_output.startswith("```"):

        lines = raw_output.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw_output = "\n".join(lines)

    return raw_output.strip()


# ============================================================
# 7. LOAD EXISTING OKF KNOWLEDGE
# ============================================================

def load_existing_knowledge():

    documents = []

    for file in sorted(
        CONCEPTS_DIR.glob("*.md")
    ):

        content = file.read_text(
            encoding="utf-8"
        )

        documents.append({
            "filename": file.name,
            "name": file.stem,
            "content": content
        })

    return documents


existing_documents = load_existing_knowledge()


print(
    f"Existing OKF concepts: "
    f"{len(existing_documents)}"
)


# ============================================================
# 8. BUILD EXISTING KNOWLEDGE STRING
# ============================================================

existing_knowledge_parts = []

for document in existing_documents:

    existing_knowledge_parts.append(
        f"""
--- EXISTING CONCEPT ---
FILE: {document["filename"]}

{document["content"]}

--- END CONCEPT ---
"""
    )


existing_knowledge = "\n".join(
    existing_knowledge_parts
)


# ============================================================
# 9. LOAD RESEARCH
# ============================================================

if not RESEARCH_FILE.exists():

    raise FileNotFoundError(
        "research/sources.md was not found."
    )


research_material = RESEARCH_FILE.read_text(
    encoding="utf-8"
)


# ============================================================
# 10. AGENT A SYSTEM PROMPT
# ============================================================

system_prompt = """
You are Agent A, an incremental knowledge researcher.

You maintain an Open Knowledge Format (OKF) knowledge bundle.

Your job is to examine:

1. Existing OKF knowledge
2. New research material
3. The requested research topic

You must extend the knowledge graph rather than blindly
recreating it.

============================================================
CONCEPT RULES
============================================================

If a concept already exists:

- DO NOT recreate it.
- Use its exact existing name.
- You may propose new relationships for it.

If a concept does not exist:

- Create it in new_concepts.
- Give it a unique meaningful name.
- Do not create duplicates.

============================================================
RELATIONSHIP RULES
============================================================

Relationships are extremely important.

Every meaningful relationship must contain:

- source concept
- target concept
- relationship type

For example:

REST API
--[implemented_using]-->
FastAPI

FastAPI
--[written_in]-->
Python

Python
--[requires]-->
Runtime

Runtime
--[runs_on]-->
Operating System

Use precise relationship types whenever possible.

Good examples:

implemented_using
written_in
requires
runs_on
uses
depends_on
communicates_with
built_with
implements
exposes
served_by
uses_protocol

Avoid vague relationship types such as:

related_to

unless no more precise relationship is appropriate.

============================================================
DIRECTION
============================================================

Relationships are directed.

For example:

REST API
--[implemented_using]-->
FastAPI

is different from:

FastAPI
--[implements]-->
REST API

When both directions are meaningful, you may create both.

============================================================
NEW → NEW RELATIONSHIPS
============================================================

If two concepts are both being created in this response,
you MUST represent their relationship explicitly.

Example:

new_concepts:
    FastAPI
    Python

relationships:
    FastAPI --[written_in]--> Python

============================================================
NEW → EXISTING RELATIONSHIPS
============================================================

If a new concept connects to an existing concept,
represent that explicitly.

Example:

existing:
    HTTP

new:
    HTTP Method

relationship:

HTTP --[defines]--> HTTP Method

============================================================
EXISTING → NEW RELATIONSHIPS
============================================================

If an existing concept should point toward a newly created
concept, put that relationship in existing_relationships.

Example:

existing_relationships:
    HTTP
    --[defines]-->
    HTTP Method

============================================================
SOURCE RULES
============================================================

The sources field must contain only source numbers that
actually support the concept or relationship.

Never invent sources.

If the research material does not contain a source number
supporting a fact, use an empty list.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{
  "new_concepts": [
    {
      "name": "...",
      "type": "concept",
      "description": "...",
      "tags": ["..."],
      "content": "...",
      "sources": [1, 2]
    }
  ],

  "relationships": [
    {
      "source": "Exact concept name",
      "relation": "relationship_type",
      "target": "Exact concept name"
    }
  ],

  "existing_relationships": [
    {
      "source": "Exact existing concept name",
      "relation": "relationship_type",
      "target": "Exact existing or new concept name"
    }
  ]
}

============================================================
IMPORTANT
============================================================

The "source" and "target" names in relationships MUST
exactly match either:

1. An existing concept name
2. A new concept name in new_concepts

Do not invent concept names inside relationships.

Do not put relationships inside new_concepts.

Do not create duplicate concepts.

Return JSON only.
"""


# ============================================================
# 11. BUILD USER PROMPT
# ============================================================

user_prompt = f"""
The current research task is:

{topic}


============================================================
EXISTING OKF KNOWLEDGE
============================================================

{existing_knowledge}


============================================================
NEW RESEARCH MATERIAL
============================================================

{research_material}


============================================================
TASK
============================================================

Extend the existing OKF knowledge.

Create only genuinely new concepts.

Do not recreate concepts that already exist.

Create explicit directed relationships between concepts.

Pay particular attention to multi-hop chains.

The graph should support chains such as:

REST API
→ FastAPI
→ Python
→ Runtime
→ Operating System

REST API
→ HTTP
→ TCP
→ IP

Web Application
→ Web Framework
→ FastAPI
→ Python

Python
→ Package Manager
→ Python Package
→ Dependency

Client
→ HTTP
→ REST API

Server
→ Web Application
→ Web Framework
"""


# ============================================================
# 12. CALL AGENT A
# ============================================================

print()
print("Calling Agent A...")
print()


response = client.chat.completions.create(

    model=MODEL,

    messages=[
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ],

    temperature=0.1,

    max_tokens=7000
)


# ============================================================
# 13. PARSE AGENT A RESPONSE
# ============================================================

raw_output = response.choices[0].message.content

if not raw_output:
    raise RuntimeError(
        "Agent A returned an empty response."
    )


raw_output = clean_json_output(
    raw_output
)


print()
print("--- AGENT A OUTPUT ---")
print(raw_output)
print("--- END AGENT A OUTPUT ---")
print()


try:

    update = json.loads(
        raw_output
    )

except json.JSONDecodeError as e:

    print(
        "Agent A returned invalid JSON."
    )

    print(
        raw_output
    )

    raise e


# ============================================================
# 14. VALIDATE OUTPUT
# ============================================================

new_concepts = update.get(
    "new_concepts",
    []
)

relationships = update.get(
    "relationships",
    []
)

existing_relationships = update.get(
    "existing_relationships",
    []
)


# ============================================================
# 15. BUILD CONCEPT NAME MAP
# ============================================================

existing_name_map = {}

for document in existing_documents:

    match = re.search(
        r"^title:\s*(.+)$",
        document["content"],
        flags=re.MULTILINE
    )

    if match:

        title = match.group(1).strip()

        existing_name_map[
            normalize_name(title)
        ] = title

    else:

        existing_name_map[
            normalize_name(document["name"])
        ] = document["name"]


new_name_map = {}

for concept in new_concepts:

    name = concept["name"]

    new_name_map[
        normalize_name(name)
    ] = name


all_name_map = {}

all_name_map.update(
    existing_name_map
)

all_name_map.update(
    new_name_map
)


# ============================================================
# 16. VALIDATE RELATIONSHIPS
# ============================================================

def resolve_concept_name(name):

    normalized = normalize_name(
        name
    )

    return all_name_map.get(
        normalized
    )


valid_relationships = []

invalid_relationships = []


for relationship in relationships:

    source = relationship.get(
        "source"
    )

    relation = relationship.get(
        "relation"
    )

    target = relationship.get(
        "target"
    )


    if not source or not relation or not target:

        invalid_relationships.append(
            relationship
        )

        continue


    resolved_source = resolve_concept_name(
        source
    )

    resolved_target = resolve_concept_name(
        target
    )


    if not resolved_source or not resolved_target:

        invalid_relationships.append(
            relationship
        )

        continue


    valid_relationships.append({

        "source":
            resolved_source,

        "relation":
            relation.strip(),

        "target":
            resolved_target

    })


# ============================================================
# 17. VALIDATE EXISTING RELATIONSHIPS
# ============================================================

valid_existing_relationships = []


for relationship in existing_relationships:

    source = relationship.get(
        "source"
    )

    relation = relationship.get(
        "relation"
    )

    target = relationship.get(
        "target"
    )


    if not source or not relation or not target:

        invalid_relationships.append(
            relationship
        )

        continue


    resolved_source = resolve_concept_name(
        source
    )

    resolved_target = resolve_concept_name(
        target
    )


    if not resolved_source or not resolved_target:

        invalid_relationships.append(
            relationship
        )

        continue


    valid_existing_relationships.append({

        "source":
            resolved_source,

        "relation":
            relation.strip(),

        "target":
            resolved_target

    })


# ============================================================
# 18. CREATE NEW CONCEPT FILES
# ============================================================

created_count = 0


for concept in new_concepts:

    name = concept["name"]

    filename = safe_filename(
        name
    )


    output_file = (
        CONCEPTS_DIR /
        f"{filename}.md"
    )


    # --------------------------------------------------------
    # Prevent accidental overwriting of existing concept
    # --------------------------------------------------------

    if output_file.exists():

        print(
            f"Skipping existing file: "
            f"{output_file}"
        )

        continue


    tags = concept.get(
        "tags",
        []
    )


    if tags:

        tags_text = ", ".join(
            str(tag)
            for tag in tags
        )

    else:

        tags_text = ""


    content = f"""---
type: {concept.get("type", "concept")}
title: {name}
description: {concept.get("description", "")}
tags: [{tags_text}]
---

# {name}

{concept.get("content", "")}

## Relationships

"""


    # --------------------------------------------------------
    # Add relationships originating from this new concept
    # --------------------------------------------------------

    concept_relationships = [

        relationship

        for relationship in valid_relationships

        if normalize_name(
            relationship["source"]
        )
        ==
        normalize_name(name)

    ]


    for relationship in concept_relationships:

        target = relationship[
            "target"
        ]

        relation = relationship[
            "relation"
        ]

        target_file = safe_filename(
            target
        )


        content += (
            f"- **{relation}** → "
            f"[{target}](./{target_file}.md)\n"
        )


    # --------------------------------------------------------
    # Add sources
    # --------------------------------------------------------

    content += "\n## Sources\n\n"


    sources = concept.get(
        "sources",
        []
    )


    if sources:

        for source in sources:

            content += (
                f"- Source {source}\n"
            )

    else:

        content += "- None\n"


    output_file.write_text(
        content,
        encoding="utf-8"
    )


    created_count += 1


    print(
        f"Created: {output_file}"
    )


# ============================================================
# 19. ADD RELATIONSHIPS TO EXISTING CONCEPTS
# ============================================================

relationship_update_count = 0


def add_relationship_to_file(
    source_name,
    relation,
    target_name
):

    source_file = (
        CONCEPTS_DIR /
        f"{safe_filename(source_name)}.md"
    )


    if not source_file.exists():

        print(
            f"Warning: source concept does not exist: "
            f"{source_name}"
        )

        return False


    content = source_file.read_text(
        encoding="utf-8"
    )


    target_file = safe_filename(
        target_name
    )


    relationship_line = (
        f"- **{relation}** → "
        f"[{target_name}](./{target_file}.md)"
    )


    # --------------------------------------------------------
    # Already exists
    # --------------------------------------------------------

    if relationship_line in content:

        return False


    # --------------------------------------------------------
    # Ensure Relationships section exists
    # --------------------------------------------------------

    if "## Relationships" not in content:

        marker = "\n## Sources"


        if marker in content:

            content = content.replace(

                marker,

                "\n## Relationships\n\n"
                + relationship_line
                + "\n"
                + marker,

                1

            )

        else:

            content += (
                "\n## Relationships\n\n"
                + relationship_line
                + "\n"
            )


    else:

        before, after = content.split(
            "## Relationships",
            1
        )


        # Find next section

        next_section = re.search(
            r"\n## ",
            after
        )


        if next_section:

            relationships_text = (
                after[
                    :next_section.start()
                ]
            )

            remainder = (
                after[
                    next_section.start():
                ]
            )

        else:

            relationships_text = after

            remainder = ""


        relationships_text = (
            relationships_text.rstrip()
            + "\n"
            + relationship_line
            + "\n"
        )


        content = (
            before
            + "## Relationships"
            + relationships_text
            + remainder
        )


    source_file.write_text(
        content,
        encoding="utf-8"
    )


    return True


# ============================================================
# 20. APPLY ALL RELATIONSHIPS
# ============================================================

all_relationships = (
    valid_relationships
    +
    valid_existing_relationships
)


for relationship in all_relationships:

    source = relationship[
        "source"
    ]

    relation = relationship[
        "relation"
    ]

    target = relationship[
        "target"
    ]


    changed = add_relationship_to_file(

        source,

        relation,

        target

    )


    if changed:

        relationship_update_count += 1

        print(
            f"Relationship: "
            f"{source} "
            f"--[{relation}]--> "
            f"{target}"
        )


# ============================================================
# 21. UPDATE INDEX
# ============================================================

index_file = BUNDLE_DIR / "index.md"


if index_file.exists():

    index_content = index_file.read_text(
        encoding="utf-8"
    )

else:

    index_content = """---
type: Index
title: Knowledge Base
description: Agent-generated OKF knowledge.
---

# Knowledge Base

## Concepts

"""


# Get every concept currently in the graph

existing_files = sorted(
    CONCEPTS_DIR.glob("*.md")
)


existing_index_links = set(
    re.findall(
        r"- \[\[concepts/([^]]+)\]\]",
        index_content
    )
)


for file in existing_files:

    filename = file.stem

    link = (
        f"- [[concepts/{filename}]]"
    )


    if filename not in existing_index_links:

        index_content += (
            link + "\n"
        )


index_file.write_text(
    index_content,
    encoding="utf-8"
)


# ============================================================
# 22. UPDATE LOG
# ============================================================

log_file = BUNDLE_DIR / "log.md"


if log_file.exists():

    log_content = log_file.read_text(
        encoding="utf-8"
    )

else:

    log_content = """---
type: Log
title: Knowledge Generation Log
---

# Knowledge Generation Log
"""


log_content += f"""

## Knowledge Update

Research topic:

{topic}

New concepts created:
{created_count}

Relationships processed:
{len(all_relationships)}

Relationships added:
{relationship_update_count}

Invalid relationships ignored:
{len(invalid_relationships)}
"""


log_file.write_text(
    log_content,
    encoding="utf-8"
)


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

print()
print("=" * 60)
print("OKF KNOWLEDGE UPDATE COMPLETE")
print("=" * 60)

print(
    f"Existing concepts before update: "
    f"{len(existing_documents)}"
)

print(
    f"New concepts created: "
    f"{created_count}"
)

print(
    f"Relationships processed: "
    f"{len(all_relationships)}"
)

print(
    f"Relationships added: "
    f"{relationship_update_count}"
)

print(
    f"Invalid relationships ignored: "
    f"{len(invalid_relationships)}"
)

print(
    f"Total concept files now: "
    f"{len(list(CONCEPTS_DIR.glob('*.md')))}"
)

print("=" * 60)