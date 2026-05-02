# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 16:00:35 2026

@author: chodo
"""

from DataPreprocessing import IssueLoader
from DataPreprocessing.Evaluation import evaluate_IR
from DataPreprocessing import AllChunker
from DataPreprocessing import _dataset_walker as dw
from DataPreprocessing.Visualizations import hist
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from AI import AlstomAI
from AI import message_manager

import argparse

def coverage_analysis(old, new, tag):
    covs = []
    for i in range(len(old)):
        cov = (new[i])/old[i]
        covs.append(cov)
    hist.hist_from_array_single(covs, x="Coverage of target output", y="Count", title="Potential "+tag+" coverage of target output")
    
def coverage_analysis_api(incidents_json):
    lens_orig = []
    word_lens_orig = []
    line_lens_oring = []
    
    lens_new = []
    word_lens_new = []
    line_lnes_new = []
    line_2_lnes_new = []
    
    for i,incident in enumerate(IssueLoader.load_incidents(incidents_json=incidents_json)):
        print("\r",i,incident.__str__(),end="")
        srcs = incident.chunk_folder.replace("\\","/").split("/")[:-1]
        src = ""
        for s in srcs:
            src += s+"/"
        src += "windowed_selection/"
        target = incident.get_target()
        target_manager = evaluate_IR.target_manager(target)
        for fp in dw.dataset_iterator(src):
            for line in IssueLoader.log_file_reader(fp):
                target_manager.log_in_line(line)
                target_manager.log_in_word(line)
        old_str_len, new_str_len, old_word_len, new_word_len, old_line_len, new_line_len, new_len_line_target_2 = target_manager.result()
        lens_orig.append(old_str_len)
        word_lens_orig.append(old_word_len)
        line_lens_oring.append(old_line_len)
        lens_new.append(new_str_len)
        word_lens_new.append(new_word_len)# word contained
        line_lnes_new.append(new_line_len)# line exact
        line_2_lnes_new.append(new_len_line_target_2)# line contained
    hist.hist_from_array_single(lens_orig, x="Length of target output", y="Count", title="Length of target [characters]")
    hist.hist_from_array_single(word_lens_orig, x="Length of target output", y="Count", title="Length of target [words]")
    hist.hist_from_array_single(line_lens_oring, x="Length of target output", y="Count", title="Length of target [lines]")
    coverage_analysis(lens_orig, lens_new, "character")
    coverage_analysis(word_lens_orig, word_lens_new, "word")
    coverage_analysis(line_lens_oring, line_lnes_new, "line (exact) ")
    coverage_analysis(line_lens_oring, line_2_lnes_new, "line (contained) ")
    
def api(context_manager, incidents_json):
    #incident=None
    #incidents_json=r".\DataPreprocessing\out\chunked_incidents.json"
    for incident in IssueLoader.load_incidents(incidents_json=incidents_json):
        print(incident)
        incident.swap_into_db()# (yyyy-mm-ddThh:mm:ss+hh:ss)
        TIME_ANCHOR = "This incident occured around (yyyy-mm-dd):"+str(incident.ts).split("T")[0]+"\n"
        user_problem = TIME_ANCHOR+incident.description
        print(">:",str(user_problem)[:150],"...")
        
        rca = AlstomAI.api(user_problem=user_problem
                           , context_manager=context_manager)
        rca = rca["content"]
        print("\nRCA:",rca)
        target = incident.get_target()
        precission,recall = evaluate_IR.eval_prec_rec(pred=rca, targ=target)
        print("P:",precission, "\nR:",recall)
        break


def parse_args():
    parser = argparse.ArgumentParser(
       description="Experiment setup"
       )
    parser.add_argument(
        "-t", "--trunk",
        dest="trunk",
        action="store_true",
        help="Truncation"
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
    args = parser.parse_args()
    if args.trunk:
        context_manager = message_manager.ContextManagement.TRUNCATION
    else:
        context_manager = message_manager.ContextManagement.NONE
    return context_manager, args.incidents, args.target_analysis

if __name__ == "__main__":
    context_manager, incidents_json, target_analysis = parse_args()
    if not target_analysis:
        api(context_manager=context_manager, incidents_json=incidents_json)
    else:
        coverage_analysis_api(incidents_json)