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


