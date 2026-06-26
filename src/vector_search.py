import lancedb


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
