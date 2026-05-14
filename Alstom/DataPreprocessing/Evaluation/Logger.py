# -*- coding: utf-8 -*-
"""
Created on Thu May 14 01:11:01 2026

@author: chodo
"""
from datetime import datetime
import json
import os
LOGGER="LOGGER.json"

def assistant_msgs(conversation):
    msgs = []
    for msg in conversation:
        role = msg["role"]
        if role == "assistant":
            cont = msg["content"]
            if cont and type(cont) == str and len(cont) > 4:
                msgs.append(cont)
    return msgs

class logger:
    def __init__(self, dest, tag):
        self.res_folder = dest+datetime.now().strftime("%Y%m%d_%H%M%S")+"-"+tag.split(".")[0]+"/"
        os.makedirs(self.res_folder, exist_ok=True)
        self.resname = self.res_folder + LOGGER
        print(self.resname)
        self.samples = []
    
    def log(self, incident, rca, retrieved, conversation):
        ret_lines = []
        for content in retrieved:
            content = content['content_json']
            for line in content:
                ret_lines.append(content[-1])
        sample = {"incident id": incident.__str__()
            , "reference":incident.get_target()
            , "generated":rca
            , "retrieved":ret_lines
            , "assistant": assistant_msgs(conversation=conversation)}
        self.samples.append(sample)
        with open(self.resname, "w") as fp:
            json.dump(obj=self.samples, fp=fp)

def prep(txt):
    lines = []
    for line in txt.split("\n"):
        if "<time>" in line:
            line = line.split("<time>")[-1]
        line = line.strip()
        if len(line) > 0:
            lines.append(line)
    return lines

def cov_PT(targ_l, pred_l):
    cov = 0
    for tar in targ_l:
        mxcov = 0
        for pre in pred_l:
            if pre in tar:
                mxcov = max(mxcov, len(pre))
        cov += mxcov
    return cov

def evaluate_txt(pred, targ):
    pred_l = prep(pred)
    targ_l = prep(targ)
    tl = sum([len(t) for t in targ_l])
    pl = sum([len(p) for p in pred_l])
    cv = cov_PT(targ_l=targ_l, pred_l = pred_l)
    print("cov", cv, str(cv/tl)[:5], tl, pl)
    return cv

def zero_port(arr):
    zeros = 0
    for a in arr:
        if a == 0:
            zeros+=1
    return zeros

import statistics
def eva(pth):
    trans = transform(pth)
    i = 0
    cts = []
    ats = []
    pts = []
    for i in range(len(trans["generated"])):
        pred = trans["generated"][i]
        targ = trans["reference"][i]
        ret = trans["retrieved"][i]
        ass = trans["assistant"][i]
        ct = evaluate_txt(ret, targ)
        at = evaluate_txt(ass, targ)
        pt = evaluate_txt(pred, targ)
        print("---")
        cts.append(ct)
        ats.append(at)
        pts.append(pt)
    print("retriever ", zero_port(cts))
    print("assistant ", zero_port(ats))
    print("model ", zero_port(pts))
    


def transform(pth):
    with open(pth, "r") as fp:
        samples = json.load(fp)
    trans = {}
    for s in samples:
        for k in s:
            if k not in trans:
                trans[k] = []
            trans[k].append(s[k])
    retr = []
    for r in trans["retrieved"]:
        s = ""
        for l in r:
            s += l[-1]+"\n"
        retr.append(s)
    trans["retrieved"] = retr
    ass = []
    for a in trans["assistant"]:
        s = ""
        for l in a:
            s += l+"\n"
        ass.append(s)
    trans["assistant"] = ass
        
    return trans

def test(pth):
    trans = transform(pth)
    aspect = ["generated", "retrieved", "reference", "assistant"]#"generated", "retrieved", "reference", "assistant"]
    for a in aspect:
        print("\n",a+":")
        for s in ["emergency", "restart"]:
            i = 0
            j = 0
            for g in trans[a]:
                if s in g.lower():
                    i+=1
                    print(j,i)
                j+=1
            #print(s+":",i)


rut = r"C:\Users\chodo\Documents\Studies\Projects\Sweden\MasterThesis/"
def main():
    case1 = r"out/chunked_3000/20260514_133443--VALIDATION_results/LOGGER.json"
    case2 = r"out/chunked_3000/20260514_140816--VALIDATION_results/LOGGER.json"
    case3 = "out/chunked_3000/20260514_143143--VALIDATION_results/LOGGER.json"
    case4 = "out/chunked_3000/20260514_144503--VALIDATION_results/LOGGER.json"
    case5 = "out/chunked_3000/20260514_145814--VALIDATION_results/LOGGER.json"
    case6_12sampl = "out/chunked_3000/20260514_151732--VALIDATION_results/LOGGER.json"
    case7 = "out/chunked_3000/20260514_161422--VALIDATION_results/LOGGER.json"
    case8 = "out/chunked_3000/20260514_164025--VALIDATION_results/LOGGER.json"
    
    case9_ass = "out/chunked_3000/20260514_173251--VALIDATION_results/LOGGER.json"
    case10 = "out/chunked_3000/20260514_182535--VALIDATION_results/LOGGER.json"
    case11_gpt5_mini = "out/chunked_3000/20260514_192035--VALIDATION_results/LOGGER.json"
    
    case_experimemnts_gpt4omini_3000 = "out/chunked_3000/20260514_201646--EXPERIMENT_results/LOGGER.json"
    pth= rut + case10
    test(pth)
    eva(pth)
