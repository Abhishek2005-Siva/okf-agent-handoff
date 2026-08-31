from pathlib import Path
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# CONFIGURATION
# ============================================================

KNOWLEDGE_DIR = Path(
    "knowledge_graph_v2/concepts"
)

QUESTIONS_FILE = Path(
    "benchmark_questions.json"
)

MAX_HOPS = 4


# ============================================================
# LOAD QUESTIONS
# ============================================================

with open(
    QUESTIONS_FILE,
    "r",
    encoding="utf-8"
) as f:

    questions = json.load(f)


print(
    f"Loaded {len(questions)} benchmark questions."
)


# ============================================================
# LOAD CONCEPTS
# ============================================================

documents = []


for file in KNOWLEDGE_DIR.glob("*.md"):

    content = file.read_text(
        encoding="utf-8"
    )

    documents.append({

        "name":
            file.stem.lower(),

        "file":
            file,

        "content":
            content

    })


if not documents:

    raise RuntimeError(
        "No OKF concept documents found."
    )


print(
    f"Loaded {len(documents)} OKF concepts."
)


document_map = {

    document["name"]:
        document

    for document in documents

}


# ============================================================
# EXTRACT SEMANTIC CONTENT
# ============================================================

def extract_content(markdown):

    # Remove YAML frontmatter

    markdown = re.sub(

        r"^---.*?---\s*",

        "",

        markdown,

        flags=re.DOTALL

    )


    # Remove relationships

    markdown = re.sub(

        r"## Relationships.*?(?=\n## |\Z)",

        "",

        markdown,

        flags=re.DOTALL

    )


    # Remove sources

    markdown = re.sub(

        r"## Sources.*?(?=\n## |\Z)",

        "",

        markdown,

        flags=re.DOTALL

    )


    return markdown.strip()


# ============================================================
# EXTRACT RELATIONSHIPS
# ============================================================

def extract_relationships(markdown):

    relationships = []


    match = re.search(

        r"## Relationships(.*?)(?=\n## |\Z)",

        markdown,

        flags=re.DOTALL

    )


    if not match:

        return relationships


    section = match.group(1)


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

        relationships.append({

            "relation":
                relation.strip(),

            "target":
                Path(filename).stem.lower()

        })


    return relationships


# ============================================================
# BUILD TF-IDF INDEX
# ============================================================

semantic_documents = []


for document in documents:

    semantic_documents.append({

        "name":
            document["name"],

        "content":
            extract_content(
                document["content"]
            )

    })


vectorizer = TfidfVectorizer(
    stop_words="english"
)


matrix = vectorizer.fit_transform(

    [
        document["content"]

        for document in semantic_documents
    ]

)


# ============================================================
# INITIAL RETRIEVAL
# ============================================================

def retrieve_start_node(question):

    question_vector = vectorizer.transform(
        [question]
    )


    scores = cosine_similarity(

        question_vector,

        matrix

    )[0]


    ranked = sorted(

        zip(
            semantic_documents,
            scores
        ),

        key=lambda x: x[1],

        reverse=True

    )


    return ranked[0][0]["name"]


# ============================================================
# GRAPH TRAVERSAL
# ============================================================

def traverse(
    start_node,
    max_hops
):

    visited = {
        start_node
    }

    current = [
        start_node
    ]


    for _ in range(max_hops):

        next_nodes = []


        for node in current:

            document = document_map[
                node
            ]


            relationships = (
                extract_relationships(
                    document["content"]
                )
            )


            for relationship in relationships:

                target = (
                    relationship["target"]
                )


                if target not in document_map:

                    continue


                if target in visited:

                    continue


                visited.add(
                    target
                )


                next_nodes.append(
                    target
                )


        current = next_nodes


        if not current:

            break


    return visited


# ============================================================
# EXPECTED PATH RECALL
# ============================================================

def calculate_recall(

    expected_path,

    retrieved

):

    if not expected_path:

        return 1.0


    found = 0


    for node in expected_path:

        if node.lower() in retrieved:

            found += 1

        else:

            break


    return (
        found /
        len(expected_path)
    )


# ============================================================
# REQUIRED DEPTH
# ============================================================

def required_depth(
    expected_path
):

    return max(
        len(expected_path) - 1,
        0
    )


# ============================================================
# RUN BENCHMARK
# ============================================================

results = []


print()
print("=" * 80)
print("OKF RETRIEVAL BENCHMARK")
print("=" * 80)


for question_data in questions:

    question = question_data[
        "question"
    ]


    expected_path = [

        node.lower()

        for node in question_data[
            "expected_path"
        ]

    ]


    start_node = question_data[
        "start_node"
    ].lower()


    required = required_depth(
        expected_path
    )


    print()
    print("-" * 80)

    print(
        f"QUESTION: {question}"
    )

    print(
        "EXPECTED: "
        + " → ".join(
            expected_path
        )
    )

    print(
        f"STARTING NODE: {start_node}"
    )

    print(
        f"REQUIRED DEPTH: {required}"
    )


    depth_results = []


    # --------------------------------------------------------
    # TEST EACH DEPTH
    # --------------------------------------------------------

    for depth in range(
        MAX_HOPS + 1
    ):

        retrieved = traverse(
            start_node,
            depth
        )


        recall = calculate_recall(

            expected_path,

            retrieved

        )


        target = (
            expected_path[-1]
        )


        target_reached = (
            target in retrieved
        )


        depth_results.append({

            "depth":
                depth,

            "recall":
                recall,

            "target_reached":
                target_reached

        })


        print(

            f"Depth {depth}: "

            f"recall={recall:.2f} "

            f"target="
            f"{'YES' if target_reached else 'NO'}"

        )


    results.append({

        "question":
            question,

        "type":
            question_data.get(
                "type",
                "unknown"
            ),

        "expected_path":
            expected_path,

        "required_depth":
            required,

        "depth_results":
            depth_results

    })


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)


for depth in range(
    MAX_HOPS + 1
):

    recall_values = []

    target_values = []


    for result in results:

        depth_result = next(

            item

            for item in result[
                "depth_results"
            ]

            if item[
                "depth"
            ] == depth

        )


        recall_values.append(

            depth_result[
                "recall"
            ]

        )


        target_values.append(

            1

            if depth_result[
                "target_reached"
            ]

            else 0

        )


    average_recall = (

        sum(recall_values)

        /

        len(recall_values)

    )


    target_rate = (

        sum(target_values)

        /

        len(target_values)

    )


    print()

    print(
        f"Depth {depth}"
    )

    print(
        f"  Average path recall: "
        f"{average_recall:.2f}"
    )

    print(
        f"  Target reach rate: "
        f"{target_rate:.2f}"
    )


# ============================================================
# RESULTS BY QUESTION TYPE
# ============================================================

print()
print("=" * 80)
print("RESULTS BY QUESTION TYPE")
print("=" * 80)


types = sorted(

    set(
        result["type"]
        for result in results
    )

)


for question_type in types:

    subset = [

        result

        for result in results

        if result[
            "type"
        ] == question_type

    ]


    print()
    print(
        f"{question_type.upper()}"
    )


    for depth in range(
        MAX_HOPS + 1
    ):

        recall_values = []

        target_values = []


        for result in subset:

            depth_result = next(

                item

                for item in result[
                    "depth_results"
                ]

                if item[
                    "depth"
                ] == depth

            )


            recall_values.append(

                depth_result[
                    "recall"
                ]

            )


            target_values.append(

                1

                if depth_result[
                    "target_reached"
                ]

                else 0

            )


        average_recall = (

            sum(recall_values)

            /

            len(recall_values)

        )


        target_rate = (

            sum(target_values)

            /

            len(target_values)

        )


        print(

            f"  Depth {depth}: "

            f"recall={average_recall:.2f}, "

            f"target={target_rate:.2f}"

        )


print()
print("=" * 80)
print("BENCHMARK COMPLETE")
print("=" * 80)
