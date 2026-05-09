# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 15:26:03 2026

@author: chodo
"""

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import IssueLoader
import statistics

class ExperimentsEvaluator:
    def __init__(self):
        self.metrics = {}
    
    def evaluate(self, incident, rca, retrieved):
        target_chunks_unique, target_chunks_all = incident.get_relevant_chunks()
        target = incident.get_target()
        metrics = eval_prec_rec(pred=rca, targ=target)
        eval_db_recall(METRICS = metrics
                        , target_rca = target
                        , retrieved_chunks=retrieved
                        , relevant_all = target_chunks_all
                        , relevant_unique = target_chunks_unique)
        self.add_metrics(metrics)
    
    def add_metrics(self, metrics):
        for k in metrics:
            if k not in self.metrics:
                self.metrics[k] = []
            self.metrics[k].append(metrics[k])
    
    def get_results(self):
        results = {}
        for k in self.metrics:
            results[k] = metric_statistics(self.metrics[k])
        return results
    
    def log_results(self, dest, res_name):
        results = self.get_results()
        TS = datetime.now().strftime("%Y%m%d_%H%M%S")+"-"
        with open(dest+TS+res_name, "w", encoding="utf-8") as fp:
            json.dump(results, fp=fp)

def metric_statistics(arr:list):
    return {"mean":sum(arr)/len(arr)
            , "median":statistics.median(arr)}

def src_cid(sample):
    src = sample["source_path"]
    cid = sample["chunk_id"]
    return src, cid

def safe_len_diff(ar1, ar2):
    return safe_div(len(ar1), len(ar2))

def safe_div(n1, n2):
    return 0 if n2 == 0 else n1/n2

def eval_db_recall(METRICS, target_rca, retrieved_chunks, relevant_all, relevant_unique):
    TM = target_manager(target=target_rca)
    r2 = []# relevant unique
    rn = []# relevant all
    for r in retrieved_chunks:
        lines = r["content_json"]
        for l in IssueLoader.line_in_content(content=lines):
            c2, cn = TM.log_all_at_once(l)
            if c2 and r not in r2:
                r2.append(r)
            if cn and r not in rn:
                rn.append(r)
    METRICS["recall relevant unique"] = safe_len_diff(r2, relevant_unique)
    METRICS["precission relevant unique"] = safe_len_diff(r2, retrieved_chunks)
    METRICS["recall relevant all"] = safe_len_diff(rn, relevant_all)
    METRICS["precission relevant all"] = safe_len_diff(rn, retrieved_chunks)
    _res, coverages =TM.result_as_dict()
    for k in coverages:
        METRICS["Reference recall ["+k+"]"] = coverages[k]


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
        print(key, value)
        rouge_metr = {"precision":value.precision, "recall":value.recall, "F1":value.fmeasure}
        for k in rouge_metr:
            jsonscores[key+"-"+k] = rouge_metr[k]
    return jsonscores

import re
def _over_normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"""[<>,.+;=\[\]()\-`]+""", "", text)
    text = re.sub(r"""[:/\\*\n\t"']+""", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
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
    over_pred = _over_normalize(pred)
    over_targ = _over_normalize(targ)
    rouge_score = rouge_eval(pred, targ)
    pred = _lemmatize(over_pred)
    targ = _lemmatize(over_targ)
    #bleu_score = bleu_eval(pred, targ)
    #print(rouge_score)
    #print("evaluating",len(pred),"x",len(targ))
    rel_ret = relevant_retrieved(pred, targ)
    recall = rel_ret/len(pred)
    precision = rel_ret/len(targ)
    metrics={"recall":recall
            ,"precision":precision}
    for k in rouge_score:
        metrics[k] = rouge_score[k]
    log(over_pred, over_targ, metrics=metrics)
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
        self.line_target_all = []
        for t in target.split("\n"):
            t = t.strip()
            if len(_over_normalize(t)) > 5:# threshold
                self.line_target_all.append(t)
        self.found_lines2 = []
        # len:
        self._len_word_target = _word_len(target)
        self._len_target = len(target)
        self._len_line_target = len(self.line_target)
        # counters:
        self._counter_word = 0
        self._counter_subline = 0
    
    def log_all_at_once(self, line):
        self.log_in_line(line)
        c2 = self.log_in_line2(line)
        cn = self.log_in_line_nonrem(line)
        self.log_in_word(line)
        return c2, cn
    
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
    
    def log_in_line_nonrem(self, line):
        contribution = False
        line = line.strip()
        if len(_over_normalize(line)) < 5:
            return contribution
        for i in range(len(self.line_target_all)):
            if line in self.line_target_all[i]:
                contribution = True
        return contribution
    
    def log_in_word(self, line):
        for word in line.split(" "):
            self.target = self.target.replace(" "+word+" ", "")# sole words
    
    
    def result(self):
        diff_target = self._len_target - len(self.target)
        new_len_line_target = len(self.found_lines)
        new_len_line_target_2 = len(self.found_lines2)
        new_words_found = self._len_word_target - _word_len(self.target)
        return self._len_target, diff_target, self._len_word_target, new_words_found, self._len_line_target, new_len_line_target, new_len_line_target_2
    
    def result_as_dict(self):
        TM_len_target, diff_target, TM_len_word_target, TM_new_words_found, TM_len_line_target, TM_new_len_line_target, TM_new_len_line_target_2=self.result()
        results = {
                "reference [characters]":TM_len_target
                ,"matched [characters]":diff_target
                ,"reference [words]":TM_len_word_target
                ,"matched [words]":TM_new_words_found
                ,"reference [lines]":TM_len_line_target
                ,"matched [lines]":TM_new_len_line_target
                ,"matched as subset [lines]":TM_new_len_line_target_2
            }
        coverage = {
            "character":    safe_div(diff_target,               TM_len_target)
            ,"words":       safe_div(TM_new_words_found,        TM_len_word_target)
            ,"lines":       safe_div(TM_new_len_line_target,    TM_len_line_target)
            ,"sublines":    safe_div(TM_new_len_line_target_2,  TM_len_line_target)
            }
        return results, coverage