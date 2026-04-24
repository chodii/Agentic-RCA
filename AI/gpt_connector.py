# -*- coding: utf-8 -*-
"""
Created on Thu Jan  1 01:31:58 2026

@author: chodo
"""

import os
from openai import OpenAI
def ask_open_ai():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "How do you say hi in swedish?"}
        ],
    )
    
    print(response.choices[0].message.content)

import requests
import json
def ask_open_router(messages, tools):
    API_KEY = os.environ["OPENROUTER"]
    response = requests.post(
      url="https://openrouter.ai/api/v1/chat/completions",
      headers={
        "Authorization": f"Bearer {API_KEY}",
        #"HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
        #"X-OpenRouter-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
        
        },
      data=json.dumps({
        "model": "openai/gpt-5.2", # Optional
        "messages": messages
        ,"tools":tools
      })
    )
    #return response
    response.raise_for_status()
    if not response.ok:
        print("STATUS:", response.status_code)
        print("BODY:", response.text)
        response.raise_for_status()

    return response.json()

def main():
    messages = [{"role":"system", "content":"Don't act weird."}, {"role":"user", "content":"What is the airi speed velocity of unloaden swallow?"}]
    res = ask_open_router(messages)
    for l in res.iter_content(100):
        print(l,"\n")
if __name__ == "__main__":
    main()