
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

# Test several retrieval sizes.
TOP_K_VALUES = [1, 3, 5]

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
# LOAD CONCEPT DOCUMENTS
# ============================================================

documents = []


for file in sorted(
    KNOWLEDGE_DIR.glob("*.md")
):

    content = file.read_text(
        encoding="utf-8"
    )

    documents.append({

        "name": file.stem.lower(),

        "file": file,

        "content": content

    })


if not documents:

    raise RuntimeError(
        f"No concept documents found in {KNOWLEDGE_DIR}"
    )


print(
    f"Loaded {len(documents)} OKF concepts."
)


# ============================================================
# EXTRACT SEMANTIC CONTENT
# ============================================================

def extract_semantic_content(markdown):

    # Remove YAML frontmatter
    markdown = re.sub(
        r"^---.*?---\s*",
        "",
        markdown,
        flags=re.DOTALL
    )

    # Remove relationships because this is a
    # semantic retrieval baseline.
    #
    # This is IMPORTANT:
    #
    # The baseline must NOT get an advantage from
    # explicitly reading the OKF graph relationships.
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
# BUILD SEMANTIC CORPUS
# ============================================================

semantic_documents = []


for document in documents:

    semantic_documents.append({

        "name":
            document["name"],

        "content":
            extract_semantic_content(
                document["content"]
            )

    })


corpus = [

    document["content"]

    for document in semantic_documents

]


# ============================================================
# BUILD TF-IDF INDEX
# ============================================================

vectorizer = TfidfVectorizer(
    stop_words="english"
)


matrix = vectorizer.fit_transform(
    corpus
)


# ============================================================
# SEMANTIC RETRIEVAL
# ============================================================

def semantic_retrieve(
    question,
    top_k
):

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

        key=lambda item:
            item[1],

        reverse=True

    )


    return [

        {
            "name":
                item[0]["name"],

            "score":
                float(item[1])

        }

        for item in ranked[:top_k]

    ]


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
# RUN RAG BENCHMARK
# ============================================================

all_results = []


print()
print("=" * 80)
print("SEMANTIC RAG TOP-K BENCHMARK")
print("=" * 80)


for top_k in TOP_K_VALUES:

    print()
    print("=" * 80)

    print(
        f"TOP-K = {top_k}"
    )

    print("=" * 80)


    results = []


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


        # ----------------------------------------------------
        # Semantic retrieval
        # ----------------------------------------------------

        retrieved_documents = semantic_retrieve(

            question,

            top_k

        )


        retrieved_nodes = {

            item["name"]

            for item in retrieved_documents

        }


        print()
        print("RETRIEVED DOCUMENTS:")


        for item in retrieved_documents:

            print(

                f"  {item['name']}"
                f" | score="
                f"{item['score']:.3f}"

            )


        # ----------------------------------------------------
        # Calculate path recall
        #
        # Since semantic RAG has no graph traversal,
        # retrieval is the same at every "depth".
        # ----------------------------------------------------

        depth_results = []


        for depth in range(
            MAX_HOPS + 1
        ):

            recall = calculate_path_recall(

                expected_path,

                retrieved_nodes

            )


            target = (

                expected_path[-1]

                if expected_path

                else None

            )


            target_reached = (

                target in retrieved_nodes

                if target

                else False

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

            "start_node":
                start_node,

            "required_depth":
                required,

            "retrieved_documents":
                retrieved_documents,

            "depth_results":
                depth_results

        })


    all_results.append({

        "top_k":
            top_k,

        "results":
            results

    })


# ============================================================
# SUMMARY BY TOP-K
# ============================================================

print()
print("=" * 80)
print("SUMMARY BY TOP-K")
print("=" * 80)


for experiment in all_results:

    top_k = experiment[
        "top_k"
    ]

    results = experiment[
        "results"
    ]


    print()
    print(
        f"TOP-K = {top_k}"
    )


    # --------------------------------------------------------
    # Required-depth metrics
    # --------------------------------------------------------

    recall_values = []

    target_values = []


    for result in results:

        required = result[
            "required_depth"
        ]


        depth_result = next(

            item

            for item in result[
                "depth_results"
            ]

            if item[
                "depth"
            ] == required

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
        f"  Required-depth average path recall: "
        f"{average_recall:.2f}"
    )

    print(
        f"  Required-depth target reach rate: "
        f"{target_rate:.2f}"
    )


# ============================================================
# COMPARISON TABLE
# ============================================================

print()
print("=" * 80)
print("TOP-K COMPARISON")
print("=" * 80)

print()

print(
    f"{'Top-K':<10}"
    f"{'Path Recall':<20}"
    f"{'Target Reach':<20}"
)

print("-" * 50)


for experiment in all_results:

    top_k = experiment[
        "top_k"
    ]

    results = experiment[
        "results"
    ]


    recall_values = []

    target_values = []


    for result in results:

        required = result[
            "required_depth"
        ]


        depth_result = next(

            item

            for item in result[
                "depth_results"
            ]

            if item[
                "depth"
            ] == required

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

        f"{top_k:<10}"
        f"{average_recall:<20.2f}"
        f"{target_rate:<20.2f}"

    )


# ============================================================
# RESULTS BY QUESTION TYPE
# ============================================================

print()
print("=" * 80)
print("RESULTS BY QUESTION TYPE")
print("=" * 80)


for experiment in all_results:

    top_k = experiment[
        "top_k"
    ]

    results = experiment[
        "results"
    ]


    print()
    print(
        f"TOP-K = {top_k}"
    )


    question_types = sorted(

        set(

            result["type"]

            for result in results

        )

    )


    for question_type in question_types:

        subset = [

            result

            for result in results

            if result[
                "type"
            ] == question_type

        ]


        recall_values = []

        target_values = []


        for result in subset:

            required = result[
                "required_depth"
            ]


            depth_result = next(

                item

                for item in result[
                    "depth_results"
                ]

                if item[
                    "depth"
                ] == required

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
            f"  {question_type.upper()}"
        )

        print(
            f"    Path recall: "
            f"{average_recall:.2f}"
        )

        print(
            f"    Target reach: "
            f"{target_rate:.2f}"
        )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 80)
print("SEMANTIC RAG BENCHMARK COMPLETE")
print("=" * 80)
