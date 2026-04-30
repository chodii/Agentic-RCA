# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 17:57:27 2026

@author: chodo
"""

def standardize(prompt):
    if type(prompt["content"]) is str:
        return prompt
    c = ""
    for k in prompt["content"]:
        c += "\n"+k
    prompt["content"] = c
    return prompt

def truncate_retrieved(manager):
    if manager.last_calls == 0:
        return
    for i in range(manager.last_calls):
        calls = manager.messages.pop()
        print("pop",calls["role"], len(calls), "-", str(calls["content"])[:200])
    message = manager.messages.pop()
    if "tool_calls" in message:
        message.pop("tool_calls")# remove all tool calls
    manager.messages.append(message)# keep at least track of thoughts
    print("popop", len(manager.messages))
    
    
def summarize(manager):
    ...

def context_management_prompt(manager):
    ...

def foo_none(manager):
    ...# by intention - do nothing


from enum import Enum
class ContextManagement(Enum):
    TRUNCATION          = truncate_retrieved
    SUMMARIZATION       = summarize
    CONTEXT_MANAGEMENT  = context_management_prompt
    NONE  = foo_none


import json
INITIAL_MSG_KEY = "initial_prompt"
FORCE_STOP_KEY = "force_end_prompt"
class MessageManager:
    
    def __init__(self, db_manager
                 , system_prompt_pth
                 , context_management_strategy
                 , gpt
                 , max_iter = 10):
        self.db_manager = db_manager
        self.gpt = gpt# might be used, depending on the context_management_strategy
        
        self.predefined_prompts = None
        with open(system_prompt_pth, "r", encoding="utf-8") as fp:
            self.predefined_prompts = json.load(fp)
        self.messages = [standardize(self.predefined_prompts[INITIAL_MSG_KEY])]
        self.force_end = False
        self.about_to_end = False
        self.context_manager = context_management_strategy
        self.last_calls = 0
        self.iteration = 0
        self.max_iter = max_iter
        
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
        if assistant_message.get("refusal"):
            print("MODEL IS REFUSING TO ANSWER")
            self.messages.append(assistant_message)
            self.force_end = True
        self.iteration += 1
        tool_calls = assistant_message.get("tool_calls", [])
        role = assistant_message.get("role","")
        self.context_manager(self)
        self.last_calls = len(tool_calls)
        
        past_conclusion=None
        assistant_ready_for_conclusion=False
        #if content is None or content == []:
        content = assistant_message.get("content",[])
                    
        reasoning = assistant_message.get("reasoning",[])
        if tool_calls:
            self.messages.append({
                "role": "assistant",
                "content": content,
                "reasoning":reasoning,
                "tool_calls": tool_calls,
            })
            # Keep the assistant tool-call message in history
            for call in tool_calls:
                result = self.db_manager.dispatch_tool(call)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    #"content": json.dumps(result),
                    "content": json.dumps(result, default=str),
                })
        else:
            self.messages.append({
                "role": "assistant",
                "content": content,
                "reasoning":reasoning
            })
        if (role == "assistant" and content is not None and len(content) > 0):
            if past_conclusion is None:
                past_conclusion = content
            elif past_conclusion == content:
                assistant_ready_for_conclusion=True
        investigation_exceeding_budget = (self.iteration >= self.max_iter-1)
        print("\r",self.iteration, "-", assistant_ready_for_conclusion, investigation_exceeding_budget, end="")
        if self.about_to_end or assistant_ready_for_conclusion:
            self.force_end = True
            return
        if investigation_exceeding_budget:
            self.about_to_end = True
            self.messages.append(self.predefined_prompts[FORCE_STOP_KEY])
