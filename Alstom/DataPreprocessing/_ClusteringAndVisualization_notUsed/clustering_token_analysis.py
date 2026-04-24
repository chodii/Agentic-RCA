# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 15:34:49 2026

@author: chodo
"""

import re
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt

# Replace < and > by space (so <A><B> -> A B)
ANGLE_RE = re.compile(r"[<>]")

# Token rule:
# - sequences of alphanumeric characters -> one token
# - every single non-alphanumeric, non-whitespace character -> separate token
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9\s]", flags=re.UNICODE)


def tokenize_structural(text: str):
    text = ANGLE_RE.sub(" ", text)
    text = text.lower()
    return TOKEN_RE.findall(text)


def analyze_dataset(normalized_samples, k = 20):
    print("\n=== DATASET TOKENIZATION ANALYSIS ===\n")

    token_counter = Counter()
    line_lengths = []

    total_lines = 0
    total_tokens = 0

    for file_path, lines in normalized_samples.items():
        for line in lines:
            tokens = tokenize_structural(line)
            length = len(tokens)

            if length == 0:
                continue

            total_lines += 1
            total_tokens += length

            line_lengths.append(length)
            token_counter.update(tokens)

    # ---- Line statistics ----
    mean_len = np.mean(line_lengths)
    median_len = np.median(line_lengths)

    print(f"Total files: {len(normalized_samples)}")
    print(f"Total lines: {total_lines}")
    print(f"Total tokens: {total_tokens}")
    print(f"Distinct tokens: {len(token_counter)}")
    print(f"Mean line length (tokens): {mean_len:.2f}")
    print(f"Median line length (tokens): {median_len}")

    # ---- Line length histogram ----
    plt.figure()
    plt.hist(line_lengths, bins=50)
    plt.title("Histogram of Line Lengths (in tokens)")
    plt.xlabel("Line length")
    plt.ylabel("Frequency")
    plt.savefig("out/line_lengths_hist.pdf")
    plt.show()

    # ---- Top 15 tokens ----
    print("\nTop ",str(k)," most common tokens:")
    for token, count in token_counter.most_common(k):
        print(f"{token!r}: {count}")

    # ---- Unknown mass if k=20 ----
    top_k = token_counter.most_common(k - 1)  # last slot reserved for UNK
    top_k_tokens = {t for t, _ in top_k}
    unk_count = sum(c for t, c in token_counter.items() if t not in top_k_tokens)

    print(f"\nIf k={k}, tokens outside top-{k-1}: {unk_count}")

    # ---- Token frequency histogram (counts only) ----
    token_freqs = list(token_counter.values())

    plt.figure()
    plt.hist(token_freqs, bins=50)
    plt.title("Histogram of Token Frequencies")
    plt.xlabel("Token frequency")
    plt.ylabel("Number of tokens")
    plt.savefig("out/token_freq_hist.pdf")
    plt.show()
    print("\n=== END OF ANALYSIS ===\n")
    return top_k_tokens, median_len

if __name__ == "__main__":
    import main_cluster
    main_cluster.main()