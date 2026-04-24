# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 15:53:10 2026

@author: chodo
"""
import re
import numpy as np
from collections import Counter

# Replace < and > by spaces so <A><B> -> A B
ANGLE_RE = re.compile(r"[<>]")

# Token rule:
# - alphanumeric runs -> one token
# - every single non-alphanumeric, non-whitespace char -> separate token
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9\s]", flags=re.UNICODE)


def tokenize_structural(text: str):
    text = ANGLE_RE.sub(" ", text)
    text = text.lower()
    return TOKEN_RE.findall(text)


def _build_vocab(top_tokens):
    """Deterministic vocab order + append UNK."""
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
    return id_to_token, token_to_id, unk_id, UNK


def _compute_df_cf_tf(normalized_samples, file_paths, token_to_id, unk_id, use_unk=True):
    """
    Computes:
      - df[id]: in how many files token appears (presence, max 1 per file)
      - cf[id]: total occurrences across all files
      - tf_by_file[file_index][id]: occurrences in that file (counts)
    """
    k = len(token_to_id)
    df = np.zeros(k, dtype=np.int64)
    cf = np.zeros(k, dtype=np.int64)
    tf_by_file = []

    for path in file_paths:
        lines = normalized_samples[path]
        tf = np.zeros(k, dtype=np.int64)
        seen = np.zeros(k, dtype=np.bool_)

        for line in lines:
            toks = tokenize_structural(line)
            for t in toks:
                tid = token_to_id.get(t, unk_id) if use_unk else token_to_id.get(t, None)
                if tid is None:
                    continue
                tf[tid] += 1
                cf[tid] += 1
                seen[tid] = True

        df += seen.astype(np.int64)
        tf_by_file.append(tf)

    return df, cf, tf_by_file


def _safe_row_normalize_sum1(mat: np.ndarray, eps: float = 1e-12):
    """
    Normalize each row to sum to 1 (if row sum > 0).
    """
    row_sums = mat.sum(axis=1, keepdims=True)
    mat = np.where(row_sums > eps, mat / row_sums, mat)
    return mat


def compute_tf_idf_index(
    normalized_samples,
    file_paths,
    top_tokens,
    target_len,
    # weighting knobs (log-friendly)
    g_max=6.0,          # cap on global penalty term
    min_df=2,           # optionally suppress ultra-rare tokens
    unk_weight_floor=0.1,  # keep UNK low-impact (acts like "garbage")
    # normalization knobs
    sum1_per_position=True,   # <-- your requested "one-hot encodings normalized to sum of 1"
    l2_normalize=True,        # recommended for cosine
    dtype=np.float32,
):
    """
    Positional resampled embedding (B) with log-friendly weighting:
      w(t,d) = log(1+tf(t,d)) * idf(t) * cap(log(T/cf(t)), g_max)
    applied as a per-token multiplier.
    
    Representation:
      per file: F in R^{L x k}
      - build per-line resampled matrices, average across lines
      - optionally normalize each position (row) to sum 1
      - flatten to vector length L*k
      - optionally L2 normalize for cosine

    Returns:
      X: ndarray (n_files, L*k)
      meta: dict
    """
    L = int(target_len)
    if L <= 0:
        raise ValueError(f"target_len must be positive, got {L}")

    id_to_token, token_to_id, unk_id, UNK = _build_vocab(top_tokens)
    k = len(id_to_token)
    N = len(file_paths)

    # Compute df, cf, and tf per file
    df, cf, tf_by_file = _compute_df_cf_tf(
        normalized_samples=normalized_samples,
        file_paths=file_paths,
        token_to_id=token_to_id,
        unk_id=unk_id,
        use_unk=True,
    )
    T = int(cf.sum())

    # IDF (file-presence)
    idf = np.log((N + 1.0) / (df + 1.0)) + 1.0

    # Global penalty from collection frequency
    # G(t)=log(T/cf(t)), capped
    # Avoid div-by-zero: if cf=0, treat as max (but cf=0 shouldn't happen for in-vocab tokens)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.log((T + 1e-12) / (cf.astype(np.float64) + 1e-12))
    g = np.clip(g, 0.0, g_max)

    # Optional: suppress tokens that appear in too few files (avoid one-off noise)
    # Instead of removing dimensions, we set their weight to 0 so they don't affect similarity.
    rare_mask = (df < min_df)
    rare_mask[unk_id] = False  # handle UNK separately

    # We will compute a per-file token multiplier:
    # W_d[t] = log(1+tf_d[t]) * idf[t] * g[t]
    # then used inside the one-hot interpolation as the amplitude for token t in that file.

    # Force UNK low-impact regardless of tf/df/cf
    # (You asked for this behavior.)
    # We implement by setting its effective multiplier later to unk_weight_floor.
    # Also, if you want to keep punctuation from dominating, min_df and g help a lot.

    # Precompute resampling positions
    if L == 1:
        def positions(n): return [0.0]
    else:
        def positions(n):
            scale = (n - 1) / (L - 1)
            return [j * scale for j in range(L)]

    X = np.zeros((N, L * k), dtype=dtype)

    for file_idx, path in enumerate(file_paths):
        lines = normalized_samples[path]
        if not lines:
            continue

        tf = tf_by_file[file_idx].astype(np.float64)
        tf_log = np.log1p(tf)

        # per-token multipliers for THIS file
        W = tf_log * idf * g

        # suppress ultra-rare tokens
        W[rare_mask] = 0.001

        # UNK fixed floor weight (small)
        W[unk_id] = float(unk_weight_floor)

        file_mat = np.zeros((L, k), dtype=np.float64)
        used_lines = 0

        for line in lines:
            toks = tokenize_structural(line)
            n = len(toks)
            if n == 0:
                continue

            ids = [token_to_id.get(t, unk_id) for t in toks]
            line_mat = np.zeros((L, k), dtype=np.float64)

            if n == 1:
                tid = ids[0]
                line_mat[:, tid] = W[tid]
            else:
                ps = positions(n)
                for j, p in enumerate(ps):
                    i = int(np.floor(p))
                    if i >= n - 1:
                        tid = ids[n - 1]
                        line_mat[j, tid] += W[tid]
                    else:
                        a = p - i
                        t0 = ids[i]
                        t1 = ids[i + 1]
                        line_mat[j, t0] += (1.0 - a) * W[t0]
                        line_mat[j, t1] += a * W[t1]

            # Your requested normalization: each position sums to 1
            if sum1_per_position:
                line_mat = _safe_row_normalize_sum1(line_mat)

            file_mat += line_mat
            used_lines += 1

        if used_lines > 0:
            file_mat /= float(used_lines)

        # It can be beneficial to re-normalize after averaging too:
        if sum1_per_position:
            file_mat = _safe_row_normalize_sum1(file_mat)

        vec = file_mat.reshape(-1).astype(np.float64)

        if l2_normalize:
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

        X[file_idx, :] = vec.astype(dtype)

    print(f"Built positional weighted embedding X with shape {X.shape} (L={L}, k={k}).")
    return X, {
        "id_to_token": id_to_token,
        "token_to_id": token_to_id,
        "k": k,
        "L": L,
        "idf": idf.astype(dtype),
        "g": g.astype(dtype),
        "df": df,
        "cf": cf,
        "T": T,
        "N_files": N,
        "unk_token": UNK,
        "unk_id": unk_id,
        "g_max": g_max,
        "min_df": min_df,
        "unk_weight_floor": unk_weight_floor,
        "sum1_per_position": sum1_per_position,
        "l2_normalize": l2_normalize,
    }


if __name__ == "__main__":
    import main_cluster
    main_cluster.main()