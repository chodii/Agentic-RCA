# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Created on Sun Feb 15 18:06:45 2026

@author: chodo
"""


from pathlib import Path
from collections import defaultdict

import json
from typing import Dict, List, Sequence, Union, Optional, Any

import numpy as np
import matplotlib.pyplot as plt


def inspect_clusters(file_paths, labels):
    from collections import defaultdict
    clusters = defaultdict(list)
    
    for path, label in zip(file_paths, labels):
        clusters[label].append(path)
    
    for label, files in clusters.items():
        print("\n==============================")
        print(f"Cluster {label} — {len(files)} files")
        print("==============================")
        for f in files[:5]:  # preview
            print(f)

def write_clusters_json(
    out_path: Union[str, Path],
    file_paths: Sequence[Path],
    labels: Sequence[int],
    *,
    include_noise: bool = True,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Writes a JSON report with *all* files per cluster and no file content.

    Output schema (example):
    {
      "meta": {...},
      "clusters": {
        "0": {"count": 123, "files": ["...","..."]},
        "-1": {"count": 45, "files": ["...","..."]}
      }
    }
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    clusters: Dict[int, List[str]] = defaultdict(list)
    for p, lab in zip(file_paths, labels):
        lab_i = int(lab)
        if lab_i == -1 and not include_noise:
            continue
        clusters[lab_i].append(str(Path(p)))

    # Sort clusters by size desc, noise last
    cluster_items = list(clusters.items())
    cluster_items.sort(key=lambda kv: (kv[0] == -1, -len(kv[1]), kv[0]))

    clusters_out: Dict[str, Any] = {}
    for lab, files in cluster_items:
        files_sorted = sorted(files)
        clusters_out[str(lab)] = {"count": len(files_sorted), "files": files_sorted}

    meta = {
        "total_files": len(file_paths),
        "unique_labels": len(set(int(x) for x in labels)),
        "noise_label": -1,
        "include_noise": include_noise,
    }
    if extra_meta:
        meta.update(extra_meta)

    payload = {"meta": meta, "clusters": clusters_out}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote JSON cluster report: {out_path}")


def write_cluster_previews_log(
    out_path: Union[str, Path],
    file_paths: Sequence[Path],
    labels: Sequence[int],
    normalized_samples: Dict[Path, List[str]],
    *,
    N: int = 10,
    K: int = 100,
    include_noise: bool = True,
) -> None:
    """
    Writes a .log file that contains cluster summaries + preview snippets
    (first N files per cluster, first K chars per file). No full content.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    clusters: Dict[int, List[Path]] = defaultdict(list)
    for p, lab in zip(file_paths, labels):
        lab_i = int(lab)
        if lab_i == -1 and not include_noise:
            continue
        clusters[lab_i].append(Path(p))

    # Sort clusters by size desc, noise last
    cluster_items = list(clusters.items())
    cluster_items.sort(key=lambda kv: (kv[0] == -1, -len(kv[1]), kv[0]))

    lines: List[str] = []
    lines.append("CLUSTER PREVIEWS")
    lines.append(f"Total files: {len(file_paths)}")
    lines.append(f"Preview policy: first N={N} files per cluster, first K={K} chars")
    lines.append("")

    for lab, files in cluster_items:
        lines.append("=" * 80)
        lines.append(f"Cluster {lab} (count={len(files)})")
        lines.append("=" * 80)

        for i, p in enumerate(sorted(files)[:N]):
            sample_lines = normalized_samples.get(p)
            if not sample_lines:
                preview = "(no normalized preview available)"
            else:
                text = "\n".join(sample_lines)
                preview = text[:K].replace("\n", "\\n")
            lines.append(f"{i+1:02d}. {p}")
            lines.append(f"    preview: {preview}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote preview log: {out_path}")

def visualize_clusters_2d(
    X,
    labels,
    *,
    out_png="clusters_2d.png",
    sample_max=5000,
    random_state=42,
):

    labels = np.asarray([int(x) for x in labels])
    n = labels.shape[0]

    rng = np.random.default_rng(random_state)

    # Optional sampling for large datasets
    if n > sample_max:
        idx = rng.choice(n, size=sample_max, replace=False)
        labels_s = labels[idx]
        X_s = X[idx]
        print(f"Visualizing sample {sample_max}/{n}")
    else:
        labels_s = labels
        X_s = X

    if hasattr(X_s, "toarray"):
        X_dense = X_s.toarray()
    else:
        X_dense = np.asarray(X_s)

    # Dimensionality reduction
    coords = None
    reducer_name = None

    try:
        import umap
        reducer = umap.UMAP(
            n_components=2,
            metric="cosine",
            random_state=random_state,
        )
        coords = reducer.fit_transform(X_dense)
        reducer_name = "UMAP"
    except Exception:
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=2, random_state=random_state)
        coords = reducer.fit_transform(X_dense)
        reducer_name = "PCA"

    plt.figure()

    unique_labels = sorted(set(labels_s))
    handles = []

    for lab in unique_labels:
        mask = labels_s == lab
        cluster_size = np.sum(mask)

        label_name = f"Cluster {lab}" if lab != -1 else "Noise (-1)"
        label_name += f" (n={cluster_size})"

        scatter = plt.scatter(
            coords[mask, 0],
            coords[mask, 1],
            s=5,
            label=label_name,
        )
        handles.append(scatter)

    plt.title(f"Cluster Visualization ({reducer_name})")
    plt.xlabel("dim-1")
    plt.ylabel("dim-2")

    # Place legend outside if many clusters
    if len(unique_labels) > 10:
        plt.legend(
            loc="upper left",
            bbox_to_anchor=(1.05, 1),
            fontsize="small",
        )
        plt.tight_layout()
    else:
        plt.legend()

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"Wrote cluster visualization: {out_png}")

