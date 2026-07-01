from hardcoded import current_title_keywords, jd_data


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
