#!/usr/bin/env python3
"""
NFDI4Chem Search Service nmrXiv ID normalization script part 1 (Fetching Step)

DESCRIPTION:
    This script resolves ID mismatches for the nmrXiv repository between the NFDI4Chem Search Service 'package_list'
    and 'package_show' API endpoints.
    It takes a list of "input IDs" (from package_list), queries the metadata for each, and extracts the
    "actual ID" used for file naming within using_linkml_dataclasses.py.

    It is designed for HIGH-THROUGHPUT parallel execution. Multiple instances of this script should be run
    simultaneously in different terminals, each processing a different chunk of input data, while appending
    to the SAME two output files.

WORKFLOW:
    1. Split your full list of input IDs into smaller chunks (e.g., batch1.json, batch2.json).
    2. Run multiple instances of this script in parallel, pointing them to the same output files:
       > python get_normalized_nmrxiv_ids_pt1.py batch1.json output_ids.jsonl output_map.jsonl &
       > python get_normalized_nmrxiv_ids.py batch2.json output_ids.jsonl output_map.jsonl &
    3. Wait for all instances to complete.
    4. Run 'get_normalized_nmrxiv_ids_pt2.py' to merge the .jsonl lines into standard .json files.

OUTPUT FORMAT (Critical):
    - This script writes to '.jsonl' (JSON Lines) files, NOT standard '.json' arrays.
    - Each line in the output file is a valid, independent JSON object.
    - DO NOT manually edit these files while the script is running.
    - DO NOT use these files directly in downstream tools until they have been converted.

DEPENDENCIES:
    - Requires 'get_normalized_nmrxiv_ids_pt2.py' to finalize the data.
    - The output files ('...jsonl') are intermediate artifacts. You must run the converter
      to generate valid '.json' lists/dictionaries for verification or analysis.

USAGE:
    python get_normalized_nmrxiv_ids_pt1.py <input_json> <output_ids_jsonl> <output_map_jsonl>

    Arguments:
        input_json        : Path to a JSON file containing a list of unnormalized nmrXiv
                            input IDs (e.g., ["10043_m03-1d", "10043_m50proton_m50"]) obtained by using the
                            https://search.nfdi4chem.de/api/3/action/package_list endpoint.
        output_ids_jsonl  : Path to the output file for corrected IDs (appended line-by-line).
        output_map_jsonl  : Path to the output file for ID mappings (appended line-by-line).

EXAMPLE:
    # Terminal 1
    python get_normalized_nmrxiv_ids_pt1.py chunk_1.json normalized_nmrxiv_ids.jsonl nmrxiv_ids_mapped.jsonl

    # Terminal 2 (Simultaneously)
    python get_normalized_nmrxiv_ids_pt1.py chunk_2.json normalized_nmrxiv_ids.jsonl nmrxiv_ids_mapped.jsonl

    # After both finish, convert to standard JSON:
    python get_normalized_nmrxiv_ids_pt2.py list normalized_nmrxiv_ids.jsonl final_ids.json
    python get_normalized_nmrxiv_ids_pt2.py map nmrxiv_ids_mapped.jsonl nmrxiv_ids_map.json
"""

import requests
import json
import time
import sys
import os

# Platform-specific imports for file locking
if os.name == 'nt':
    import msvcrt
else:
    import fcntl

BASE_URL = "https://search.nfdi4chem.de/api/3/action"
PACKAGE_SHOW_ENDPOINT = f"{BASE_URL}/package_show"

def load_ids_from_json(filename):
    """Loads IDs from a JSON file."""
    if not os.path.exists(filename):
        print(f"Error: Input file '{filename}' not found.")
        sys.exit(1)
    
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        
        if isinstance(data, dict):
            for key in ['ids', 'id_list', 'dataset_ids', 'input_ids', 'data']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            for value in data.values():
                if isinstance(value, list):
                    return value
            
        print("Error: Could not find a list of IDs in the input JSON file.")
        sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in '{filename}': {e}")
        sys.exit(1)

def write_line_safely(filename, data_item):
    """
    Writes a single JSON item to a file in append mode.
    Simplified version without explicit locking for Windows compatibility debugging.
    """
    try:
        # Open in append mode ('a')
        with open(filename, 'a', encoding='utf-8') as f:
            # Write JSON item + newline
            json.dump(data_item, f, ensure_ascii=False)
            f.write('\n')
            f.flush() # Force write to disk
    except PermissionError as pe:
        print(f"\n*** CRITICAL ERROR: Permission Denied for file '{filename}' ***")
        print(f"Details: {pe}")
        print("ACTION: Please manually DELETE '{filename}' and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n*** ERROR writing to '{filename}': {e} ***")
        sys.exit(1)

def main():
    if len(sys.argv) < 4:
        print("Usage: python correct_ids_parallel.py <input_json> <output_list_jsonl> <output_map_jsonl>")
        print("  <input_json>: File with list of old IDs")
        print("  <output_list_jsonl>: File to append new IDs (one per line)")
        print("  <output_map_jsonl>: File to append mappings {'old': ..., 'new': ...} (one per line)")
        print("Example: python correct_ids_parallel.py chunk_1.json results.jsonl mapping.jsonl")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_list_filename = sys.argv[2]
    output_map_filename = sys.argv[3]
    
    print(f"[PID {os.getpid()}] Loading IDs from '{input_filename}'...")
    input_ids = load_ids_from_json(input_filename)
    
    if not input_ids:
        print(f"[PID {os.getpid()}] Warning: Input list is empty.")
        sys.exit(0)

    total_count = len(input_ids)
    success_count = 0
    
    print(f"[PID {os.getpid()}] Processing {total_count} IDs...")
    print(f"[PID {os.getpid()}] Appending IDs to: '{output_list_filename}'")
    print(f"[PID {os.getpid()}] Appending Maps to: '{output_map_filename}'\n")

    for i, input_id in enumerate(input_ids):
        try:
            params = {"id": input_id}
            # Added timeout to prevent hanging on bad connections
            response = requests.get(PACKAGE_SHOW_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("success") and "result" in data and "id" in data["result"]:
                actual_id = data["result"]["id"]
                
                # 1. Write the new ID to the list file
                write_line_safely(output_list_filename, actual_id)
                
                # 2. Write the mapping object to the map file
                mapping_entry = {input_id: actual_id}
                write_line_safely(output_map_filename, mapping_entry)
                
                success_count += 1
                print(f"[PID {os.getpid()}] [{i+1}/{total_count}] OK: {input_id} -> {actual_id}")
            else:
                print(f"[PID {os.getpid()}] [{i+1}/{total_count}] WARN: No ID found for {input_id}")
                # Optional: Write failed mappings too? 
                # mapping_entry = {"old": input_id, "new": None, "error": "No ID in result"}
                # write_line_safely(output_map_filename, mapping_entry)
            
            time.sleep(0.2) 
            
        except requests.exceptions.RequestException as e:
            print(f"[PID {os.getpid()}] [{i+1}/{total_count}] ERR: {input_id} -> {e}")
        except Exception as e:
            print(f"[PID {os.getpid()}] [{i+1}/{total_count}] UNEXP: {input_id} -> {e}")

    print(f"\n[PID {os.getpid()}] Done. Mapped {success_count}/{total_count} successfully.")

if __name__ == "__main__":
    main()