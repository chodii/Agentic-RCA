# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 16:00:35 2026

@author: chodo
"""

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from DataPreprocessing import IssueLoader
from DataPreprocessing.Evaluation import evaluate_IR
from DataPreprocessing import AllChunker
from DataPreprocessing import _dataset_walker as dw
from DataPreprocessing.Visualizations import hist

from AI import AlstomAI
from AI import message_manager
import json
import argparse
import datetime

def coverage_analysis(old, new, tag, dest):
    covs = []
    for i in range(len(old)):
        cov = (new[i])/old[i]
        covs.append(cov)
    hist.hist_from_array_single(covs, x="Coverage of target output", y="Count", title="Potential "+tag+" coverage of target output", dest=dest)
    return covs

def coverage_analysis_api(incidents_json, chunking):
    if chunking is None:
        tag = "windowed_selection/"
    else:
        tag = "chunked_"+str(chunking)+"/"
    dest = "out/"+tag
    
    lens_orig = []
    word_lens_orig = []
    line_lens_oring = []
    
    lens_new = []
    word_lens_new = []
    line_lnes_new = []
    line_2_lnes_new = []
    incident_relevant_files = {}
    incident_all_relevant_files = {}
    for i,incident in enumerate(IssueLoader.load_incidents(incidents_json=incidents_json, chunk_size=chunking, OUT=dest)):
        print("\r",i,end="")
        srcs = incident.chunk_folder.replace("\\","/").split("/")[:-1]
        src = ""
        for s in srcs:
            src += s+"/"
        src += tag
        target = incident.get_target()
        target_manager = evaluate_IR.target_manager(target)
        contained_fp = []
        contained_fp_all = []
        for fp in dw.dataset_iterator(src):
            contained = False
            contained_all = False
            for line in IssueLoader.log_file_reader(fp):
                target_manager.log_in_line(line)
                target_manager.log_in_word(line)
                if target_manager.log_in_line2(line):
                    contained = True
                if target_manager.log_in_line_nonrem(line):
                    contained_all = True
            if contained:
                contained_fp.append(fp)
            if contained_all:
                contained_fp_all.append(fp)
        incident_relevant_files[incident.ts] = contained_fp
        incident_all_relevant_files[incident.ts] = contained_fp_all
        old_str_len, new_str_len, old_word_len, new_word_len, old_line_len, new_line_len, new_len_line_target_2 = target_manager.result()
        lens_orig.append(old_str_len)
        word_lens_orig.append(old_word_len)
        line_lens_oring.append(old_line_len)
        lens_new.append(new_str_len)
        word_lens_new.append(new_word_len)# word contained
        line_lnes_new.append(new_line_len)# line exact
        line_2_lnes_new.append(new_len_line_target_2)# line contained
    os.makedirs(dest, exist_ok=True)
    hist.hist_from_array_single(lens_orig, x="Length of target output", y="Count", title="Length of target [characters]", dest=dest)
    hist.hist_from_array_single(word_lens_orig, x="Length of target output", y="Count", title="Length of target [words]", dest=dest)
    hist.hist_from_array_single(line_lens_oring, x="Length of target output", y="Count", title="Length of target [lines]", dest=dest)
    coverage_analysis(lens_orig, lens_new, "character", dest=dest)
    coverage_analysis(word_lens_orig, word_lens_new, "word", dest=dest)
    coverage_analysis(line_lens_oring, line_lnes_new, "line exact", dest=dest)
    l2l_cov = coverage_analysis(line_lens_oring, line_2_lnes_new, "line contained", dest=dest)
    with open(dest+"coverage_analysis.json", mode="w", encoding="utf-8") as fp:
        json.dump({"files":incident_relevant_files,"files_all":incident_all_relevant_files, "l2l_coverage":l2l_cov}, fp)
    
def api(context_manager, incidents_json, chunk_size, VALIDATION=False):
    #incident=None
    #incidents_json=r".\DataPreprocessing\out\chunked_incidents.json"
    tag = "chunked_"+str(chunk_size)+"/"
    dest = "out/"+tag
    evaluator = evaluate_IR.ExperimentsEvaluator()
    for i, incident in enumerate(IssueLoader.load_incidents(incidents_json=incidents_json
                                                            , chunk_size=chunk_size
                                                            , OUT=dest)):
        #print(i)
        imod10=i % 10 != 0
        if (VALIDATION and imod10) or ((not VALIDATION) and (not imod10)):
            continue
        print(i, incident)
        incident.swap_into_db()# (yyyy-mm-ddThh:mm:ss+hh:ss)
        TIME_ANCHOR = "This incident occured around (yyyy-mm-dd):"+str(incident.ts).split("T")[0]+"\n"
        user_problem = TIME_ANCHOR+incident.description
        #print(">:",str(user_problem)[:150],"...")
        rca, retrieved, rounds = AlstomAI.api(user_problem=user_problem
                           , context_manager=context_manager)
        rca = rca["content"]
        #print("\nRCA:",rca)
        evaluator.evaluate(incident, rca, retrieved)
        #metrics["Recall_db"]=retr_common/retr_rel
        #metrics["Precision_db:"]=retr_common/retr_ret
    if VALIDATION:
        res_name = "-VALIDATION_results.json"
    else:
        res_name = "-EXPERIMENT_results.json"
    evaluator.log_results(dest, res_name)


def parse_args():
    parser = argparse.ArgumentParser(
       description="Experiment setup"
       )
    parser.add_argument(
        "-t", "--trunk",
        dest="trunk",
        action="store_true",
        help="Truncation context management strategy"
    )
    parser.add_argument(
         "-s", "--summarization",
         dest="summarization",
         action="store_true",
         help="Summarization context management strategy"
     )
    parser.add_argument(
         "-i", "--incidents",
         dest="incidents",
         default="chunked_incidents.json"
         ,help="The chunked_incidents.json file"
     )
    parser.add_argument(
          "-a", "--target_analysis",
          dest="target_analysis",
          action="store_true",
          help="Target analysis instead of experiments"
      )
    parser.add_argument(
          "-v", "--validation",
          dest="validation",
          action="store_true",
          help="Validation set experimentation"
      )
    
    args = parser.parse_args()
    if args.summarization:
        context_manager = message_manager.ContextManagement.SUMMARIZATION
    elif args.trunk:
        context_manager = message_manager.ContextManagement.TRUNCATION
    else:
        context_manager = message_manager.ContextManagement.NONE
    return context_manager, args.incidents, args.target_analysis, args.validation

if __name__ == "__main__":
    context_manager, incidents_json, target_analysis, validation = parse_args()
    chunk_size = incidents_json.replace("\\","/").split("/")[-2]
    if not target_analysis:
        api(context_manager=context_manager, incidents_json=incidents_json, chunk_size=chunk_size, VALIDATION=validation)
    else:
        if not chunk_size.isdigit():
            chunk_size = None
        coverage_analysis_api(incidents_json, chunking=chunk_size)