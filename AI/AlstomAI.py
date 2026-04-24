# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 11:39:56 2026

@author: chodo
"""


import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import gpt_connector
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
    
    def record_selector(self, source_path, start_ts, end_ts, exact_pattern, similarity_pattern, limit):
        recs = db_fetcher.get_file_time_pattern(source_path
                                  , start_ts
                                  , end_ts
                                  , exact_pattern
                                  , similarity_pattern
                                  , limit)
        return [r for r in recs]
    


def compact_rows(rows, max_rows=5, max_preview_chars=300):
    out = []
    for r in rows[:max_rows]:
        d = dict(r)
        out.append({
            "id": d.get("id"),
            "source_path": d.get("source_path"),
            "chunk_id": d.get("chunk_id"),
            "time_start": str(d.get("time_start")),
            "time_end": str(d.get("time_end")),
            "preview": str(d.get("content_json"))[:max_preview_chars],
        })
    return out


def old_run_rca(user_problem: str, tool_schemas, displatcher):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an RCA investigator. Break the problem into small steps. "
                "Use tools to retrieve only the next needed evidence. "
                "Maintain a timeline, hypotheses, supporting evidence, "
                "contradicting evidence, and open questions. "
                "Do not conclude until evidence is sufficient."
                "Be aware, you have just 10 iterations to complete your task."
            ),
        },
        {"role": "user", "content": user_problem},
    ]
    it = 0
    max_iter = 10
    last_calls = 0
    while True:
        if it >= max_iter:
            break
        it += 1
        resp = gpt_connector.ask_open_router(messages=messages, tools=tool_schemas)

        assistant_message = resp["choices"][0]["message"]
        tool_calls = assistant_message.get("tool_calls", [])
        if assistant_message.get("content") is not None:
            print(">:",assistant_message["content"])
        if assistant_message.get("reasoning") is not None:
            print("-:"+str(assistant_message["reasoning"])+"\n")
        print("->"+str(tool_calls)+"<-\n\n","round",it,"\n","="*32)
        for i in range(last_calls):
            messages.pop(-1)
        print(len(messages),"msgs")
        last_calls = len(tool_calls)
        if tool_calls:
            # Keep the assistant tool-call message in history
            messages.append({
                "role": "assistant",
                "content": assistant_message.get("content", "reasoning"),
                "tool_calls": tool_calls,
            })

            for call in tool_calls:
                result = displatcher.dispatch_tool(call)
                print("<:",str(result)[100:300])
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    #"content": json.dumps(result),
                    "content": json.dumps(result, default=str),
                })

            continue

        return assistant_message, messages#.get("content", "")


def run_rca(user_problem: str, tool_schemas, displatcher):
    evidence_bank = {}   # evidence_id -> full raw result
    working_summary = ""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an RCA investigator. Break the problem into small steps. "
                "Use tools to retrieve only the next needed evidence. "
                "Maintain a timeline, hypotheses, supporting evidence, "
                "contradicting evidence, and open questions. "
                "Do not conclude until evidence is sufficient."
                "Be aware, you have just 10 iterations to complete your task."
            ),
        },
        {"role": "user", "content": user_problem},
    ]
    it = 0
    max_iter = 10
    last_calls = 0
    while True:
        if it >= max_iter:
            break
        it += 1
        resp = gpt_connector.ask_open_router(messages=messages, tools=tool_schemas)

        assistant_message = resp["choices"][0]["message"]
        tool_calls = assistant_message.get("tool_calls", [])
        if assistant_message.get("content") is not None:
            print(">:",assistant_message["content"])
        if assistant_message.get("reasoning") is not None:
            print("-:"+str(assistant_message["reasoning"])+"\n")
        print("->"+str(tool_calls)+"<-\n\n","round",it,"\n","="*32)
        for i in range(last_calls):
            messages.pop(-1)
        print(len(messages),"msgs")
        last_calls = len(tool_calls)
        if tool_calls:
            messages.append({
                "role": "assistant",
                "content": assistant_message.get("content"),
                "tool_calls": tool_calls,
            })
        
            compact_for_model = []
        
            for call in tool_calls:
                result = displatcher.dispatch_tool(call)
        
                evidence_id = f"ev_{it}_{call['id']}"
                evidence_bank[evidence_id] = result
        
                compact = {
                    "evidence_id": evidence_id,
                    "result_count": len(result) if isinstance(result, list) else 1,
                    "top_matches": compact_rows(result if isinstance(result, list) else [result]),
                }
                compact_for_model.append(compact)
        
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(compact, default=str, ensure_ascii=False),
                })
            continue
        print("working summary:",working_summary)
        return assistant_message, messages#.get("content", "")


def main():
    #root = parse_args()
    displatcher = DB_Tools()
    with open(file="./AlstAI-tools.json", mode="r", encoding="utf-8") as fp:
        tool_schemas = json.load(fp)
    print("Processing Root Cause Analysis")
    #gpt_connector.ask_open_router(messages=[{"role":...,"content":...}])
    user_problem = "You are a helpful assistant which performes Root Cause Analysis."
    rca, messages = run_rca(user_problem, tool_schemas, displatcher)
    with open("last_chat.json", mode="w", encoding="utf-8") as fp:
        json.dump(messages, fp, default=str)
    print("The root cause analysis of the issue is:", rca)

if __name__ == "__main__":
    main()