# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 18:29:37 2026

@author: chodo
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Union
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
from urllib.parse import quote
from pathlib import Path
import os

def path_to_file_url(p: Path) -> str:
    # Ensure absolute, normalize separators
    p = p.resolve()
    # Path.as_posix() gives forward slashes
    posix_path = p.as_posix()
    # On Windows, as_posix() yields like C:/Users/...
    return "file:///" + quote(posix_path, safe="/:")  # keep / and : unescaped

def path_to_vscode_url(p: Path) -> str:
    p = p.resolve()
    posix_path = p.as_posix()
    return "vscode://file/" + quote(posix_path, safe="/:")


def umap_plotly_scatter(
    X,
    file_paths: Sequence[Path],
    labels: Sequence[int],
    normalized_samples: Dict[Path, List[str]],
    *,
    out_html: Union[str, Path] = "out/umap_clusters.html",
    preview_lines: int = 3,     # multiline preview size
    preview_chars: int = 300,   # max chars total in preview
    sample_max: int = 20000,
    random_state: int = 42,
    umap_n_neighbors: int = 15,
    umap_min_dist: float = 0.4,
    umap_spread: float = 0.45,
    open_mode: str = "file",    # "file" | "vscode"
) -> None:
    """
    Interactive UMAP scatter:
    - Hover shows: cluster + multiline preview (no filepath shown)
    - Click opens file (best-effort):
        open_mode="file"  -> tries file:///path (browser may block)
        open_mode="vscode"-> tries vscode://file/path
    Saves a self-contained HTML.

    Requires: umap-learn, plotly, pandas
    """
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)

    labels = np.asarray([int(x) for x in labels])
    n = len(file_paths)
    if n != len(labels):
        raise ValueError(f"file_paths length ({n}) != labels length ({len(labels)})")

    rng = np.random.default_rng(random_state)

    # Optional sampling
    if n > sample_max:
        idx = rng.choice(n, size=sample_max, replace=False)
        idx.sort()
        file_paths_s = [Path(file_paths[i]) for i in idx]
        labels_s = labels[idx]
        X_s = X[idx]
        print(f"UMAP: using sample {sample_max}/{n}")
    else:
        file_paths_s = [Path(p) for p in file_paths]
        labels_s = labels
        X_s = X

    # Dense for UMAP
    X_dense = X_s.toarray() if hasattr(X_s, "toarray") else np.asarray(X_s)

    import umap  # pip install umap-learn

    reducer = umap.UMAP(
        n_components=2,
        metric="cosine",
        random_state=random_state,
        n_neighbors=umap_n_neighbors,
        min_dist=umap_min_dist,
        spread=umap_spread,
    )
    coords = reducer.fit_transform(X_dense)

    # Build multiline preview: take first preview_lines lines, then truncate to preview_chars.
    previews = []
    for p in file_paths_s:
        lines = normalized_samples.get(p, [])
        text = "\n".join(lines[:preview_lines]).strip()
        if len(text) > preview_chars:
            text = text[:preview_chars] + "…"
        # Plotly hover wants <br> for new lines
        previews.append(text.replace("\n", "<br>"))

    df = pd.DataFrame(
        {
            "x": coords[:, 0],
            "y": coords[:, 1],
            "cluster": labels_s.astype(int),
            "preview": previews,
            "filepath": [str(p) for p in file_paths_s],  # not shown on hover, used for click
        }
    )
    
    df["file_url"] = [path_to_file_url(Path(p)) for p in file_paths_s]
    df["vscode_url"] = [path_to_vscode_url(Path(p)) for p in file_paths_s]
    
    
    # Make cluster categorical for consistent legend coloring
    df["cluster_str"] = df["cluster"].astype(str).where(df["cluster"] != -1, "Noise (-1)")

    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="cluster_str",
        title="UMAP clusters (hover = cluster + preview, click = open file)",
    )

    # Put the real filepath into customdata so it’s available to click JS
    fig.update_traces(
        customdata=np.stack([df["filepath"].to_numpy()], axis=-1),
        hovertemplate=(
            "Group: %{marker.color}<br>"
            "%{customdata[0]|s}<extra></extra>"  # placeholder, replaced below
        )
    )
    
    fig.update_traces(
        customdata=np.stack([df["file_url"].to_numpy(), df["vscode_url"].to_numpy()], axis=-1)
    )   

    
    # Replace hovertemplate properly (Plotly Express uses marker.color for color values, not label)
    # We'll set hovertemplate per trace with the text we want:
    # Show only: "Group: <cluster>" + preview (multiline)
    for trace in fig.data:
        # This trace corresponds to one cluster_str value; trace.name is the legend label.
        trace.hovertemplate = (
            f"Group: {trace.name}<br>"
            "%{text}<extra></extra>"
        )

    # Provide the preview as "text" for hover
    fig.update_traces(text=df["preview"])

    fig.update_traces(marker=dict(size=6))

    # Export to HTML + inject JS click handler
    html = pio.to_html(fig, include_plotlyjs="cdn", full_html=True)

    # Click handler: open file path
    # Note: file:// opens may be blocked by browser. vscode:// works if configured.
    js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
  var plot = document.getElementsByClassName('plotly-graph-div')[0];
  if (!plot) return;

  plot.on('plotly_click', function(data) {
    try {
      var cd = data.points[0].customdata;
      if (!cd || cd.length < 2) return;

      var fileUrl = cd[0];
      var vscodeUrl = cd[1];

      // Try VS Code first
      window.open(vscodeUrl, "_blank");

      // Fallback to file URL
      setTimeout(function() {
        window.open(fileUrl, "_blank");
      }, 200);

    } catch (e) {
      console.error("Click open failed:", e);
    }
  });
});
</script>
"""

    out_html.write_text(html.replace("</body>", js + "\n</body>"), encoding="utf-8")
    print(f"Wrote interactive UMAP HTML: {out_html}")


if __name__ == "__main__":
    import main_cluster
    main_cluster.main()