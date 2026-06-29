import random
import re
from dataclasses import asdict, dataclass
from typing import Optional

from hardcoded import (relevant_skill_keyword_replacement,
                       relevant_skill_keywords)
from heuristic import NormalizedSignals
from utils import candidate_to_career_text, job_change_frequency


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
