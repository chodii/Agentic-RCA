#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 17:42:46 2026

@author: chodo
"""

"""
Walk a dataset directory recursively, read the first N lines of each file,
and create a "structural" normalized version of those lines by replacing:
- timestamps/dates -> <time>
- IP addresses     -> <ip>
- hex addresses    -> <hex>
- (remaining) nums -> <num>

Nothing is written back to disk. The script only reads files and produces
in-memory normalized samples (and prints optional progress).
"""


import os
import re
from pathlib import Path
from typing import Dict, List, Iterator, Tuple, Optional


import clustering_method
import clustering_inspector
import clustering_visualizer
import clustering_preprocessing
import clustering_by_exact_matching

import clustering_token_analysis
import clustering_token_vectorization
import clustering_commonness_embedding

# ---------- Config ----------
LINES = 50

# Point this at your dataset root
DATASET_ROOT = None

# Optionally restrict which files you consider "log-like" by suffix patterns.
# Rotary logs often look like: something.log, something.log.1, something.log.2, ...
LOG_SUFFIX_RE = re.compile(r".*\.log(\.\d+)?$", re.IGNORECASE)

# If True, skip files that look binary (based on a small byte sample)
SKIP_BINARY = True


def looks_binary(path: Path, sniff_bytes: int = 4096) -> bool:
    """
    Heuristic: if there are NUL bytes in the first chunk, treat as binary.
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(sniff_bytes)
        return b"\x00" in chunk
    except Exception:
        # If unreadable, treat as binary-ish/skip
        return True
    
def iter_files(root: Path) -> Iterator[Path]:
    """
    Recursively yield files. Adjust filters here if you want to include everything
    (including PDFs) or only log-ish files.
    """
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.is_file():
                yield p


def read_first_lines(path: Path, n_lines: int) -> Optional[List[str]]:
    """
    Read first N lines as text (best-effort). Returns None if unreadable.
    """
    try:
        # errors="replace" avoids crashing on weird encodings
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines: List[str] = []
            for _ in range(n_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
        return lines
    except Exception:
        return None


def main() -> None:
    DATASET_ROOT = Path("C:\\Datasets\\alstomu\\").expanduser().resolve()
    # Stores normalized sample lines per file path (in-memory only)
    # In the next step, you’ll turn this into feature vectors / embeddings.
    normalized_samples: Dict[Path, List[str]] = {}

    total = 0
    kept = 0
    skipped = 0

    for path in iter_files(DATASET_ROOT):
        total += 1

        # Optional: keep only .log, .log.1, .log.2, ...
        # Comment out if you want to examine *all* files and decide later.
        if not LOG_SUFFIX_RE.match(path.name):
            skipped += 1
            continue

        if SKIP_BINARY and looks_binary(path):
            skipped += 1
            continue

        raw_lines = read_first_lines(path, LINES)
        if raw_lines is None:
            skipped += 1
            continue

        norm = [clustering_preprocessing.normalize_line(ln) for ln in raw_lines]
        normalized_samples[path] = norm
        kept += 1

        # Minimal progress output every so often
        if kept % 500 == 0:
            print(f"Processed {kept} files (total seen: {total}, skipped: {skipped})")

    print(f"Done. total seen={total}, kept={kept}, skipped={skipped}")
    print(f"In-memory normalized samples: {len(normalized_samples)} files")
    # At this point nothing is written back; we only built an in-memory dict.

    # You can inspect one example:
    if normalized_samples:
        any_path = next(iter(normalized_samples))
        print("\n--- Example file:", any_path, "---")
        for ln in normalized_samples[any_path][:10]:
            print(ln)

    # token analysis
    """continue clustering here"""# Ensure stable order
    # Ensure stable ordering:
    file_paths = sorted(normalized_samples.keys())
    
    toptok, linemedian = clustering_token_analysis.analyze_dataset(normalized_samples, k=15)
    
    
    
    X, meta = clustering_token_vectorization.compute_tf_idf_index(
        normalized_samples=normalized_samples,
        file_paths=file_paths,
        top_tokens=toptok,
        target_len=int(linemedian),
        g_max=8.0,
        min_df=1,
        unk_weight_floor=0.1,
        sum1_per_position=True,   # your "sum to 1" requirement
        l2_normalize=True,        # keep for cosine
    )
    labels, probs, outlier_scores = clustering_method.cluster_HDBSCAN(
        X,
        min_cluster_size=20,
        min_samples=20,
        metric="euclidean",
    )
    
    prob_threshold = 0.30
    hard = (labels == -1)
    soft = (probs < prob_threshold)
    anomaly_mask = hard | soft
    
    labels_viz = labels.copy()
    labels_viz[hard] = -1           # keep HDBSCAN noise as -1
    labels_viz[~hard & soft] = -2   # soft anomalies as -2
    
    clustering_inspector.write_clusters_json(
        out_path="out/clusters.json",
        file_paths=file_paths,
        labels=labels,  # keep true cluster labels in JSON
        include_noise=True,
        extra_meta={"method": "positional weighted + HDBSCAN", "prob_threshold": prob_threshold},
    )
    
    clustering_inspector.write_cluster_previews_log(
        out_path="out/cluster_previews.log",
        file_paths=file_paths,
        labels=labels,  # previews based on real clusters
        normalized_samples=normalized_samples,
        N=10,
        K=100,
    )

    
    # Visualization uses labels_viz so anomalies are clearly separated
    clustering_inspector.visualize_clusters_2d(
        X=X,
        labels=labels_viz,
        out_png="out/clusters_2d.png",
        sample_max=5000,
    )
    
    clustering_visualizer.umap_plotly_scatter(
        X, file_paths, labels_viz, normalized_samples
    )
    #clustering_visualizer.cluster_size_distribution_plotly(labels=labels)


if __name__ == "__main__":
    main()
