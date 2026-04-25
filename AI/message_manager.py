# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 17:57:27 2026

@author: chodo
"""
 
def truncate_retrieved(manager):
    if manager.last_calls == 0:
        return
    for i in range(len(manager.last_calls) + 1):
        manager.messages.pop()
    # basically pop everything related to that information

def summarize(manager):
    ...

def context_management_prompt(manager):
    ...

from enum import Enum
class ContextManagement(Enum):
    TRUNCATION          = truncate_retrieved
    SUMMARIZATION       = summarize
    CONTEXT_MANAGEMENT  = context_management_prompt

import json
class MessageManager:
    
    def __init__(self, db_manager
                 , system_prompt_pth
                 , context_management_strategy
                 , gpt):
        self.db_manager = db_manager
        self.gpt = gpt# might be used, depending on the context_management_strategy
        
        system_prompts = None
        with open(system_prompt_pth, "r", encoding="utf-8") as fp:
            system_prompts = json.load(fp)
        self.messages = [system_prompts]
        self.force_end = False
        self.context_manager = context_management_strategy
        self.last_calls = 0
        
    def init_problem(self, user_problem):
        self.messages.append({"role": "user", "content": user_problem})
        if self.context_manager is ContextManagement.TRUNCATION:
            ...
            return
        if self.context_manager is ContextManagement.SUMMARIZATION:
            ...
            return
        if self.context_manager is ContextManagement.CONTEXT_MANAGEMENT:
            ...
            return
        
    
    def add_response(self, assistant_message):
        tool_calls = assistant_message.get("tool_calls", [])
        self.context_manager(self)
        self.last_calls = len(tool_calls)
        if tool_calls:
            # Keep the assistant tool-call message in history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message.get("content", "reasoning"),
                "tool_calls": tool_calls,
            })
            for call in tool_calls:
                result = self.db_manager.dispatch_tool(call)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    #"content": json.dumps(result),
                    "content": json.dumps(result, default=str),
                })
   