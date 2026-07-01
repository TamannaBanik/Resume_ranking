import random

jd_data = {
    "role_title": "Senior AI Engineer",
    "min_years_experience": 5,
    "max_years_experience": 9,
    "years_experience_flexible": True,
    "target_locations": ["Pune", "Noida"],
    "target_country": "India",
    "relocation_provided": True,
    "core_skills_required": [
        "production experience with embeddings-based retrieval systems",
        "production experience with vector databases or hybrid search infrastructure",
        "strong Python",
        "hands-on experience designing evaluation frameworks for ranking systems",
    ],
    "work_ethics_and_behavior": [
        "scrappy product-engineering attitude",
        "comfortable with two things that sound contradictory: deep technical depth in modern ML systems and scrappy product-engineering attitude",
    ],
    "preferred_past_projects": [
        "candidate-JD matching at scale",
        "recruiter-experience PM collaboration",
    ],
    "disqualified_titles": ["Researcher", "Architect"],
    "disqualified_backgrounds": [
        "academic labs",
        "research-only roles",
        "closed-source proprietary systems for 5+ years without external validation",
    ],
}

current_title_keywords = [
    "AI",
    "Artificial Intelligence",
    "Machine Learning",
    "ML",
    "NLP",
    "Recommendation Systems",
    "Search",
]

jd_summarized = """Experience Required: 5–9 years

1. Deep technical depth in modern ML systems — embeddings, retrieval, ranking, LLMs, fine-tuning.
2. Scrappy product-engineering attitude — willing to ship a working ranker in a week even if the underlying ML is "obviously suboptimal," because we need to learn from real users before we know what to actually optimize for.

These are not contradictory in real life. They feel contradictory because of how engineering culture sorted itself into "researcher" vs "shipper" archetypes. We need both modes available in the same person, and we'd rather you tilt slightly toward shipper than toward researcher.

The high-level mandate: own the intelligence layer of Redrob's product. That means the ranking, retrieval, and matching systems that decide what recruiters see when they search for candidates and what candidates see when they search for roles.
    • Audit what we currently have (it's mostly BM25 + rule-based scoring).
    • Ship a ranking system that demonstrably improves recruiter-engagement metrics. This will involve embeddings, hybrid retrieval, and probably some LLM-based re-ranking.
    • Set up the evaluation infrastructure — offline benchmarks, online A/B testing, recruiter-feedback loops.
Beyond that, you'll be driving the long-term architecture of how we do candidate-JD matching at scale, mentoring the next round of hires (we're growing the team from 4 to 12 engineers in the next year).

Things you absolutely need
    • Production experience with embeddings-based retrieval systems (sentence-transformers, OpenAI embeddings, BGE, E5, or similar) deployed to real users. Handled embedding drift, index refresh, retrieval-quality regression in production.
    • Production experience with vector databases or hybrid search infrastructure — Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS, or something similar.
    • Strong Python.
    • Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation.

    • LLM fine-tuning experience (LoRA, QLoRA, PEFT)
    • Experience with learning-to-rank models (XGBoost-based or neural)
    • Prior exposure to HR-tech, recruiting tech, or marketplace products
    • Background in distributed systems or large-scale inference optimization
    • Open-source contributions

Location: Pune / Noida"""


def relevant_skill_keywords():
    s1 = ["jd"]
    s2 = ["qlora", "lora", "peft"]
    s3 = ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch"]
    s4 = ["rag", "ranking", "xgboost"]
    s5 = ["ndcg", "mrr"]
    s6 = ["bm25", "faiss"]

    [random.shuffle(s) for s in [s1, s2, s3, s4, s5, s6]]
    arr = [s1, s2, s3, s4, s5, s6]
    return arr


relevant_skill_keyword_replacement = {
    "jd": "candidate-JD matching architecture",
    "rag": "RAG systems",
    "ranking": "ranking and retrieval",
    "xgboost": "XGBoost",
    "qlora": "fine tuning LLMs",
    "lora": "fine tuning LLMs",
    "peft": "fine tuning LLMs",
    "bm25": "BM25",
    "faiss": "FAISS",
    "pinecone": "vector databases",
    "weaviate": "vector databases",
    "qdrant": "vector databases",
    "milvus": "vector databases",
    "opensearch": "search engines",
    "elasticsearch": "search engines",
    "ndcg": "evaluation metrics",
    "mrr": "evaluation metrics",
}

relevant_skills = [
    "Information Retrieval",
    "pgvector",
    "Milvus",
    "Qdrant",
    "QLoRA",
    "Sentence Transformers",
    "Embeddings",
    "Learning to Rank",
    "RAG",
    "Vector Search",
    "Recommendation Systems",
    "Pinecone",
    "Weaviate",
    "LoRA",
    "OpenSearch",
    "Haystack",
    "BM25",
    "FAISS",
    "LlamaIndex",
    "Fine-tuning LLMs",
]
