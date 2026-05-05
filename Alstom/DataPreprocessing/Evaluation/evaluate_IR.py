# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 15:26:03 2026

@author: chodo
"""
from nltk.translate.bleu_score import corpus_bleu, sentence_bleu, SmoothingFunction

from rouge_score import rouge_scorer
# REPLACE BLEU with ROGUE
def rouge_eval(pred, targ):
    scorer = rouge_scorer.RougeScorer(
            ['rouge1', 'rouge2', 'rouge3', 'rouge4'],
            use_stemmer=True
        )
    rouge_scores = scorer.score(targ, pred)
    jsonscores = {}
    for key, value in rouge_scores.items():
        jsonscores[key] = {"precision":value.precision, "recall":value.recall, "F1":value.F1}
    return jsonscores

import re
def _over_normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"""[:<>,.+;=]+""", "", text)
    text = re.sub(r"""[/\\()\-*\n\t"']+""", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
def _lemmatize(txt):
    lemmatizer = WordNetLemmatizer()
    tokens = word_tokenize(txt)
    lemmatized_words = [lemmatizer.lemmatize(word) for word in tokens]
    return lemmatized_words

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

def eval_prec_rec(pred:str, targ:str):
    #pred = _normlize(pred)
    #targ = _normlize(targ)
    pred = _over_normalize(pred)
    targ = _over_normalize(targ)
    rouge_score = rouge_eval(pred, targ)
    pred = _lemmatize(pred)
    targ = _lemmatize(targ)
    #bleu_score = bleu_eval(pred, targ)
    #print(rouge_score)
    #print("evaluating",len(pred),"x",len(targ))
    rel_ret = relevant_retrieved(pred, targ)
    recall = rel_ret/len(pred)
    precision = rel_ret/len(targ)
    metrics={"recall":recall
            ,"precision":precision
            ,"ROGUE":rouge_score}
    log(pred, targ, metrics=metrics)
    return metrics

def relevant_retrieved(pred:list, targ:list):
    rec = 0
    for p in pred:
        if p in targ:
            #print(p)
            rec += 1
    return rec


def _word_len(text):
    text = text.replace("\n", " ").split(" ")
    word_len = 0
    for t in text:
        if len(t)>0:
            word_len += 1
    return word_len
import os
import json
from datetime import datetime
DEST = "out/eval/"
def log(pred, targ, metrics):
    os.makedirs(DEST, exist_ok=True)
    result_log = DEST+"e"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json"
    obj = {"pred":pred, "targ":targ, "metrics":metrics}
    with open(result_log, "w", encoding="utf-8") as fp:
        json.dump(obj, fp)


class target_manager:
    def __init__(self, target:str):
        self.target = target# 100% word coverage
        self.line_target = target.split("\n")# 60% line coverage
        self.found_lines = []
        self.line_target_2 = target.split("\n")
        self.found_lines2 = []
        # len:
        self._len_word_target = _word_len(target)
        self._len_target = len(target)
        self._len_line_target = len(self.line_target)
        # counters:
        self._counter_word = 0
        self._counter_subline = 0
        
    def log_in_line(self, line):
        new_line_target = []
        for i in range(len(self.line_target)):
            if self.line_target[i].strip() == line.strip():
                self.found_lines.append(self.line_target[i])
            else:
                new_line_target.append(self.line_target[i])
        self.line_target = new_line_target
    
    def log_in_line2(self, line):
        """ line: <line>
        """
        contribution = False
        new_line_target = []
        for i in range(len(self.line_target_2)):
            if line in self.line_target_2[i]:
                self.found_lines2.append(line)
                contribution = True
            else:
                new_line_target.append(self.line_target_2[i])
        self.line_target_2 = new_line_target
        return contribution
    
    def log_in_word(self, line):
        for word in line.split(" "):
            self.target = self.target.replace(" "+word+" ", "")# sole words
    
    
    def result(self):
        new_len_target = self._len_target - len(self.target)
        new_len_line_target = len(self.found_lines)
        new_len_line_target_2 = len(self.found_lines2)
        new_words_found = self._len_word_target - _word_len(self.target)
        return self._len_target, new_len_target, self._len_word_target, new_words_found, self._len_line_target, new_len_line_target, new_len_line_target_2
    