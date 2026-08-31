
from pathlib import Path
import json
import re


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

if not QUESTIONS_FILE.exists():
    raise FileNotFoundError(
        f"Questions file not found: {QUESTIONS_FILE}"
    )


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


for file in sorted(
    KNOWLEDGE_DIR.glob("*.md")
):

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
        f"No concept documents found in {KNOWLEDGE_DIR}"
    )


print(
    f"Loaded {len(documents)} OKF concepts."
)


# ============================================================
# DOCUMENT MAP
# ============================================================

document_map = {

    document["name"]:
        document

    for document in documents

}


# ============================================================
# REMOVE YAML FRONTMATTER
# ============================================================

def remove_frontmatter(markdown):

    return re.sub(

        r"^---.*?---\s*",

        "",

        markdown,

        flags=re.DOTALL

    ).strip()


# ============================================================
# REMOVE RELATIONSHIPS
# ============================================================

def remove_relationships(markdown):

    return re.sub(

        r"## Relationships.*?(?=\n## |\Z)",

        "",

        markdown,

        flags=re.DOTALL

    ).strip()


# ============================================================
# REMOVE SOURCES
# ============================================================

def remove_sources(markdown):

    return re.sub(

        r"## Sources.*?(?=\n## |\Z)",

        "",

        markdown,

        flags=re.DOTALL

    ).strip()


# ============================================================
# EXTRACT SEMANTIC CONTENT
# ============================================================

def extract_semantic_content(markdown):

    markdown = remove_frontmatter(
        markdown
    )

    markdown = remove_relationships(
        markdown
    )

    markdown = remove_sources(
        markdown
    )

    return markdown.strip()


# ============================================================
# BASELINE RETRIEVAL
# ============================================================

def baseline_retrieve(
    start_node,
    depth
):
    """
    Baseline retrieval.

    IMPORTANT:

    This baseline intentionally does NOT follow
    OKF relationships.

    Regardless of requested depth, the baseline
    only retrieves the starting concept document.

    This represents a simple single-document
    retrieval system.
    """

    if start_node not in document_map:

        return set()

    return {
        start_node
    }


# ============================================================
# PATH RECALL
# ============================================================

def calculate_path_recall(
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
# TARGET REACHED
# ============================================================

def target_reached(
    expected_path,
    retrieved
):

    if not expected_path:

        return False


    target = (
        expected_path[-1]
        .lower()
    )


    return target in retrieved


# ============================================================
# RUN BENCHMARK
# ============================================================

results = []


print()
print("=" * 80)
print("BASELINE SINGLE-DOCUMENT RETRIEVAL BENCHMARK")
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
        +
        " → ".join(
            expected_path
        )
    )

    print(
        f"STARTING NODE: {start_node}"
    )

    print(
        f"REQUIRED DEPTH: {required}"
    )


    # --------------------------------------------------------
    # Verify starting node
    # --------------------------------------------------------

    if start_node not in document_map:

        print(
            f"ERROR: Starting node "
            f"'{start_node}' not found."
        )

        continue


    # --------------------------------------------------------
    # Test every depth
    # --------------------------------------------------------

    depth_results = []


    for depth in range(
        MAX_HOPS + 1
    ):

        retrieved = baseline_retrieve(

            start_node,

            depth

        )


        recall = calculate_path_recall(

            expected_path,

            retrieved

        )


        reached = target_reached(

            expected_path,

            retrieved

        )


        depth_results.append({

            "depth":
                depth,

            "recall":
                recall,

            "target_reached":
                reached

        })


        print(

            f"Depth {depth}: "

            f"recall={recall:.2f} "

            f"target="

            f"{'YES' if reached else 'NO'}"

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
print("BASELINE SUMMARY")
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


    if not recall_values:

        continue


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
        question_type.upper()
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


        if not recall_values:

            continue


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


# ============================================================
# FINAL COMPARISON-FRIENDLY TABLE
# ============================================================

print()
print("=" * 80)
print("DEPTH COMPARISON")
print("=" * 80)

print()

print(
    f"{'Depth':<10}"
    f"{'Avg Recall':<15}"
    f"{'Target Reach':<15}"
)

print("-" * 40)


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


    if not recall_values:

        continue


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

        f"{depth:<10}"
        f"{average_recall:<15.2f}"
        f"{target_rate:<15.2f}"

    )


print()
print("=" * 80)
print("BENCHMARK COMPLETE")
print("=" * 80)
