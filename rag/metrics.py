import math


def project_ranking(evidence: list[dict]) -> list[str]:
    seen, out = set(), []
    for e in evidence:
        p = e.get("project")
        if p and p not in seen:
            seen.add(p); out.append(p)
    return out


def recall_at(rank, gold, k=5):
    if not gold:
        return None
    return len(set(rank[:k]) & set(gold)) / min(len(gold), k)


def mrr(rank, gold):
    for i, p in enumerate(rank):
        if p in gold:
            return 1 / (i + 1)
    return 0.0


def ndcg_at(rank, gold, k=10):
    if not gold:
        return None
    dcg = sum(1 / math.log2(i + 2) for i, p in enumerate(rank[:k]) if p in gold)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / ideal
