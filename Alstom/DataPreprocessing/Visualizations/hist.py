# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 01:11:09 2026

@author: chodo
"""
import os
import re
import numpy as np
import matplotlib.pyplot as plt

DEST = "./"

def hist_from_array(array, x, y, title, bins=30, show=False):
    os.makedirs(DEST, exist_ok=True)

    data = np.asarray(array, dtype=float)
    data = data[np.isfinite(data)]  # remove NaN / inf

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

    # Normal histogram
    ax1.hist(data, bins=bins, edgecolor="black")
    ax1.set_xlabel(x)
    ax1.set_ylabel(y)
    ax1.set_title(title)

    # Same histogram, but logarithmic y-axis
    ax2.hist(data, bins=bins, edgecolor="black")
    ax2.set_xlabel(x)
    ax2.set_ylabel(y)
    ax2.set_title(title + " (log)")
    ax2.set_yscale("log")

    plt.tight_layout()

    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
    out_path = os.path.join(DEST, safe_title + ".pdf")

    plt.savefig(out_path, format="pdf")
    if show:
        plt.show()
    plt.close()

    return out_path
