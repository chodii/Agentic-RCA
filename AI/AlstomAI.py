# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 11:39:56 2026

@author: chodo
"""


import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from AI import gpt_connector
from AI import message_manager
from Alstom.Database import db_fetcher

from datetime import datetime, timedelta
import pytz
import logging

import argparse
import json
def parse_args():
    parser = argparse.ArgumentParser(
       description="Give me the root, I'll give you the Root Cause."
       )
    parser.add_argument(
        "-r", "--root",
        dest="root",
        type=str,
        help="Path to the root folder"
    )
    args = parser.parse_args()
    root=args.root
    return root

def _convert_time(time):
    utc=pytz.UTC
    t=utc.localize(datetime.fromisoformat(time))
    return t

def extract_params(query):
    source_path:str=None
    start_ts: str=None
    end_ts: str=None
    exact_pattern:str=None
    limit:int=1
    return source_path, start_ts, end_ts, exact_pattern, limit

class DB_Tools:
    def __init__(self):
        ...
    
    def dispatch_tool(self, call):
        tool_name = call["function"]["name"]
        args = json.loads(call["function"].get("arguments", "{}"))
    
        if tool_name == "record_selector":
            return self.record_selector(**args)
        raise ValueError(f"Unknown tool: {tool_name}")
    
    def record_selector(self
                        , source_path=None
                        , start_ts=None
                        , end_ts=None
                        , exact_pattern=None
                        , similarity_pattern=None
                        , limit=1):
        recs = db_fetcher.get_file_time_pattern(source_path
                                  , start_ts
                                  , end_ts
                                  , exact_pattern
                                  , similarity_pattern
                                  , limit)
        return [r for r in recs]
    


def run_rca(user_problem: str, tool_schemas, system_prompt_pth, context_manager):
    displatcher = DB_Tools()
    messanger = message_manager.MessageManager(
                db_manager = displatcher
                 , system_prompt_pth = system_prompt_pth
                 , context_management_strategy = context_manager
                 , gpt = gpt_connector.ask_open_router)
    messanger.init_problem(user_problem=user_problem)
    try:
        while True:
            if messanger.force_end:
                break
            if messanger.about_to_end:
                tool_schemas = None# I want you to talk --> therefore no tools
            assistant_message = gpt_connector.ask_open_router(messages=messanger.messages
                                                 , tools=tool_schemas)
            messanger.add_response(assistant_message)
    except Exception as e:
        print("\nExcepted:",e)
        return "-", messanger.messages
    print()
    return assistant_message, messanger.messages#.get("content", "")



def main():
    #root = parse_args()
    rca = api("Your mom")
    print("The root cause analysis of the issue is:", rca)

from pathlib import Path
def api(user_problem
        , context_manager
        , tools = "AlstAI-tools.json"
        , system_prompt_pth = "AlstAI-prompts.json"):
    MODULE_DIR = Path(__file__).resolve().parent
    tools = str(MODULE_DIR)+"/"+tools
    system_prompt_pth=str(MODULE_DIR)+"/"+system_prompt_pth
    with open(file=tools, mode="r", encoding="utf-8") as fp:
        tool_schemas = json.load(fp)
    result_log = "out/last_chats/"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json"
    #gpt_connector.ask_open_router(messages=[{"role":...,"content":...}])
    
    rca, messages = run_rca(user_problem=user_problem
                            , tool_schemas=tool_schemas
                            , system_prompt_pth=system_prompt_pth
                            , context_manager=context_manager)
    os.makedirs(result_log,exist_ok=True)
    with open(result_log, mode="w", encoding="utf-8") as fp:
        json.dump(messages, fp, default=str)
    return rca

if __name__ == "__main__":
    main()