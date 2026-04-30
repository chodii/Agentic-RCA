# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 18:31:10 2026

@author: chodo
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Database import db_loader

from DataPreprocessing.Window import ExtractorLog

import json
DEST_KEY = "chunked_destination"
TS_KEY = "mapped_date"
ROW_KEY = "row"
HEADER_KEY = "headers"
ROW_VALS_KEY = "row_values"
SHEET_KEY = "sheet_name"
MATCHES_KEY = "matches"

DESCRIPTION = "description"
TARGET = "target"
ISSUE = "issue"
SHEET_MAP = {
    "EAA-720":{DESCRIPTION:"details +time"
               , TARGET:"Developer's analysis"
               , ISSUE:"Type of NOSS"}
    ,"LOT-710":{DESCRIPTION:"Details and time"
                , TARGET:"TCMS HMI team analysis"
                , ISSUE:"Type of NOSS"}
    ,"CRO-345":{DESCRIPTION:"Details and time"
                , TARGET:"Comments from Developer"
                , ISSUE:"Issue TYPE"}
    }

def load_incidents(incidents_json):
    incidents = None
    with open(incidents_json, "r", encoding="utf-8") as fp:
        incidents = json.load(fp)
    for k in incidents:
        incident = Incident(incident=incidents[k])
        yield incident

def extract_from_sheet(row, information):
    ix = 0
    sheet = row[SHEET_KEY]
    header_to_find = SHEET_MAP[sheet][information]
    found=False
    for h in row[HEADER_KEY]:
        if h is not None and h.strip() == header_to_find:
            found=True
            break
        ix += 1
    if not found:
        print("SHOULD FIND", ">"+header_to_find+"<")
    matched_val = row[ROW_VALS_KEY][ix]
    return matched_val
    
class Incident:
    def __init__(self, incident):
        self.chunk_folder = incident[DEST_KEY]
        self.ts = incident[TS_KEY]
        match = incident[MATCHES_KEY][0]
        row = match[ROW_KEY]
        self.description = extract_from_sheet(row, DESCRIPTION)
        self.raw_target = extract_from_sheet(row, TARGET)
        self._target=None
        self.issue_type = extract_from_sheet(row, ISSUE)
    
    def __str__(self):
        return str(self.chunk_folder) + "\n" + str(self.ts)
    
    def get_target(self):
        if not self._target:
            converted_target = ExtractorLog.all_from_text(self.raw_target)
            preprocessed = []
            for l in converted_target:
                ts = l[0]
                content = l[1]
                if ts:
                    line = str(ts.isoformat())+" "+str(content)
                else:
                    line = str(content)
                preprocessed.append(line)
            self._target = ""
            for i in range(len(preprocessed)-1):
                self._target+=preprocessed[i]+"\n"
            self._target += preprocessed[-1]
        return self._target
    
    def swap_into_db(self):
        db_loader.api(root=self.chunk_folder)
