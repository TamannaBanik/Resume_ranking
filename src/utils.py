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
