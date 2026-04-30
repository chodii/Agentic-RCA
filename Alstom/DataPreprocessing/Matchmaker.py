# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 02:15:51 2026

@author: chodo
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from Alstom.DataPreprocessing.Window import TextSniffer as TxSf
from General import xlsx_main_pipeline_top_compact as xlsx_matchmaker

def api(root, xlsx_file):
    if root is None or xlsx_file is None:
        return xlsx_matchmaker.api(xlsx_path=None, source_json=None)# will return the name
    anomalies = TxSf.api(root=root)
    best_matches = xlsx_matchmaker.api(xlsx_path=xlsx_file, source_json=anomalies)
    #best_matches=r"C:\Users\chodo\Documents\Studies\Projects\Sweden\MasterThesis\src\General\out\source_date_row_matches_best.json"
    return best_matches
