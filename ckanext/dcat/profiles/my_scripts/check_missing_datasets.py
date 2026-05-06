#!/usr/bin/env python3
"""
Check Missing Dataset IDs Across Multiple Folders

This script compares a list of expected dataset IDs against existing TTL files
in one or more directories. It identifies which IDs are missing a corresponding
file and saves the list of missing IDs to a text file.

File Naming Convention:
  The script expects files to follow the pattern: {ID}{SUFFIX}
  It extracts the ID by removing the specific suffix from the filename.
  This method correctly supports IDs that contain underscores (e.g., "my_id_123").

  Supported Suffixes:
  - _dcat-ap-plus.ttl
  - _chem-dcat-ap.ttl

Usage:
  python3 check_missing_datasets.py <ids_file> <output_file> <suffix> <folder1> [folder2] ...

Arguments:
  ids_file    : Path to a JSON file containing a list of dataset IDs (e.g., ["id1", "id_2"]).
  output_file : Path where the resulting list of missing IDs will be saved (JSON format).
  suffix      : The file suffix to check for. Choose one:
                - "_dcat-ap-plus.ttl"
                - "_chem-dcat-ap.ttl"
  folders     : One or more paths to directories containing the TTL files.

Examples:
  1. Check a single folder for DCAT-AP-Plus files:
     python3 check_missing_datasets.py ids.json missing_ids.json _dcat-ap-plus.ttl ./data/processed

  2. Check multiple folders for Chem-DCAT-AP files (handles IDs with underscores):
     python3 check_missing_datasets.py ids.json missing_ids.json _chem-dcat-ap.ttl ./batch1 ./batch2 ./archive

  3. Full command with absolute paths:
     python3 check_missing_datasets.py /home/user/lists/all_ids.json \
       /home/user/lists/missing_ids.json \
       _dcat-ap-plus.ttl \
       /mnt/data/part1 /mnt/data/part2

Output:
  - Console: Summary statistics (total IDs, files found per folder, total missing) and names of non-matching files.
  - File: A JSON-formatted list of missing IDs (e.g., ["id_3", "complex_id_99"]).
"""
import os
import sys
import json
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Find dataset IDs missing corresponding TTL files across multiple folders.")
    parser.add_argument("ids_file", help="Path to JSON file containing the list of dataset IDs")
    parser.add_argument("output_file", help="Path to the output .txt file")
    parser.add_argument("suffix", choices=["_dcat-ap-plus.ttl", "_chem-dcat-ap.ttl"],
                        help="The file suffix to check for")
    # Accept one or more folder paths
    parser.add_argument("folders", nargs="+", help="One or more paths to folders containing .ttl files")

    args = parser.parse_args()

    # 1. Load the list of IDs
    try:
        with open(args.ids_file, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                dataset_ids = data
            else:
                print("Error: JSON file must contain a direct list of IDs.")
                sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{args.ids_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{args.ids_file}' is not valid JSON.")
        sys.exit(1)

    total_input_ids = len(dataset_ids)
    print(f"Loaded {total_input_ids} dataset IDs from '{args.ids_file}'.")

    # 2. Scan ALL provided folders for existing files
    processed_ids = set()
    total_files_found = 0

    for folder_path in args.folders:
        if not os.path.isdir(folder_path):
            print(f"Warning: Folder '{folder_path}' does not exist. Skipping.")
            continue

        existing_files = os.listdir(folder_path)
        folder_count = 0

        for filename in existing_files:
            if filename.endswith(args.suffix):
                file_id = filename.replace(args.suffix, "")
                processed_ids.add(file_id)
                folder_count += 1
            else:
                print(filename)

        print(f"  - Scanned '{folder_path}': found {folder_count} matching file(s).")
        total_files_found += folder_count

    print(f"Total unique processed IDs found across all folders: {len(processed_ids)}")

    # 3. Identify missing IDs
    missing_ids = [ds_id for ds_id in dataset_ids if ds_id not in processed_ids]
    total_missing = len(missing_ids)

    print(f"Result: {total_missing} dataset(s) are missing.")

    # 4. Write results to output file
    output_content = json.dumps(missing_ids)

    try:
        with open(args.output_file, "w") as f:
            f.write(output_content)
        print(f"Missing IDs written to '{args.output_file}'.")
    except IOError as e:
        print(f"Error writing to file '{args.output_file}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
