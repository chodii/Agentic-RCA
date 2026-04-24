# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 17:05:03 2026

@author: chodo
"""

import re
import numpy as np
from collections import Counter, defaultdict

# Replace < and > by spaces so <A><B> -> A B
ANGLE_RE = re.compile(r"[<>]")
# Alnum runs OR single non-alnum non-space character
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9\s]", flags=re.UNICODE)

def tokenize_structural(text: str):
    text = ANGLE_RE.sub(" ", text)
    text = text.lower()
    return TOKEN_RE.findall(text)

def compute_commonness_weights(normalized_samples, top_tokens, base=0.1, alpha=0.9, unk_token="<UNK>"):
    """
    Computes file-presence commonness p(t) over the dataset (max 1 per file).
    Returns per-token weights for tokens in top_tokens, plus unk_token.
    """
    # deterministic token order
    if isinstance(top_tokens, (set, frozenset)):
        vocab_tokens = sorted(top_tokens)
    else:
        vocab_tokens = list(top_tokens)

    # file presence counts (df)
    df = Counter()
    n_files = len(normalized_samples)

    for _path, lines in normalized_samples.items():
        seen = set()
        for line in lines:
            toks = tokenize_structural(line)
            seen.update(toks)
        # only care about tokens in top_tokens; others become UNK anyway
        for t in seen:
            if t in vocab_tokens:
                df[t] += 1

    weights = {}
    for t in vocab_tokens:
        p = df[t] / n_files if n_files else 0.0
        weights[t] = base + alpha * (1.0 - p)

    # UNK fixed to base (low importance)
    weights[unk_token] = base

    return weights

def compute_tf_idf_index(
    normalized_samples,
    file_paths,
    top_tokens,
    target_len,
    base=0.1,
    alpha=0.9,
    l2_normalize=True,
    dtype=np.float32,
):
    """
    Positional embedding with linear-interpolation resampling,
    using commonness-based per-token weights (file presence).
    Returns X (numeric) and meta.
    """
    L = int(target_len)
    if L <= 0:
        raise ValueError(f"target_len must be positive, got {L}")

    # deterministic vocab order
    if isinstance(top_tokens, (set, frozenset)):
        vocab_tokens = sorted(top_tokens)
    else:
        vocab_tokens = list(top_tokens)

    UNK = "<UNK>"
    if UNK in vocab_tokens:
        UNK = "__UNK__"

    id_to_token = vocab_tokens + [UNK]
    token_to_id = {t: i for i, t in enumerate(id_to_token)}
    unk_id = len(id_to_token) - 1
    k = len(id_to_token)

    # compute weights from file presence
    weights = compute_commonness_weights(
        normalized_samples=normalized_samples,
        top_tokens=vocab_tokens,
        base=base,
        alpha=alpha,
        unk_token=UNK,
    )
    # store as vector aligned with ids
    wvec = np.array([weights[t] for t in id_to_token], dtype=dtype)

    n_files = len(file_paths)
    X = np.zeros((n_files, L * k), dtype=dtype)

    # resampling positions helper
    if L == 1:
        def positions(n): return [0.0]
    else:
        def positions(n):
            scale = (n - 1) / (L - 1)
            return [j * scale for j in range(L)]

    for file_idx, path in enumerate(file_paths):
        lines = normalized_samples[path]
        if not lines:
            continue

        file_mat = np.zeros((L, k), dtype=dtype)
        used_lines = 0

        for line in lines:
            toks = tokenize_structural(line)
            n = len(toks)
            if n == 0:
                continue

            ids = [token_to_id.get(t, unk_id) for t in toks]

            line_mat = np.zeros((L, k), dtype=dtype)

            if n == 1:
                tid = ids[0]
                line_mat[:, tid] = wvec[tid]
            else:
                ps = positions(n)
                for j, p in enumerate(ps):
                    i = int(np.floor(p))
                    if i >= n - 1:
                        tid = ids[n - 1]
                        line_mat[j, tid] += wvec[tid]
                    else:
                        a = p - i
                        t0 = ids[i]
                        t1 = ids[i + 1]
                        line_mat[j, t0] += (1.0 - a) * wvec[t0]
                        line_mat[j, t1] += a * wvec[t1]

            file_mat += line_mat
            used_lines += 1

        if used_lines > 0:
            file_mat /= float(used_lines)

        vec = file_mat.reshape(-1)

        if l2_normalize:
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

        X[file_idx, :] = vec

    print(f"Built commonness-weighted positional embedding X with shape {X.shape} (L={L}, k={k}).")
    print(f"Weight range (excluding UNK): [{min(wvec[:-1]):.3f}, {max(wvec[:-1]):.3f}]  UNK={wvec[-1]:.3f}")
    return X, {
        "token_to_id": token_to_id,
        "id_to_token": id_to_token,
        "weights": weights,
        "k": k,
        "L": L,
        "base": base,
        "alpha": alpha,
        "unk_token": UNK,
    }
