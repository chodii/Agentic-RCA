# -*- coding: utf-8 -*-
"""
Created on Sun Mar  8 18:48:13 2026

@author: chodo
"""


import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Window import WindowedDataSelection
from Window import hist_yearly
from Window import hist_monthly

from datetime import datetime, timezone, timedelta
years = None

def gather_data_for_plot():
    
    root = "C:\\Datasets\\MonLis"
    time_start = datetime(1900,3,10,21,40,16,tzinfo=timezone.utc)
    time_end = datetime(2026,4,14,21,40,16,tzinfo=timezone.utc)
    years = {}
    for events_log in WindowedDataSelection.extract_time_relevant_events(root, time_start, time_end):
        for (time, line) in events_log[WindowedDataSelection.DATA_KEY]:
            #n+=1
            year = time.isoformat()[:4]
            if year not in years:
                years[year] = {}
            month = time.isoformat()[5:7]
            if month not in years[year]:
                years[year][month] = 0
            years[year][month] += 1
    return years

def main():
    global years
    import matplotlib as mtl
    font = {'family' : 'normal',
            #'weight' : 'normal',
            'size'   : 10}
    mtl.rc('font', **font)
    years = gather_data_for_plot()
    hist_yearly.plot_data(years)
    hist_monthly.plot_data(years)
    import json
    with open("years.json", "w") as fp:
        json.dump({"years":years, "stats":WindowedDataSelection.ExtractorLog.STATISTICS_COUNTER}, fp)

if __name__ == "__main__":
    main()