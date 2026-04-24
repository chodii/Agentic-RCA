# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 00:17:42 2026

@author: chodo
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#print("pp",os.path.dirname(__file__))
import argparse
import json
from datetime import datetime, timedelta

import AlstomAnalyst
from Visualizations import time_diffs

MIN_SCORE = 8
def get_incident_root(root, match, ts, DEPTH=3):
    root_parts = match.get("source_path").replace(root, "").split("\\")
    incident_root = root
    for i in range(min(DEPTH, len(root_parts))):
        incident_root = os.path.join(incident_root, root_parts[i]+"\\")
    print("searching", incident_root,  str(datetime.fromisoformat(ts)))
    return incident_root


def reported_date(match):
    row = match["row"]
    header_to_find = None
    sheet = row["sheet_name"]
    if sheet == "EAA-720":
        header_to_find = "Date"
    if sheet == "LOT-710":
        header_to_find = "Date"
    if sheet == "CRO-345":
        header_to_find = "Occ Date"
    ix = 0
    for h in row["headers"]:
        if h is not None and h.strip() == header_to_find:
            break
        ix += 1
    matched_date = row["row_values"][ix]
    dt = datetime.strptime(matched_date, "%Y-%m-%d %H:%M:%S")
    return dt

def unmatch(match, ts):
    #src_len = len(match.get("matched_source_lines", []))
    #score = match.get("score", 0)
    #if src_len == 0 or src_len > score:
    #    print("skipping", str(datetime.fromisoformat(ts)))
    #    return True# skip, not fully matching
    ts_formated = ts.split("+")[0].replace("T", " ")
    print("Matching", ts_formated)
    cells = match.get("row",{}).get("row_values",[])
    if cells is None or len(cells) == 0:
        return True
    for val in cells:
        if type(val) is not str:
            continue
        if ts_formated in val:
            return False# definitely this time! :)
    return True

from datetime import timezone
def read_times_file(times_file, root, time_differences, incidents):
    """
    Reads source_date_row_matches_best.json and yields only timestamps
    whose entry has a non-empty 'matches' list.

    The yielded time is the TOP-LEVEL KEY, e.g.:
    '2022-06-01T07:17:53+01:00'
    parsed into a datetime.
    """
    with open(times_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", {})

    for ts, entry in results.items():
        matches = entry.get("matches", [])
        if not matches:
            continue
        match = matches[0]
        if unmatch(match, ts):
            continue
        reported_time = reported_date(match)
        actual_time = datetime.fromisoformat(ts)
        if reported_time.tzinfo is None:
            reported_time = reported_time.replace(tzinfo=timezone.utc)
        if actual_time.tzinfo is None:
            actual_time = actual_time.replace(tzinfo=timezone.utc)
        diff = time_diffs.signed_difference_record(reported_time, actual_time)
        time_differences.append(diff)
        incident_root = get_incident_root(root, match, ts)
        incident_time = reported_time
        
        entry["mapped_date"] = reported_time.isoformat()
        incidents[str(ts)]=entry
        
        yield incident_time, incident_root, entry


def parse_args():
    parser = argparse.ArgumentParser(
        description="Give me the time, I'll give you files and tell you where to start."
    )
    parser.add_argument(
        "-r", "--root",
        dest="root",
        type=str,
        required=True,
        help="Path to the root folder"
    )
    parser.add_argument(
        "-d", "--dest",
        dest="dest",
        type=str,
        required=True,
        help="Path to the dest folder"
    )
    parser.add_argument(
        "-t", "--time_file",
        dest="time_file",
        type=str,
        required=True,
        help="Path to the time_file"
    )
    
    parser.add_argument(
        "-anom", "--detect-anomalies",
        dest="det_anom",
        action="store_true"
        , help="Detect anomalies"
    )
    
    args = parser.parse_args()
    return args.root, args.dest, args.time_file, args.det_anom


def main():
    root, dest, times_file, det_anom = parse_args()
    api(root, dest, times_file, anomally_detection=det_anom)

def api(root, dest, times_file, anomally_detection=False, CHUNK_SIZE = 5000, inc_json = "chunked_incidents.json"):
    SPAN_START = timedelta(days=1)
    SPAN_AFTER_END = timedelta(days=1)
    
    
    time_differences = []
    chuns = []
    incidents = {}
    for incident_time, incident_root, entry in read_times_file(times_file
                                                        , root
                                                        , time_differences
                                                        , incidents):
        time_start = incident_time - SPAN_START
        time_end = incident_time + SPAN_AFTER_END

        chunk_sizes, anomalies, chunk_dest = AlstomAnalyst.api(
            incident_root,
            dest,
            time_start,
            time_end,
            chunk_size=CHUNK_SIZE
            , INCLUDE_STATIC_FILES=True
            , anom_detect=anomally_detection
        )
        chuns.extend(chunk_sizes)
        entry["anomalies"] = anomalies
        entry["chunked_destination"]  = chunk_dest
        print("\nINCIDENTS:",len(incidents),"\n")
    import Visualizations.hist as Viz_Hist
    Viz_Hist.hist_from_array(chuns, x="Chunk Size", y="Frequency", title="Chunk Sizes", show=True)
    time_diffs.plot_difference_histograms(time_differences, unit="hours", bins=30, title="Reported vs actual time")
    import json
    with open(inc_json, "w", encoding="utf-8") as fp:
        json.dump(incidents, fp,
        default=str)
    
if __name__ == "__main__":
    main()
    

