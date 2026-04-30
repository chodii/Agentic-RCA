# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 16:00:35 2026

@author: chodo
"""

from DataPreprocessing import IssueLoader
from DataPreprocessing.Evaluation import evaluate_IR
from DataPreprocessing import AllChunker

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from AI import AlstomAI
from AI import message_manager

import argparse


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
    args = parser.parse_args()
    if args.trunk:
        context_manager = message_manager.ContextManagement.TRUNCATION
    else:
        context_manager = message_manager.ContextManagement.NONE
    return context_manager, args.incidents

if __name__ == "__main__":
    context_manager,incidents_json = parse_args()
    api(context_manager=context_manager, incidents_json=incidents_json)