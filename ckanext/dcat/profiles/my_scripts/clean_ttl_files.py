import os
import sys
import argparse
import re

# Default Base URI
BASE_URI = "https://search.nfdi4chem.de/dataset/"

def clean_turtle_content(content: str) -> str:
    """
    Cleans the Turtle content:
    1. Removes '@base' and erroneous '@prefix @base:' lines.
    2. Identifies the dataset ID from the dcat:Dataset subject.
    3. Replaces the Dataset subject with the absolute IRI.
    4. Expands ANY relative or partial IRI referencing this dataset ID 
       (e.g., <#sample>, <msbnk-...#sample_compound>) to absolute IRIs.
    """
    lines = content.splitlines()
    cleaned_lines = []
    
    dataset_id = None
    # Regex to find the main dataset subject definition: <...> a dcat:Dataset
    dataset_subject_pattern = re.compile(r'^<([^>]+)>\s+a\s+dcat:Dataset')
    
    # First pass: Remove base lines and identify the Dataset ID
    for line in lines:
        strip_line = line.strip()
        
        # Skip base declarations
        if strip_line.startswith('@base') or strip_line.startswith('@prefix @base:'):
            continue
            
        # Identify Dataset ID if not found yet
        if dataset_id is None:
            match = dataset_subject_pattern.match(strip_line)
            if match:
                potential_id = match.group(1)
                
                # Normalize: Extract the local ID if it's already absolute or relative
                if potential_id.startswith(BASE_URI):
                    # It's already absolute, extract the local part
                    local_part = potential_id.replace(BASE_URI, "")
                    # Remove fragment if present (e.g. if the subject was mistakenly defined with a fragment)
                    if '#' in local_part:
                        local_part = local_part.split('#')[0]
                    dataset_id = local_part
                elif not potential_id.startswith('http'):
                    # It's relative (e.g., msbnk-...)
                    if '#' in potential_id:
                        dataset_id = potential_id.split('#')[0]
                    else:
                        dataset_id = potential_id
        
        cleaned_lines.append(line)
    
    if not dataset_id:
        # If no dataset ID found, just return content without base lines
        return "\n".join(cleaned_lines)

    # Construct the base absolute IRI for this dataset
    full_dataset_base = f"{BASE_URI}{dataset_id}"
    
    # Rejoin lines for text processing
    text_block = "\n".join(cleaned_lines)
    
    # 1. Replace the Dataset Subject Definition
    # Ensure the main subject is exactly <full_base_uri> a dcat:Dataset
    escaped_id = re.escape(dataset_id)
    
    # Patterns for the subject line (relative or already absolute)
    # We use multiline flag (^) to ensure we only hit the start of the definition
    subject_patterns = [
        rf'^<{escaped_id}>\s+a\s+dcat:Dataset',                # Relative: <msbnk-...>
        rf'^<{re.escape(full_dataset_base)}>\s+a\s+dcat:Dataset' # Already absolute
    ]
    
    new_subject = f'<{full_dataset_base}> a dcat:Dataset'
    
    for pattern in subject_patterns:
        text_block = re.sub(pattern, new_subject, text_block, flags=re.MULTILINE)
    
    # 2. Normalize ALL Fragment References for this Dataset
    # We look for any IRI that starts with the dataset_id (or nothing) followed by #
    # Patterns to catch:
    # A) <#fragment> (Purely relative)
    # B) <dataset_id#fragment> (Partial: the missed case including #sample_compound)
    # C) <http://wrong_base...dataset_id#fragment> (Less likely, but handled if base matches logic)
    
    # We construct a regex that matches < optionally followed by the ID, then #, then the fragment name >
    # Fragment names can contain letters, numbers, underscores, hyphens.
    # Regex: <(dataset_id)?#([^>]+)>
    
    def replace_fragment(match):
        # match.group(0) is the whole match e.g. <#sample> or <msbnk-...#sample_compound>
        # match.group(1) is the ID part (might be empty if purely relative)
        # match.group(2) is the fragment name (e.g. "sample_compound")
        
        fragment_name = match.group(2)
        # Construct the correct absolute IRI
        return f'<{full_dataset_base}#{fragment_name}>'

    # Pattern explanation:
    # <             : Literal start of IRI
    # (?:...)?      : Non-capturing group for the ID, optional (covers both <#...> and <id#...>)
    #   {escaped_id}: The specific dataset ID
    #   |           : OR
    #   (empty)     : Nothing (for purely relative <#...>)
    # #             : Literal hash
    # ([^>]+)       : Capturing group for the fragment name (everything until >)
    # >             : Literal end of IRI
    
    # We need to be careful with order. If we match <id#...>, we replace. If we match <#...>, we replace.
    # A single regex can handle both if we make the ID part optional but specific.
    
    # Option 1: Match <#fragment>
    pattern_relative = rf'<#([^>]+)>'
    # Option 2: Match <dataset_id#fragment>
    pattern_partial = rf'<{escaped_id}#([^>]+)>'
    
    # Apply replacement for partial matches first (more specific)
    # We use a lambda to reconstruct the full IRI
    text_block = re.sub(pattern_partial, lambda m: f'<{full_dataset_base}#{m.group(1)}>', text_block)
    
    # Apply replacement for purely relative matches
    text_block = re.sub(pattern_relative, lambda m: f'<{full_dataset_base}#{m.group(1)}>', text_block)
    
    return text_block

def process_file(file_path: str) -> bool:
    """
    Reads, cleans, and overwrites the file if changes were made.
    Returns True if modified, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        cleaned_content = clean_turtle_content(original_content)
        
        if original_content != cleaned_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_directory(dir_path: str, stats: dict):
    """
    Scans a directory for msbnk-*.ttl files and processes them.
    Updates the stats dictionary.
    """
    if not os.path.exists(dir_path):
        print(f"⚠️  Directory not found: {dir_path}")
        return

    print(f"Scanning: {dir_path}")
    
    try:
        for filename in os.listdir(dir_path):
            if filename.startswith("msbnk-") and filename.endswith(".ttl"):
                file_path = os.path.join(dir_path, filename)
                stats['total'] += 1
                
                if process_file(file_path):
                    stats['modified'] += 1
                    print(f"  ✅ Fixed: {filename}")
                # else:
                #     print(f"  OK: {filename}")
    except PermissionError:
        print(f"⚠️  Permission denied accessing {dir_path}")
    except Exception as e:
        print(f"⚠️  Error scanning {dir_path}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Update Turtle files (msbnk-*) to use absolute IRIs for all fragments."
    )
    parser.add_argument(
        'folders', 
        nargs='+', 
        help="One or more folder paths to scan (e.g., path/to/folder1 path/to/folder2)"
    )
    
    args = parser.parse_args()
    
    stats = {'total': 0, 'modified': 0}
    
    print(f"Starting migration to absolute IRIs...")
    print(f"Target prefix: 'msbnk-'")
    print(f"Base URI: {BASE_URI}")
    print("-" * 50)

    for folder_path in args.folders:
        clean_path = folder_path.strip('"').strip("'")
        process_directory(clean_path, stats)

    print("-" * 50)
    print(f"Migration complete.")
    print(f"Total files checked: {stats['total']}")
    print(f"Files modified: {stats['modified']}")

if __name__ == '__main__':
    main()