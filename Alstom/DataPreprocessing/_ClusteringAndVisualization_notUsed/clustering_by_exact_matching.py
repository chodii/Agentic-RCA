# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 14:28:59 2026

@author: chodo
"""

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

# 1) Remove only angle brackets, keep the content: <var> -> var
ANGLE_RE = re.compile(r"[<>]")

# 2) Tokenizer: words OR single punctuation symbols
#    - \w+ catches letters/digits/underscore sequences
#    - [^\w\s] catches any single non-word, non-space char (punctuation)
TOKEN_RE = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)

def _tokenize_structural(text: str):
    text = ANGLE_RE.sub("", text)
    return TOKEN_RE.findall(text)

def compute_tf_idf_index(normalized_samples, file_paths):
    # One document per file (same as you had)
    documents = [" ".join(normalized_samples[p]) for p in file_paths]

    print(f"Vectorizing {len(documents)} files (TOKEN n-grams)...")

    vectorizer = TfidfVectorizer(
        tokenizer=_tokenize_structural,
        preprocessor=None,      # don't let sklearn lowercase/strip in unexpected ways
        token_pattern=None,     # IMPORTANT: disable built-in token pattern
        ngram_range=(2, 5),     # captures "t1 after t2 ..." structure (tuneable)
        min_df=2,
        max_df=0.95,
        lowercase=False         # keep case unless you *want* case-insensitive templates
    )

    X = vectorizer.fit_transform(documents)
    print("TF-IDF shape:", X.shape)
    return X

def cluster_DBSCAN(X):
    print("Running DBSCAN clustering...")
    clustering = DBSCAN(
        eps=0.35,          # start here since it's what you used; you may retune
        min_samples=10,
        metric="cosine"
    )
    labels = clustering.fit_predict(X)
    print("Number of clusters (excluding noise):", len(set(labels)) - (1 if -1 in labels else 0))
    print("Noise points:", np.sum(labels == -1))
    return labels


if __name__ == "__main__":
    import main_cluster
    main_cluster.main()