# Single self contained ranker script.
# For better organized source, check `src/`

import argparse
import csv
import json
import math
import os
import random
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from types import TracebackType
from typing import Any, Optional, Type

import lancedb
import torch
from sentence_transformers import CrossEncoder

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

random.seed(42)
torch.set_num_threads(2)


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
    "disqualified_titles": ["Researcher", "Architect", "Tech Lead"],
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


class JsonlReader:
    def __init__(self, filepath: str):
        self.filepath: str = filepath
        self.isjsonl: bool = filepath.endswith(".jsonl") # json otherwise, we dont support any other types
        self.file: Optional[Any] = None

    def __enter__(self) -> "JsonlReader":
        self.file = open(self.filepath, "r")
        if not self.isjsonl:
            self.candidates = json.load(self.file)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        if self.file:
            self.file.close()

    def __iter__(self) -> "JsonlReader":
        if self.isjsonl:
            return self
        else:
            return iter(self.candidates)

    def __next__(self) -> dict[str, Any]:
        line = self.file.readline()

        if not line:
            raise StopIteration

        return json.loads(line)



def candidate_to_text(candidate) -> str:
    career_history = []
    for career in candidate["career_history"]:
        desc = f"""- {career['company']} ({career['title']})
Duration: {round(career['duration_months']/12, 1)} years
Description: {career['description']}"""
        career_history.append(desc)

    skills = []
    for skill in candidate["skills"]:
        if skill["proficiency"] in ["expert", "advanced"]:
            desc = f"""- {skill['name']}"""
            skills.append(desc)

    # Initially candidate text did have symmary but that did not provide significant improvements
    # Instead it seeped in a fed candidates with great summary but not-so-good career record
    return f"""{candidate['profile']['headline']}
Years Of Experience: {candidate['profile']['years_of_experience']} years

Skills
{'\n'.join(skills)}"""


def candidate_to_career_text(candidate) -> str:
    career_history = []
    for career in candidate["career_history"]:
        career_history.append(career["description"])
    return " ".join(career_history)


# TODO: Use this, JD states this requirement
def job_change_frequency(career_history, threshold_months=24) -> float:
    past_roles = [job for job in career_history if not job["is_current"]]

    if not past_roles:
        return False

    short_stints = sum(
        1 for job in past_roles if job["duration_months"] < threshold_months
    )
    stint_ratio = short_stints / len(past_roles)

    return stint_ratio


class HardFilter:
    def __init__(self):
        pass
        self.filter_list: list[dict] = []
        self.allowed_current_title_filters = current_title_keywords

    def add_candidate(self, candidate: dict):
        self.filter_list.append(candidate)

    def __current_title_filter(self, candidate) -> bool:
        for keyword in self.allowed_current_title_filters:
            if keyword in candidate["profile"]["current_title"]:
                return True
        return False

    def filter_on_current_title(self):
        self.filter_list = filter(
            lambda c: self.__current_title_filter(c), self.filter_list
        )

    def __yoe_mismatch_filter(self, candidate) -> bool:
        total_exp = candidate["profile"]["years_of_experience"]
        exp_sum = 0
        for career in candidate["career_history"]:
            exp_sum += career["duration_months"]
        if (total_exp - exp_sum / 12) > 1.5:
            return False
        if not candidate.get("__rank_meta"):
            candidate["__rank_meta"] = {}
        candidate["__rank_meta"]["wyoe"] = round(exp_sum / 12, 1)
        return True

    def filter_on_years_of_experience_mismatch(self):
        self.filter_list = filter(
            lambda candidate: self.__yoe_mismatch_filter(candidate), self.filter_list
        )

    def __location_filter(self, candidate) -> bool:
        for target_location in jd_data["target_locations"]:
            if target_location in candidate["profile"]["location"]:
                return True
            elif (
                candidate["profile"]["country"] == jd_data["target_country"]
                and candidate["redrob_signals"]["willing_to_relocate"]
            ):
                return True
        return False

    def filter_on_location(self):
        self.filter_list = filter(
            lambda candidate: self.__location_filter(candidate), self.filter_list
        )

    def __open_to_work_filter(self, candidate) -> bool:
        if candidate["redrob_signals"]["open_to_work_flag"]:
            return True
        return False

    def filter_on_open_to_work_signal(self):
        self.filter_list = filter(
            lambda candidate: self.__open_to_work_filter(candidate), self.filter_list
        )

    def get_filtered_list(self) -> list:
        return list(self.filter_list)


class VectorSearch:
    def __init__(self, candidates, db_path):
        self.target_candidate_ids = [
            candidate["candidate_id"] for candidate in candidates
        ]
        self.db = lancedb.connect(db_path)

    def search(self, query: str, across: str, num_results: int):
        source_table = self.db.open_table(query)
        query_vector = source_table.search().to_list()[0]["vector"]

        search_table = self.db.open_table("candidate_resumes")
        results = (
            search_table.search(query_vector, vector_column_name=across)
            .where(
                f"candidate_id IN ({', '.join(f"'{cid}'" for cid in self.target_candidate_ids)})"
            )
            .select(["candidate_id", "_distance"])
            .metric("cosine")
            .limit(num_results)
        )

        return results.to_pandas()


class CrossEncoderReranker:
    def __init__(
        self, candidates, jd_text, model_path="./models/ettin-reranker-32m-v1"
    ):
        self.candidates = candidates
        self.model = model = CrossEncoder(model_path)
        self.jd_text = jd_text

    def rerank(self) -> list[dict]:
        rankings = self.model.rank(
            query=self.jd_text,
            documents=[candidate_to_text(c) for c in self.candidates],
            return_documents=True,
            show_progress_bar=True,
        )

        for idx, result in enumerate(rankings):
            original_index = result["corpus_id"]
            score = result["score"]

            self.candidates[original_index]["__rank_meta"]["score"] = score

        min_score = min([c["__rank_meta"]["score"] for c in self.candidates])
        max_score = max([c["__rank_meta"]["score"] for c in self.candidates])

        def normalize(c):
            c["__rank_meta"]["rerank_score"] = (
                c["__rank_meta"]["score"] - min_score
            ) / (max_score - min_score)
            return c

        self.candidates = map(normalize, self.candidates)

        return list(self.candidates)


@dataclass
class NormalizedSignals:
    profile_completeness_score: float
    github_activity_score: float
    saved_by_recruiters_30d: float
    recruiter_response_rate: float
    interview_completion_rate: float
    offer_acceptance_rate: float
    signup_date: float
    last_active_date: float
    notice_period_days: float
    expected_salary_score: float
    avg_response_time_hours: float
    profile_views_received_30d: float
    applications_submitted_30d: float
    connection_count: float
    endorsements_received: float
    search_appearance_30d: float
    active_experience_score: float
    skill_assessment_score: float

    verified_email: float
    verified_phone: float
    linkedin_connected: float
    preferred_work_mode: float


class SignalNormalizer:
    def __init__(self, candidates):
        self.candidates = candidates
        self.bounds = {}
        self.target_work_mode = "onsite"

    def _parse_date(self, date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").timestamp()

    def calculate_pool_bounds(self):
        fields_to_track = [
            "profile_completeness_score",
            "signup_date",
            "last_active_date",
            "profile_views_received_30d",
            "applications_submitted_30d",
            "recruiter_response_rate",
            "avg_response_time_hours",
            "connection_count",
            "endorsements_received",
            "notice_period_days",
            "expected_salary_midpoint",
            "github_activity_score",
            "search_appearance_30d",
            "saved_by_recruiters_30d",
            "interview_completion_rate",
            "offer_acceptance_rate",
            "active_experience_years",
        ]

        for field in fields_to_track:
            self.bounds[field] = {"min": float("inf"), "max": float("-inf")}

        for c in self.candidates:
            sig = c["redrob_signals"]

            for field in [
                "profile_completeness_score",
                "profile_views_received_30d",
                "applications_submitted_30d",
                "recruiter_response_rate",
                "avg_response_time_hours",
                "connection_count",
                "endorsements_received",
                "notice_period_days",
                "github_activity_score",
                "search_appearance_30d",
                "saved_by_recruiters_30d",
                "interview_completion_rate",
                "offer_acceptance_rate",
            ]:
                val = float(sig[field])
                self.bounds[field]["min"] = min(self.bounds[field]["min"], val)
                self.bounds[field]["max"] = max(self.bounds[field]["max"], val)

            sig_date = self._parse_date(sig["signup_date"])
            act_date = self._parse_date(sig["last_active_date"])
            self.bounds["signup_date"]["min"] = min(
                self.bounds["signup_date"]["min"], sig_date
            )
            self.bounds["signup_date"]["max"] = max(
                self.bounds["signup_date"]["max"], sig_date
            )
            self.bounds["last_active_date"]["min"] = min(
                self.bounds["last_active_date"]["min"], act_date
            )
            self.bounds["last_active_date"]["max"] = max(
                self.bounds["last_active_date"]["max"], act_date
            )

            sal = sig["expected_salary_range_inr_lpa"]
            midpoint = (sal["min"] + sal["max"]) / 2.0
            self.bounds["expected_salary_midpoint"]["min"] = min(
                self.bounds["expected_salary_midpoint"]["min"], midpoint
            )
            self.bounds["expected_salary_midpoint"]["max"] = max(
                self.bounds["expected_salary_midpoint"]["max"], midpoint
            )

            wyoe_val = float(c["__rank_meta"]["wyoe"])
            self.bounds["active_experience_years"]["min"] = min(
                self.bounds["active_experience_years"]["min"], wyoe_val
            )
            self.bounds["active_experience_years"]["max"] = max(
                self.bounds["active_experience_years"]["max"], wyoe_val
            )

        max_relevant_skills = 1
        for c in self.candidates:
            sig = c["redrob_signals"]
            matches = sum(
                1
                for skill in relevant_skills
                if skill in sig["skill_assessment_scores"]
            )
            if matches > max_relevant_skills:
                max_relevant_skills = matches

        self.bounds["max_pool_skills_match"] = max_relevant_skills

    def _scale_linear(self, val, field, invert=False):
        b = self.bounds[field]
        denom = b["max"] - b["min"]
        if denom == 0:
            return 1.0 if invert else 0.0
        score = (val - b["min"]) / denom
        return (1.0 - score) if invert else score

    def _scale_log(self, val, field):
        b = self.bounds[field]
        denom = math.log1p(b["max"]) - math.log1p(b["min"])
        if denom == 0:
            return 0.0
        return (math.log1p(val) - math.log1p(b["min"])) / denom

    def _calculate_skills_score(self, skill_scores: dict) -> float:
        k = self.bounds["max_pool_skills_match"]

        scores = [
            skill_scores[skill] for skill in relevant_skills if skill in skill_scores
        ]

        if not scores:
            return 0.0

        return sum(scores) / (k * 100.0)

    def generate_normalized_profiles(self):
        self.calculate_pool_bounds()
        normalized_candidates = {}

        for c in self.candidates:
            sig = c["redrob_signals"]
            norm_sig = {}

            norm_sig["profile_completeness_score"] = self._scale_linear(
                sig["profile_completeness_score"], "profile_completeness_score"
            )
            norm_sig["github_activity_score"] = self._scale_linear(
                sig["github_activity_score"], "github_activity_score"
            )
            norm_sig["saved_by_recruiters_30d"] = self._scale_linear(
                sig["saved_by_recruiters_30d"], "saved_by_recruiters_30d"
            )
            norm_sig["recruiter_response_rate"] = self._scale_linear(
                sig["recruiter_response_rate"], "recruiter_response_rate"
            )
            norm_sig["interview_completion_rate"] = self._scale_linear(
                sig["interview_completion_rate"], "interview_completion_rate"
            )
            norm_sig["offer_acceptance_rate"] = self._scale_linear(
                sig["offer_acceptance_rate"], "offer_acceptance_rate"
            )
            norm_sig["signup_date"] = self._scale_linear(
                self._parse_date(sig["signup_date"]), "signup_date"
            )
            norm_sig["last_active_date"] = self._scale_linear(
                self._parse_date(sig["last_active_date"]), "last_active_date"
            )

            norm_sig["notice_period_days"] = self._scale_linear(
                sig["notice_period_days"], "notice_period_days", invert=True
            )
            midpoint = (
                sig["expected_salary_range_inr_lpa"]["min"]
                + sig["expected_salary_range_inr_lpa"]["max"]
            ) / 2.0
            norm_sig["expected_salary_score"] = self._scale_linear(
                midpoint, "expected_salary_midpoint", invert=True
            )

            norm_sig["avg_response_time_hours"] = 1.0 - self._scale_log(
                sig["avg_response_time_hours"], "avg_response_time_hours"
            )

            norm_sig["profile_views_received_30d"] = self._scale_log(
                sig["profile_views_received_30d"], "profile_views_received_30d"
            )
            norm_sig["applications_submitted_30d"] = self._scale_log(
                sig["applications_submitted_30d"], "applications_submitted_30d"
            )
            norm_sig["connection_count"] = self._scale_log(
                sig["connection_count"], "connection_count"
            )
            norm_sig["endorsements_received"] = self._scale_log(
                sig["endorsements_received"], "endorsements_received"
            )
            norm_sig["search_appearance_30d"] = self._scale_log(
                sig["search_appearance_30d"], "search_appearance_30d"
            )
            norm_sig["active_experience_score"] = self._scale_log(
                c["__rank_meta"]["wyoe"], "active_experience_years"
            )

            norm_sig["skill_assessment_score"] = self._calculate_skills_score(
                sig["skill_assessment_scores"]
            )

            norm_sig["verified_email"] = 1.0 if sig["verified_email"] else 0.0
            norm_sig["verified_phone"] = 1.0 if sig["verified_phone"] else 0.0
            norm_sig["linkedin_connected"] = 1.0 if sig["linkedin_connected"] else 0.0
            norm_sig["preferred_work_mode"] = (
                1.0 if sig["preferred_work_mode"] == self.target_work_mode else 0.0
            )

            normalized_candidates[c["candidate_id"]] = NormalizedSignals(**norm_sig)

        return normalized_candidates


def heuristic_scorer(signals: NormalizedSignals) -> float:
    score = (
        signals.profile_completeness_score * 10
        + signals.github_activity_score * 4
        + signals.saved_by_recruiters_30d * 4
        + signals.recruiter_response_rate * 4
        + signals.interview_completion_rate * 4
        + signals.offer_acceptance_rate * 4
        +
        # don't really care about signup date
        signals.last_active_date * 4
        + signals.notice_period_days * 15  # This gets downgraded later aswell
        + signals.expected_salary_score * 5
        + signals.avg_response_time_hours * 5
        + signals.profile_views_received_30d * 4
        + signals.applications_submitted_30d * 5
        + signals.connection_count * 4
        + signals.endorsements_received * 4
        + signals.search_appearance_30d * 4
        + signals.active_experience_score * 50
        +
        # TODO: Relocation should come under location boost
        # (signals.verified_email + signals.verified_phone + signals.linkedin_connected)
        # / 3
        # * 5
        +signals.preferred_work_mode * 5
        + signals.skill_assessment_score * 10  # This also gets checked as a concern
        # Correction: nvm i removed that, check reasoning.py
    ) / 140

    return score


@dataclass
class Concern:
    statements: list[str]
    level: float
    degrade: bool


class ReasonigEngine:
    def reason(
        self, candidate, signals: NormalizedSignals, relative_score, heuristic_score
    ) -> str:
        std_dev = relative_score - 0.5
        reason = None
        concern = None
        if std_dev > 0.1:
            reason, concern = self._gen_h_reason(candidate, signals)
        elif std_dev > -0.25:
            reason, concern = self._gen_m_reason(candidate, signals)
        else:
            reason, concern = self._gen_l_reason(candidate, signals)
        candidate["__rank_meta"]["concern_level"] = concern.level
        return reason

    def _gen_h_reason(self, candidate, signals) -> (str, Concern):
        return self._gen_h_template1(candidate, signals)

    def _gen_h_template1(self, candidate, signals) -> (str, Concern):
        base = f"{candidate['profile']['current_title']} with {round(candidate['profile']['years_of_experience'])} years"
        tech = self._figure_out_tech(candidate)
        strong_point = self._strongest_point(signals)
        concern = self._gen_concerns(candidate, signals)

        reason = base
        if len(tech) > 1:
            tech = tech[:6]
            if len(tech) < 3:
                concern.statements.append("lack of relevant skills")
                concern.level += (len(tech) / 10 + 0.2) * (
                    1.0 - concern.level
                )  # A 30-40% penalty
                concern.degrade = True
            reason += f" experienced in {', '.join([relevant_skill_keyword_replacement[k] for k in tech])};"
        else:
            concern.statements.append("severe lack of relevant skills")
            concern.level += 0.5 * (1.0 - concern.level)  # A 50% penalty
            concern.degrade = True
            reason += ";"
        if not strong_point:
            concern.statements.append("lack of overall engagement, included as filler")
            concern.level += 0.4 * (1.0 - concern.level)  # A 40% penalty
            concern.degrade = True
        else:
            reason += f" Strong {strong_point};"
        if len(concern.statements) > 0:
            reason += f" Concerns over {", ".join(concern.statements)};"
        return reason, concern

    def _figure_out_tech(self, candidate) -> list[str]:
        # TODO: Some candidates (eg, CAND_0093193) boast ranking in their summary but no real product in career history
        # Degrade their ranking
        text = candidate_to_career_text(candidate).lower()
        keywords = []
        for s in relevant_skill_keywords():
            for keyword in s:
                if bool(re.search(rf"(?<![a-zA-Z]){keyword}(?![a-zA-Z])", text)):
                    keywords.append(keyword)
                    break

        return keywords

    def _gen_m_reason(self, candidate, signals) -> (str, Concern):
        base = (
            f"{round(candidate['profile']['years_of_experience'])} years of experience"
        )
        tech = self._figure_out_tech(candidate)
        concern = self._gen_concerns(candidate, signals)

        reason = base
        if tech:
            tech = tech[:3]
            if len(tech) < 3:
                concern.statements.append("lack of relevant skills")
                concern.level += (len(tech) / 10 + 0.2) * (
                    1.0 - concern.level
                )  # A 30-40% penalty
                concern.degrade = True
            reason += f" working on {', '.join([relevant_skill_keyword_replacement[k] for k in tech])};"
        else:
            concern.statements.append("severe lack of relevant skills")
            concern.level += 0.5 * (1.0 - concern.level)  # A 50% penalty
            concern.degrade = True
            reason += ";"
        if len(concern.statements) > 0:
            reason += f" Concerns over {", ".join(concern.statements)};"
        return reason, concern

    def _gen_l_reason(self, candidate, signals) -> (str, Concern):
        reason = "Low overall score, adjacent skills only;"
        tech = self._figure_out_tech(candidate)
        concern = self._gen_concerns(candidate, signals)

        if tech:
            tech = tech[:3]
            if len(tech) < 3:
                concern.level += (len(tech) / 10 + 0.2) * (
                    1.0 - concern.level
                )  # A 30-40% penalty
                concern.degrade = True
        else:
            concern.level += 0.5 * (1.0 - concern.level)  # A 50% penalty
            concern.degrade = True
        if not concern.degrade:
            # TODO: Should we boost rank?
            pass
        return reason, concern

    def _strongest_point(self, signals: NormalizedSignals) -> Optional[str]:
        groups = {
            "profile and technical presence": [
                "github_activity_score",
                "profile_completeness_score",
                "skill_assessment_score",
            ],
            "recruiter engagement": [
                "saved_by_recruiters_30d",
                "recruiter_response_rate",
                "interview_completion_rate",
                "offer_acceptance_rate",
                "avg_response_time_hours",
            ],
            "platform activity & visibility": [
                "applications_submitted_30d",
                "last_active_date",
                "profile_views_received_30d",
                "connection_count",
                "endorsements_received",
                "search_appearance_30d",
            ],
        }

        signals_dict = asdict(signals)
        averages = {}

        for group_name, fields in groups.items():
            total_score = sum(signals_dict[field] for field in fields)
            averages[group_name] = total_score / len(fields)

        if max(averages.values()) < 0.6:
            return None
        return max(averages, key=averages.get)

    # TODO: Should we use a config to determins if field should be a concern or not?
    # Not every JD has same concerns
    def _gen_concerns(self, candidate, signals: NormalizedSignals) -> Concern:
        concern = Concern(statements=[], level=0, degrade=False)
        if signals.notice_period_days < 0.35:
            concern.statements.append(
                f"notice period ({candidate['redrob_signals']['notice_period_days']} days)"
            )
            concern.level += 1  # Not *that* serious, degrade but we can excuse
        # If candidate has only 2 jobs and left one early we excuse that.
        if (
            job_change_frequency(candidate["career_history"]) > 0.5
            and len(candidate["career_history"]) > 2
        ):
            concern.statements.append(
                f"frequent job hopping ({len(candidate['career_history'])} jobs in {candidate['__rank_meta']['wyoe']} years)"
            )
            concern.level += 4  # Very serious, chosse if not other candidate fits

        # if signals.skill_assessment_score < 0.3:
        #     concern.level += 0.5 # This was initially 2 but results looked worse to me

        concern.level = concern.level / 4.0

        if concern.level > 0:
            concern.degrade = True
        return concern


def write_csv(filename: str, candidates):
    scores = [c["__rank_meta"]["total_score"] for c in candidates]
    enforce_decreasing(scores)

    header = ["candidate_id", "rank", "score", "reasoning"]
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for i, c in enumerate(candidates):
            writer.writerow(
                [
                    c["candidate_id"],
                    i + 1,
                    f"{round(scores[i], 4):.4f}",
                    c["__rank_meta"]["reasoning"],
                ]
            )


def enforce_decreasing(scores: list[float], min_gap: float = 0.0001):
    for i in range(1, len(scores)):
        if scores[i] >= scores[i - 1]:
            scores[i] = scores[i - 1] - min_gap


def run_ranking(candidates_file, output_file, lance_path, model_path):
    hard_filter = HardFilter()
    with JsonlReader(candidates_file) as reader:
        for candidate in reader:
            hard_filter.add_candidate(candidate)

    if len(hard_filter.filter_list) >= 100:
        hard_filter.filter_on_current_title()

        # NOTE: Is open to work flag an accurate ground truth?
        # We loose a good candidate (CAND_0005260) because of this filter
        hard_filter.filter_on_open_to_work_signal()

        hard_filter.filter_on_location()
    
    hard_filter.filter_on_years_of_experience_mismatch()

    candidates = hard_filter.get_filtered_list()

    candidate_id_map = {}
    for cand in candidates:
        candidate_id_map[cand["candidate_id"]] = cand

    vs = VectorSearch(candidates, lance_path)
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
    merged_results["dist"] = (
        0.8 * merged_results["dist_1"] + 0.2 * merged_results["dist_2"]
    )
    merged_results = (
        merged_results.sort_values(by="dist").reset_index(drop=True).head(300)
    )

    merged_results["score"] = 1 - (
        merged_results["dist"] - merged_results["dist"].min()
    ) / (merged_results["dist"].max() - merged_results["dist"].min())

    filtered_candidates = [
        candidate_id_map[cid] for cid in merged_results["candidate_id"]
    ]

    cerr = CrossEncoderReranker(
        filtered_candidates, jd_summarized, model_path=model_path
    )
    ranked_candidates = cerr.rerank()

    signal_normalizer = SignalNormalizer(ranked_candidates)
    signals = signal_normalizer.generate_normalized_profiles()

    for c in ranked_candidates:
        c["__rank_meta"]["heuristic_score"] = heuristic_scorer(
            signals[c["candidate_id"]]
        )
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

    write_csv(output_file, ranked_candidates)


def main():
    parser = argparse.ArgumentParser(description="Candidate ranker.")

    parser.add_argument(
        "--candidates",
        required=True,
        type=str,
        help="Path to the input JSONL file containing candidate data.",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=str,
        help="Path where the output submission CSV results file will be saved.",
    )
    parser.add_argument(
        "--embeddings",
        required=False,
        default="./lance.db",
        type=str,
        help="Path to the input JSONL file containing candidate data.",
    )
    parser.add_argument(
        "--model",
        required=False,
        default="./models/ettin-reranker-32m-v1",
        type=str,
        help="Path where the output submission CSV results file will be saved.",
    )
    args = parser.parse_args()

    run_ranking(
        candidates_file=args.candidates,
        output_file=args.out,
        lance_path=args.embeddings,
        model_path=args.model,
    )


if __name__ == "__main__":
    main()
