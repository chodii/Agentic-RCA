# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 15:26:03 2026

@author: chodo
"""
from nltk.translate.bleu_score import corpus_bleu, sentence_bleu, SmoothingFunction
def bleu_eval(hypothesis, reference):
    #hypothesis = tokenize_rca_text(pred)
    #reference = tokenize_rca_text(targ)

    smoothie = SmoothingFunction().method4

    return {
        "bleu_1": sentence_bleu([reference], hypothesis, weights=(1.0, 0, 0, 0), smoothing_function=smoothie),
        "bleu_2": sentence_bleu([reference], hypothesis, weights=(0.5, 0.5, 0, 0), smoothing_function=smoothie),
        "bleu_3": sentence_bleu([reference], hypothesis, weights=(1/3, 1/3, 1/3, 0), smoothing_function=smoothie),
        "bleu_4": sentence_bleu([reference], hypothesis, weights=(0.25, 0.25, 0.25, 0.25), smoothing_function=smoothie),
    }

def _normlize(txt):
    new_arr = []
    lines = txt.lower().split("\n")
    for l in  lines:
        arr = l.strip().split(" ")
        for p in arr:
            p = p.strip()
            if len(p) == 0:
                continue
            new_arr.append(p)
    return new_arr

def eval_prec_rec(pred:list, targ:list):
    pred = _normlize(pred)
    targ = _normlize(targ)
    bleu_score = bleu_eval(pred, targ)
    print(bleu_score)
    print("evaluating",len(pred),"x",len(targ))
    rel_ret = relevant_retrieved(pred, targ)
    recall = rel_ret/len(pred)
    precission = rel_ret/len(targ)
    return recall, precission

def relevant_retrieved(pred:list, targ:list):
    rec = 0
    for p in pred:
        if p in targ:
            print(p)
            rec += 1
    return rec