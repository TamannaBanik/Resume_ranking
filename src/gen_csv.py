import csv


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
