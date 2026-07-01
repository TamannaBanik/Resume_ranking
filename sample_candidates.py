import argparse
import json
import random


def load_candidates(file_path):
    candidates = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            candidates.append(json.loads(line))
    return candidates

def save_candidates(candidates, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(json.dumps(candidate) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Generate a random subset of candidates from a JSONL file.")
    parser.add_argument("--input",required=True,help="Path to candidates.jsonl")
    parser.add_argument("-k",type=int,required=True,help="Number of candidates to sample")
    parser.add_argument("--output",default="random_candidates.jsonl",help="Output JSONL file")
    parser.add_argument("--seed",type=int,default=None,help="Random seed (optional)")
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    candidates = load_candidates(args.input)
    if args.k > len(candidates):
        raise ValueError(f"Requested {args.k} candidates, but only {len(candidates)} are available.")
    sampled_candidates = random.sample(candidates, args.k)
    save_candidates(sampled_candidates, args.output)
    print(f"Saved {args.k} random candidates to '{args.output}'")

if __name__ == "__main__":
    main()