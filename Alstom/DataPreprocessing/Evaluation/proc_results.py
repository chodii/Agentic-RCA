# -*- coding: utf-8 -*-
"""
Created on Tue May 12 13:31:10 2026

@author: chodo
"""
import argparse
import json

import numpy as np
import matplotlib.pyplot as plt

def plot_radar(dict_a, dict_b, label_a, label_b, title, dest):
    # Ensure both dictionaries have the same keys
    if set(dict_a.keys()) != set(dict_b.keys()):
        raise ValueError("Both dictionaries must have the same keys.")

    labels = list(dict_a.keys())

    values_a = [dict_a[k] for k in labels]
    values_b = [dict_b[k] for k in labels]

    # Close the radar loop by repeating the first value
    values_a += values_a[:1]
    values_b += values_b[:1]

    # Angles for each axis
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    ax.plot(angles, values_a, linewidth=2, label=label_a)
    ax.fill(angles, values_a, alpha=0.25)

    ax.plot(angles, values_b, linewidth=2, label=label_b)
    ax.fill(angles, values_b, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    ax.set_title(title, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    ax.grid(True)

    plt.tight_layout()
    safename = title.replace(" ", "").replace("'s","")
    dest = dest+safename
    plt.savefig(fname=dest+".pdf")
    plt.show()

def calc_recall(data, k, tag, NORMALIZED):
    achieved = 0
    target_cov = 0
    for i in range(len(data)):
        achieved += data[i][0]
        target_cov += data[i][1]
    print(tag+" "+k+": recalled", achieved/len(data), ",\ttarget", target_cov/len(data))
    if NORMALIZED:
        recall = achieved/target_cov
    else:
        recall = achieved/len(data)
    print(k+":",recall)
    return recall

def compare(comparisons, tag, normalization):
    transformed_comp = {}
    for comp in comparisons:
        for k in comp:
            if k not in transformed_comp:
                transformed_comp[k] = []
            transformed_comp[k].append(comp[k])
    recalls = {}
    for k in transformed_comp:
        rcll = calc_recall(data=transformed_comp[k], k=k, tag=tag, NORMALIZED=normalization)
        recalls[k] = rcll
    return recalls

def show_comparisons(res_file_name):
    with open(res_file_name, "r", encoding="utf-8") as fp:
        res = json.load(fp)
    ret_comparisons = res["retriever_compared_metrics"]
    agent_comparisons = res["agent_compared_metrics"]
    dest = res_file_name.replace("\\","/")
    dest = dest.split(dest.split("/")[-1])[0]
    for normalization in [True, False]:
        note = ("Normalized" if normalization else "Absolute")
        print("\n","="*16,note, "="*16)
        retr_rec = compare(comparisons=ret_comparisons, tag="Retriever", normalization=normalization)
        print()
        agent_rec = compare(comparisons=agent_comparisons, tag="Agent", normalization=normalization)
        plot_radar(dict_a=retr_rec, dict_b=agent_rec, label_a="Retriever", label_b="Agent", title="Retriever's and Agent's Recall ("+note+")", dest=dest)

def parse_args():
    parser = argparse.ArgumentParser(
       description="Processing of the results.json file"
       )
    parser.add_argument(
         "-r", "--results",
         dest="results",
         default="results.json"
         ,help="The results.json file"
     )
    args = parser.parse_args()
    return args.results

def main():
    resultsfile = parse_args()
    show_comparisons(res_file_name=resultsfile)

if __name__ == "__main__":
    main()