import random

from filter import HardFilter
from gen_csv import write_csv
from hardcoded import jd_summarized
from heuristic import SignalNormalizer, heuristic_scorer
from reader import JsonlReader
from reasoning import ReasonigEngine
from rerank import CrossEncoderReranker
from vector_search import VectorSearch

random.seed(42)


hard_filter = HardFilter()
with JsonlReader("dataset/candidates.jsonl") as reader:
    for candidate in reader:
        hard_filter.add_candidate(candidate)

hard_filter.filter_on_current_title()

# NOTE: Is open to work flag an accurate ground truth?
# We loose a good candidate (CAND_0005260) because of this filter
hard_filter.filter_on_open_to_work_signal()

# NOTE: This too ^^ (eg, CAND_0071974)
hard_filter.filter_on_location()
hard_filter.filter_on_years_of_experience_mismatch()

candidates = hard_filter.get_filtered_list()

candidate_id_map = {}
for cand in candidates:
    candidate_id_map[cand["candidate_id"]] = cand

vs = VectorSearch(candidates, "./lance.db")
skill_career_search_results = vs.search(
    "jd_skills", "career_desc_vector", len(candidates)
)
full_semantic_search_results = vs.search("jd_text", "text_vector", len(candidates))

# Rename distance for merge
skill_career_search_results = skill_career_search_results.rename(
    columns={"_distance": "dist_1"}
)
full_semantic_search_results = full_semantic_search_results.rename(
    columns={"_distance": "dist_2"}
)

# Normalize distances (0-1)
skill_career_search_results_min = skill_career_search_results["dist_1"].min()
skill_career_search_results_max = skill_career_search_results["dist_1"].max()

skill_career_search_results["dist_1"] = (
    skill_career_search_results["dist_1"] - skill_career_search_results_min
) / (skill_career_search_results_max - skill_career_search_results_min)

full_semantic_search_results_min = full_semantic_search_results["dist_2"].min()
full_semantic_search_results_max = full_semantic_search_results["dist_2"].max()

full_semantic_search_results["dist_2"] = (
    full_semantic_search_results["dist_2"] - full_semantic_search_results_min
) / (full_semantic_search_results_max - full_semantic_search_results_min)

# Merge 2 results
merged_results = skill_career_search_results.merge(
    full_semantic_search_results, on="candidate_id", how="inner"
)

# Calculate total dist score
merged_results["dist"] = 0.8 * merged_results["dist_1"] + 0.2 * merged_results["dist_2"]
merged_results = merged_results.sort_values(by="dist").reset_index(drop=True).head(300)

merged_results["score"] = 1 - (
    merged_results["dist"] - merged_results["dist"].min()
) / (merged_results["dist"].max() - merged_results["dist"].min())

filtered_candidates = [candidate_id_map[cid] for cid in merged_results["candidate_id"]]

cerr = CrossEncoderReranker(filtered_candidates, jd_summarized)
ranked_candidates = cerr.rerank()

signal_normalizer = SignalNormalizer(ranked_candidates)
signals = signal_normalizer.generate_normalized_profiles()

for c in ranked_candidates:
    c["__rank_meta"]["heuristic_score"] = heuristic_scorer(signals[c["candidate_id"]])
    c["__rank_meta"]["total_score"] = round(
        c["__rank_meta"]["rerank_score"] * 0.3
        + c["__rank_meta"]["heuristic_score"] * 0.7,
        4,
    )

# Normalize total_score
min_total_score = min([c["__rank_meta"]["total_score"] for c in ranked_candidates])
max_total_score = max([c["__rank_meta"]["total_score"] for c in ranked_candidates])
for c in ranked_candidates:
    c["__rank_meta"]["relative_score"] = (
        c["__rank_meta"]["total_score"] - min_total_score
    ) / (max_total_score - min_total_score)


reasoning_engine = ReasonigEngine()
for c in ranked_candidates:
    c["__rank_meta"]["reasoning"] = reasoning_engine.reason(
        c,
        signals[c["candidate_id"]],
        c["__rank_meta"]["relative_score"],
        c["__rank_meta"]["heuristic_score"],
    )
    c["__rank_meta"]["total_score"] = c["__rank_meta"]["total_score"] * (
        1.0 - c["__rank_meta"]["concern_level"]
    )

ranked_candidates = sorted(
    ranked_candidates, key=lambda c: c["__rank_meta"]["total_score"], reverse=True
)[
    :100
]  # Top 100 candidates

write_csv("final.csv", ranked_candidates)
