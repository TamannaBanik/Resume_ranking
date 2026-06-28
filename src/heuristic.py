import math
from datetime import datetime
from dataclasses import dataclass

from hardcoded import relevant_skills


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
