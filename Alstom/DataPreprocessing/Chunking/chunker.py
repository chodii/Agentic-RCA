# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 14:21:28 2026

@author: chodo
"""
KEY_META="metadata"
KEY_SRC_PTH="source"
KEY_CHUNK_ID="chunk_id"
KEY_CONTENT="content"

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import _dataset_walker as walker

import json
def line_len(line):
    if type(line) == list:
        lineparts_len = 0
        for p in line:
            lineparts_len += len(str(p))
        return lineparts_len
    else:
        print(type(line), " could not be measured")

def chunk_id(filename, chunks_created):
    if filename not in chunks_created:
        chunks_created[filename] = 0
    else:
        chunks_created[filename] += 1
    return chunks_created[filename]
    
def create_chunk(orig_filename, chunks_created, content):
    chid = chunk_id(orig_filename, chunks_created)
    
    FILE_AS_JSON = {
            KEY_SRC_PTH : orig_filename 
            , KEY_CHUNK_ID: chid
            , KEY_CONTENT : content
        }
    return FILE_AS_JSON

def write_chunk(dest_fp, files_created, chunk):
    filename = walker.unique_name(dest_fp, files_created, POST_COUNT=True)
    with open(filename+".json", mode="w", encoding="utf-8") as jfp:
        json.dump(chunk, jfp)

def limit_content(content, max_chunk_len):
    new_content = []
    for line in content:
        if len(str(line)) <= max_chunk_len:
            new_content.append(line)
            continue
        ts_len = len(str(line[0]))
        max_without_ts = max_chunk_len-ts_len
        cont_len = len(line[1])
        sub_chunks = int(cont_len/max_without_ts) + (1 if cont_len%max_without_ts != 0 else 0)
        for i in range(sub_chunks-1):
            line_chunk = line[1][max_without_ts*i : max_without_ts*(i+1)]
            new_content.append([line[0], line_chunk])
        line_chunk = line[1][max_without_ts*(i+1):]
        new_content.append([line[0], line_chunk])
    return new_content

def chunk_dataset(src, dest, max_chunk_len=500):
    files_created={}
    chunks_ids={}
    chunk_sizes = []
    print("Chunking from",src,"into",dest)
    os.makedirs(dest, exist_ok=True)
    for fp in walker.dataset_iterator(src):
        if ".json" not in fp:
            continue
        with open(fp, mode="r", encoding="utf-8") as jfp:
            FILE_AS_JSON = json.load(jfp)
        content = []
        chunk_len = 0
        # src:
        orig_filename = FILE_AS_JSON[KEY_SRC_PTH]# root-independent
        src_dir = os.path.dirname(fp)
        # dest:        
        file_name = fp.replace(src_dir,"").replace(".", "").replace("json", "")
        #dest_dir = src_dir.replace(src, dest)
        dest_fp = dest + file_name
        JSON_CONTENT = limit_content(FILE_AS_JSON[KEY_CONTENT], max_chunk_len)
        for line in JSON_CONTENT:
            ll = line_len(line)
            next_chun_len = chunk_len + ll
            if next_chun_len <= max_chunk_len:# add to content
                chunk_len = next_chun_len
                content.append(line)
                continue# else:
            
            if chunk_len == 0:# it is what it is, it can not be shorter
                chunk_len = ll
                content = [line]
                
                chunk = create_chunk(orig_filename, chunks_ids, content)
                write_chunk(dest_fp, files_created, chunk)
                chunk_sizes.append(chunk_len)
                
                content=[]
                chunk_len=0
            else:# there is already some content, write the chunk
                chunk = create_chunk(orig_filename, chunks_ids, content)
                write_chunk(dest_fp, files_created, chunk)
                chunk_sizes.append(chunk_len)
                
                chunk_len = ll
                content = [line]
        # last chunk:
        chunk = create_chunk(orig_filename, chunks_ids, content)
        write_chunk(dest_fp, files_created, chunk)
        chunk_sizes.append(chunk_len)
    print(sum([chunks_ids[k] for k in chunks_ids]), "chunks created")
    return chunk_sizes
    