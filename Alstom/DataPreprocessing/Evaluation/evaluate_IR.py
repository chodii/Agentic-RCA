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


def _word_len(text):
    text = text.replace("\n", " ").split(" ")
    word_len = 0
    for t in text:
        if len(t)>0:
            word_len += 1
    return word_len
    
class target_manager:
    def __init__(self, target:str):
        self.target = target# 100% word coverage
        self.line_target = target.split("\n")# 60% line coverage
        self.line_target_2 = target.split("\n")
        self.found_lines2 = []
        # len:
        self._len_word_target = _word_len(target)
        self._len_target = len(target)
        self._len_line_target = len(self.line_target)
    
    def log_in_line(self, line):
        new_line_target = []
        for i in range(len(self.line_target)):
            if not self.line_target[i] == line:
                new_line_target.append(self.line_target[i])
        self.line_target = new_line_target
    
    def log_in_line2(self, line):
        """ line: <line>
        """
        new_line_target = []
        for i in range(len(self.line_target_2)):
            if line in self.line_target_2[i]:
                self.found_lines2.append(line)
            else:
                new_line_target.append(self.line_target_2[i])
        self.line_target_2 = new_line_target
    
    def log_in_word(self, line):
        for word in line.split(" "):
            self.target.replace(word, "")
    
    
    def result(self):
        new_len_target = len(self.target)
        new_len_line_target = len(self.line_target)
        new_len_line_target_2 = len(self.line_target_2)
        return self._len_target, new_len_target, self._len_word_target, _word_len(self.target), self._len_line_target, new_len_line_target, new_len_line_target_2
    