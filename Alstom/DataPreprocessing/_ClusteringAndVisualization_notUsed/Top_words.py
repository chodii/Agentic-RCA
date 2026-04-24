# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Created on Sun Feb 15 20:57:37 2026

@author: chodo
"""

import argparse
import re
from collections import Counter
from pathlib import Path
import matplotlib.pyplot as plt

import os

def to_windows_long_path(p: Path) -> str:
    """
    Convert a path to Windows extended-length form if needed.
    Works around MAX_PATH issues by using \\?\ prefix on absolute paths.
    """
    s = str(p)
    if os.name != "nt":
        return s

    # Must be absolute for \\?\ prefix
    try:
        abs_s = str(p.resolve())
    except Exception:
        abs_s = str(p.absolute())

    # Already extended-length
    if abs_s.startswith("\\\\?\\"):
        return abs_s

    # UNC path (network share)
    if abs_s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + abs_s.lstrip("\\")
    return "\\\\?\\" + abs_s


def safe_open_text(p: Path):
    """
    Open *any* file as text, best-effort.
    - Uses long-path prefix on Windows
    - Ignores decoding issues
    """
    long_p = to_windows_long_path(p)
    return open(long_p, "r", encoding="utf-8", errors="ignore")



def extract_words(text):
    """
    Extract lowercase alphabetic words.
    """
    return re.findall(r"\b[a-zA-Z]+\b", text.lower())


def process_dataset(root_path):
    """
    Walk recursively through all files and count words globally.
    """
    counter = Counter()
    for file_path in Path(root_path).rglob("*"):
        if file_path.is_file():
            try:
                with safe_open_text(file_path) as f:
                    text = f.read()
                words = extract_words(text)
                counter.update(words)
            except (FileNotFoundError, OSError, PermissionError) as e:
                print(f"Skipping: {file_path}  ({type(e).__name__}: {e})")
    

    return counter

import json
def log_to_json(N, words, counts, top_n):
    output_data = {
        "top_n": N,
        "results": [
            {"word": word, "count": count}
            for word, count in top_n
        ]
    }
    
    output_file = "out/top_words.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"Saved results to {output_file}")
    

def main():
    parser = argparse.ArgumentParser(
        description="Retrieve top N words across an entire dataset and plot histogram."
    )
    parser.add_argument(
        "--dataset_path",
        default="C:\\Datasets\\alstomu\\",
        help="Root folder of dataset"
    )
    
    parser.add_argument(
        "--N",
        type=int,
        default=300,
        help="Number of top words to display"
    )
    args = parser.parse_args()

    print("Processing dataset...")

    counter = process_dataset(args.dataset_path)

    if not counter:
        print("No words found in dataset.")
        return

    top_n = counter.most_common(args.N)
    words, counts = zip(*top_n)
    
    log_to_json(args.N, words, counts, top_n)
    
    # Plot
    plt.figure()
    plt.bar(words[:10], counts[:10])
    plt.xticks(rotation=45)
    plt.xlabel("Words")
    plt.ylabel("Frequency")
    plt.title(f"Top {args.N} Words Across Dataset")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
