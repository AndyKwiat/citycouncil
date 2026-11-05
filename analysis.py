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
        D[i, j] = D[j, i] = np.mean(M[i][both] != M[j][both]) if both.any() else np.nan
    # People who never voted together (one replaced the other, say) have no real distance. Treating that as total
    # disagreement would push them apart for no reason, so estimate it from how alike they are with everyone else.
    for i, j in zip(*np.where(np.isnan(D))):
        known = ~np.isnan(D[i]) & ~np.isnan(D[j])
        D[i, j] = np.abs(D[i][known] - D[j][known]).mean() if known.any() else .5
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


# ---------------------------------------------------------------- communities (voting alliance network)

def modularity(W, labels):
    """Newman modularity of a weighted network."""
    total = W.sum()
    if total <= 0:
        return 0.0
    strength = W.sum(1)
    same = labels[:, None] == labels[None, :]
    return float(((W - np.outer(strength, strength) / total) * same).sum() / total)


def _local_moves(W, order):
    """One Louvain level: move each node to whichever neighbouring community raises modularity most."""
    n, total, strength = len(W), W.sum(), W.sum(1)
    labels = np.arange(n)
    moved = True
    while moved:
        moved = False
        for i in order:
            current = labels[i]
            sums = {}
            for j in range(n):
                if j != i and W[i, j] > 0:
                    sums[labels[j]] = sums.get(labels[j], 0.0) + W[i, j]
            def gain(c):
                others = strength[labels == c].sum() - (strength[i] if c == current else 0)
                return sums.get(c, 0.0) - strength[i] * others / total
            best, best_gain = current, gain(current)
            for c in sorted(sums):
                g = gain(c)
                if g > best_gain + 1e-12:
                    best, best_gain = c, g
            if best != current:
                labels[i] = best
                moved = True
    return labels


def louvain(W, rng):
    """Louvain community detection on a symmetric weight matrix. Returns a community number per node."""
    W = np.array(W, float)
    np.fill_diagonal(W, 0)
    if W.sum() <= 0:
        return np.arange(len(W))
    members = [[i] for i in range(len(W))]
    current = W
    while True:
        labels = _local_moves(current, rng.permutation(len(current)))
        unique = sorted(set(labels.tolist()))
        if len(unique) == len(current):
            break
        index = {c: k for k, c in enumerate(unique)}
        merged = np.zeros((len(unique), len(unique)))
        grouped = [[] for _ in unique]
        for a, c in enumerate(labels):
            grouped[index[c]] += members[a]
            for b, d in enumerate(labels):
                merged[index[c], index[d]] += current[a, b]
        members, current = grouped, merged
    out = np.zeros(len(W), int)
    for c, group in enumerate(members):
        out[group] = c
    return out


def best_communities(W, restarts=50, seed=0):
    """Louvain's result depends on visiting order, so keep the best of several seeded runs."""
    rng = np.random.default_rng(seed)
    runs = [louvain(W, rng) for _ in range(restarts)]
    runs = sorted(runs, key=lambda r: tuple(r.tolist()))
    return max(runs, key=lambda r: round(modularity(np.array(W, float), r), 10))


def agreement_weights(R):
    """Weights for community detection: only agreement above the council's own average counts.

    Nearly everyone agrees on most contested votes, so raw percentages make one big blob. Keeping just the excess over
    the average leaves the pairs who agree more than is typical. Unknown pairs (NaN) stay at zero, which means no
    evidence rather than disagreement."""
    known = R[np.triu_indices(len(R), 1)]
    mean = np.nanmean(known)
    W = np.nan_to_num(R - mean, nan=0.0)
    W[W < 0] = 0
    np.fill_diagonal(W, 0)
    return W, float(mean)


def communities(names, agreed, shared, votes=None, resamples=300):
    """Detect voting communities from pairwise agreement; with `votes`, also test them by resampling."""
    n = len(names)
    R = np.full((n, n), np.nan)
    for i, j in itertools.combinations(range(n), 2):
        key = (names[i], names[j])
        if shared.get(key):
            R[i, j] = R[j, i] = agreed[key] / shared[key]
    W, mean = agreement_weights(R)
    labels = best_communities(W)
    # Number communities largest first, so colours stay stable between builds.
    sizes = sorted(set(labels.tolist()), key=lambda c: (-int((labels == c).sum()), int(np.where(labels == c)[0][0])))
    rank = {c: k for k, c in enumerate(sizes)}
    assigned = {names[i]: rank[int(labels[i])] for i in range(n)}
    result = {"method": "Louvain on agreement above the council average", "average_agreement": round(mean, 4),
              "modularity": round(modularity(W, labels), 3), "count": len(sizes), "members": assigned}
    if votes:
        M = np.array([[1 if x in v["for"] else -1 if x in v["against"] else 0 for v in votes] for x in names], float)
        rng = np.random.default_rng(1)
        together = np.zeros((n, n))
        counts = {}
        for _ in range(resamples):
            pick = M[:, rng.integers(0, len(votes), len(votes))]
            Rb = np.full((n, n), np.nan)
            for i, j in itertools.combinations(range(n), 2):
                both = (pick[i] != 0) & (pick[j] != 0)
                if both.any():
                    Rb[i, j] = Rb[j, i] = np.mean(pick[i][both] == pick[j][both])
            found = louvain(agreement_weights(Rb)[0], rng)
            counts[len(set(found.tolist()))] = counts.get(len(set(found.tolist())), 0) + 1
            together += found[:, None] == found[None, :]
        together /= resamples
        result["resamples"] = resamples
        result["resamples_count"] = {str(k): v for k, v in sorted(counts.items())}
        result["stays_with_community"] = {names[i]: round(float(np.mean([together[i, j] for j in range(n) if j != i and labels[j] == labels[i]] or [1.0])), 3) for i in range(n)}
    return result
