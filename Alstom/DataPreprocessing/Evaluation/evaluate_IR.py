# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 15:26:03 2026

@author: chodo
"""
def eval_prec_rec(pred:list, targ:list):
    pred = [p.strip() for p in pred]
    targ = [t.strip() for t in targ]
    rel_ret = relevant_retrieved(pred, targ)
    recall = rel_ret/len(pred)
    precission = rel_ret/len(targ)
    return recall, precission

def relevant_retrieved(pred:list, targ:list):
    rec = 0
    for p in pred:
        if p in targ:
            rec += 1
    return rec