from sentence_transformers import CrossEncoder
from utils import candidate_to_text
import torch
import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

torch.set_num_threads(2)


class CrossEncoderReranker:
    def __init__(self, candidates, jd_text):
        self.candidates = candidates
        self.model = model = CrossEncoder("./models/ettin-reranker-32m-v1")
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
