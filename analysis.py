#!/usr/bin/env python3
"""Find voting groups from the non-unanimous votes and place members on a 2D map."""
import itertools
import numpy as np

UNCLEAR_BELOW = 0.1  # a silhouette under this means someone sits between groups
RESAMPLES = 1000


def distances(M):
    """Share of the votes both attended on which two members voted differently."""
    D = np.zeros((len(M), len(M)))
    for i, j in itertools.combinations(range(len(M)), 2):
        both = (M[i] != 0) & (M[j] != 0)
        D[i, j] = D[j, i] = np.mean(M[i][both] != M[j][both]) if both.any() else 1.0
    return D


def place(D):
    """Classical multidimensional scaling: 2D positions whose gaps approximate D."""
    n = len(D)
    J = np.eye(n) - 1 / n
    values, vectors = np.linalg.eigh(-.5 * J @ (D ** 2) @ J)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    return vectors[:, :2] * np.sqrt(np.maximum(values[:2], 0)), values[:2].sum() / values[values > 0].sum()


def groups_of(D, k):
    """Average-linkage hierarchical clustering, cut into k groups."""
    groups = [[i] for i in range(len(D))]
    while len(groups) > k:
        a, b = min(itertools.combinations(range(len(groups)), 2), key=lambda p: D[np.ix_(groups[p[0]], groups[p[1]])].mean())
        groups[a] += groups.pop(b)
    return groups


def silhouettes(D, groups):
    """For each member, how much closer they are to their own group than the next nearest (-1 to 1)."""
    out = np.zeros(len(D))
    for g, members in enumerate(groups):
        for i in members:
            own = [j for j in members if j != i]
            if own:
                a, b = D[i, own].mean(), min(D[i, m].mean() for h, m in enumerate(groups) if h != g)
                out[i] = (b - a) / max(a, b) if max(a, b) else 0
    return out


def best_k(D):
    scores = {k: float(silhouettes(D, groups_of(D, k)).mean()) for k in range(2, min(6, len(D)))}
    return max(scores, key=scores.get), scores


def clusters(votes):
    names = sorted({n for v in votes for n in v["for"] + v["against"]})
    M = np.array([[1 if n in v["for"] else -1 if n in v["against"] else 0 for v in votes] for n in names], float)
    D = distances(M)
    X, explained = place(D)
    k, scores = best_k(D)
    found = sorted(groups_of(D, k), key=len, reverse=True)
    sil = silhouettes(D, found)
    # Keep the picture stable between builds: largest group left, longest vertical reach downward.
    centre = X[found[0]].mean(0)
    if centre[0] > 0:
        X[:, 0] *= -1
    if X[np.abs(X[:, 1]).argmax(), 1] < 0:
        X[:, 1] *= -1
    label = {i: chr(65 + g) for g, m in enumerate(found) for i in m}
    groups = {chr(65 + g): [i for i in m if sil[i] >= UNCLEAR_BELOW] for g, m in enumerate(found)}
    unclear = [i for i in range(len(names)) if sil[i] < UNCLEAR_BELOW]

    # Resample the votes to see how much the result depends on any particular vote.
    rng = np.random.default_rng(0)
    together = np.zeros_like(D)
    picks = {}
    for _ in range(RESAMPLES):
        Db = distances(M[:, rng.integers(0, len(votes), len(votes))])
        picked = best_k(Db)[0]
        picks[picked] = picks.get(picked, 0) + 1
        for g in groups_of(Db, k):
            together[np.ix_(g, g)] += 1
    together /= RESAMPLES

    def mean(rows, cols):
        vals = [D[a, b] for a in rows for b in cols if a != b]
        return float(np.mean(vals)) if vals else None

    return {
        "method": "Classical MDS on pairwise disagreement rates; average-linkage hierarchical clustering; k chosen by mean silhouette",
        "votes": len(votes), "groups_chosen": k, "silhouette_by_k": {str(a): round(b, 3) for a, b in scores.items()},
        "variance_in_2d": round(float(explained), 3), "unclear_below": UNCLEAR_BELOW,
        "resamples": RESAMPLES, "resamples_choosing": {str(a): b for a, b in sorted(picks.items())},
        "groups": {g: {"members": [names[i] for i in m], "agreement_within": None if len(m) < 2 else round(1 - mean(m, m), 3),
                       "stays_together": None if len(m) < 2 else round(float(np.mean([together[a, b] for a in m for b in m if a != b])), 3)}
                   for g, m in groups.items()},
        "unclear": [names[i] for i in unclear],
        "agreement_between": {f"{a}-{b}": round(1 - mean(groups[a], groups[b]), 3) for a, b in itertools.combinations(groups, 2) if groups[a] and groups[b]},
        "members": {names[i]: {"x": round(float(X[i, 0]), 4), "y": round(float(X[i, 1]), 4), "nearest_group": label[i], "silhouette": round(float(sil[i]), 3),
                               "group": None if i in unclear else label[i],
                               "with_group": {g: round(float(np.mean([together[i, j] for j in m if j != i])), 3) for g, m in groups.items() if [j for j in m if j != i]}}
                    for i in range(len(names))},
    }
