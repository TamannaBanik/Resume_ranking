## Submission for the Redrob AI India Runs Hackathon Data and AI challenge.

**This repo uses git LFS to manage dataset, models and embeddings; please download them before running any scripts.**

## How to Run

1) Install dependencies
```sh
pip install -r requirements.txt
```

2) Run the ranker script
```sh
python rank.py --candidates ./dataset/candidates.jsonl --embeddings ./lance.db/ --model ./models/ettin-reranker-32m-v1/  --out ./team_ReRankers.csv
```