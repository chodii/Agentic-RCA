# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 17:50:03 2026

@author: chodo
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import normalize
import numpy as np

def compute_ngram_index(normalized_samples, file_paths):
    documents = [
        " ".join(normalized_samples[p]) for p in file_paths
    ]
    print(f"Vectorizing {len(documents)} files (using n-grams)...")
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5))
    X = vectorizer.fit_transform(documents)
    print("TF-IDF shape:", X.shape)
    return X

def compute_tf_idf_index(normalized_samples, file_paths):
    # Convert normalized samples into documents (one document per file)
    #file_paths = list(normalized_samples.keys())
    documents = [
        " ".join(normalized_samples[p]) for p in file_paths
    ]
    
    print(f"Vectorizing {len(documents)} files...")
    
    # Character-level TF-IDF works better for structural similarity
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),   # captures structural patterns
        min_df=2,
        max_df=0.95
    )
    
    X = vectorizer.fit_transform(documents)
    print("TF-IDF shape:", X.shape)
    return X

def cluster_HDBSCAN(
    X,
    min_cluster_size=20,
    min_samples=20,
    metric="euclidean",
    cluster_selection_method="eom",
):
    import hdbscan
    import numpy as np

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_method=cluster_selection_method,
    )

    labels = clusterer.fit_predict(X)
    probs = clusterer.probabilities_
    outlier_scores = clusterer.outlier_scores_

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise = int(np.sum(labels == -1))

    print("HDBSCAN clusters (excluding noise):", n_clusters)
    print("Noise points:", noise)

    return labels, probs, outlier_scores



def cluster_DBSCAN(X,eps,min_samples):
    print("Running DBSCAN clustering...")
    clustering = DBSCAN(
        eps=eps,          # you may need to tune
        min_samples=min_samples,
        metric="cosine"
    )
    labels = clustering.fit_predict(X)
    print("Number of clusters (excluding noise):", len(set(labels)) - (1 if -1 in labels else 0))
    print("Noise points:", np.sum(labels == -1))
    return labels

def cluster_Agglomerative(X):
    from sklearn.cluster import AgglomerativeClustering
    print("Running Agglomerative clustering...")
    clustering = AgglomerativeClustering(
        n_clusters=5,  # adjust after inspection
        metric="cosine",
        linkage="average"
    )
    labels = clustering.fit_predict(X.toarray())
    return labels

    