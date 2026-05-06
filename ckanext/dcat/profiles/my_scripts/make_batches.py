"""
Dataset ID Batch Splitter
=========================

Purpose:
--------
This script was created to split a large JSON list of dataset IDs (stored in a json file)
into 12 smaller, approximately equal-sized batches.

This is typically needed when:
- Processing large datasets in parallel across 12 workers/nodes/terminals.
- Circumventing API rate limits by breaking a massive request list into smaller chunks.
- Distributing data processing tasks (e.g., MassBank missing collection updates) across multiple jobs.

Input Format:
-------------
A single .json file containing a valid JSON list of strings:
["id_001", "id_002", "id_003", ..., "id_n"]

Output Format:
--------------
Generates 12 json files in the current working directory:
- batch1.json
- batch2.json
...
- batch12.json

Each output file contains a JSON list of the subset of IDs. If the total number of IDs
is less than 12, fewer files will be generated (one per ID).

Usage:
------
Run via uv with the input file path as the first argument:

    uv run make_batches.py <path_to_input_file>

Examples:
    # Windows PowerShell
    uv run '.\my scripts\make_batches.py' '.\input\collection_massbank_missing.txt'

    # Linux/Mac
    uv run ./my_scripts/make_batches.py ./input/collection_massbank_missing.txt

Dependencies:
-------------
- Python 3.6+
- No external libraries required (uses only standard library: json, math, sys, os)

Author: Philip Strömert
Date: 2026-05-01
"""
import json
import math
import sys
import os

def split_dataset_ids_to_files(input_file, num_splits=12):
    # 1. Read the JSON list from the input text file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            raise ValueError("The input file must contain a JSON list.")
            
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The file '{input_file}' does not contain valid JSON.")
        sys.exit(1)

    total_items = len(data)
    if total_items == 0:
        print("The input list is empty. No files created.")
        return

    # 2. Calculate split logic
    chunk_size = math.ceil(total_items / num_splits)
    
    chunks = []
    for i in range(num_splits):
        start_index = i * chunk_size
        end_index = start_index + chunk_size
        
        chunk = data[start_index:end_index]
        
        if chunk:
            chunks.append(chunk)

    # 3. Write to individual files
    print(f"Splitting {total_items} items into {len(chunks)} files...")
    
    for i, chunk in enumerate(chunks):
        filename = f"batch{i+1}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(chunk, f)
            
        print(f"Created {filename} with {len(chunk)} items.")

if __name__ == "__main__":
    # Check if an argument was provided
    if len(sys.argv) < 2:
        print("Usage: python make_batches.py <path_to_input_file>")
        print("Example: uv run make_batches.py ./input/data.txt")
        sys.exit(1)

    input_filename = sys.argv[1]
    
    if not os.path.exists(input_filename):
        print(f"Error: The file '{input_filename}' does not exist.")
        sys.exit(1)
        
    split_dataset_ids_to_files(input_filename)