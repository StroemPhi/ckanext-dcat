"""
helper script to split the huge Massbank folder into parts of max 26000 files
"""
import os
import shutil
import sys
import re
import math

def get_next_part_number(parent_dir, base_name):
    """
    Scans the parent directory for existing folders matching '{base_name}_ptX'
    and returns the next available integer X.
    """
    existing_parts = []
    
    if not os.path.isdir(parent_dir):
        return 1
        
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path):
            pattern = rf"^{re.escape(base_name)}_pt(\d+)$"
            match = re.match(pattern, item)
            
            if match:
                part_num = int(match.group(1))
                existing_parts.append(part_num)
    
    if not existing_parts:
        return 1
    
    return max(existing_parts) + 1

def split_folder_resumable(source_path, batch_size=10000, output_parent_dir=None, save_mode=True):
    """
    Splits files from a source folder into NEW sibling folders.
    
    Parameters:
    - source_path: Path to the source folder.
    - batch_size: Number of files per new folder.
    - output_parent_dir: Optional parent directory for the new parts (defaults to source parent).
    - save_mode: If True (default), COPIES files (keeps originals). If False, MOVES files (deletes originals).
    """
    
    if not os.path.isdir(source_path):
        print(f"Error: The path '{source_path}' is not a valid directory.")
        return

    source_parent = os.path.dirname(source_path)
    base_name = os.path.basename(source_path)
    
    if not source_parent:
        print("Error: Cannot determine source parent directory.")
        return

    # Determine output directory
    if output_parent_dir is None:
        output_parent = source_parent
    else:
        if not os.path.isdir(output_parent_dir):
            print(f"Error: The output directory '{output_parent_dir}' does not exist.")
            return
        output_parent = output_parent_dir

    # Get files to process
    all_items = os.listdir(source_path)
    files = [f for f in all_items if os.path.isfile(os.path.join(source_path, f))]
    
    # Exclude script itself if present in source
    script_name = os.path.basename(__file__)
    files = [f for f in files if f != script_name]

    total_files = len(files)
    
    if total_files == 0:
        print("No files found to process. The source folder is empty or contains only subfolders.")
        return

    # Detect existing parts in the OUTPUT directory
    start_part = get_next_part_number(output_parent, base_name)
    
    # Determine action text based on save_mode
    if save_mode:
        action = "COPY"
        action_detail = "Originals kept"
    else:
        action = "MOVE"
        action_detail = "Originals deleted"
        
    print(f"Source Folder: {base_name}")
    print(f"Source Location: {source_parent}")
    if output_parent != source_parent:
        print(f"Output Location: {output_parent}")
    print(f"Operation Mode: {action} ({action_detail})")
    print(f"Files to process: {total_files}")
    print(f"Existing parts found: {start_part - 1} (Will start creating at _pt{start_part})")
    print(f"Target batch size: {batch_size} files per new folder.")
    
    num_batches = math.ceil(total_files / batch_size)
    end_part = start_part + num_batches - 1
    
    print(f"This run will create folders from _pt{start_part} to _pt{end_part}.")
    
    user_confirm = input(f"Do you want to proceed with {action} mode? (yes/no): ").strip().lower()
    if user_confirm != 'yes':
        print("Operation cancelled.")
        return

    files.sort()
    processed_count = 0
    current_part = start_part

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_files)
        current_batch = files[start_idx:end_idx]
        
        new_folder_name = f"{base_name}_pt{current_part}"
        new_folder_path = os.path.join(output_parent, new_folder_name)
        
        if os.path.exists(new_folder_path):
            print(f"Warning: Folder {new_folder_name} already exists. Skipping to next...")
            current_part += 1
            continue

        os.makedirs(new_folder_path, exist_ok=True)
        print(f"Creating: {new_folder_name}...")
        
        for filename in current_batch:
            src_file = os.path.join(source_path, filename)
            dst_file = os.path.join(new_folder_path, filename)
            
            try:
                if save_mode:
                    shutil.copy2(src_file, dst_file) # Copy (keeps original)
                else:
                    shutil.move(src_file, dst_file) # Move (deletes original)
                processed_count += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        
        current_part += 1

    print(f"\nSuccess! {action}d {processed_count} files into new folders.")
    print(f"Next run will automatically start at _pt{current_part}.")
    
    if save_mode:
        print(f"Original files remain in '{source_path}'.")
    else:
        remaining = len(os.listdir(source_path))
        if remaining == 0:
            print(f"The original folder '{base_name}' is now empty.")
        else:
            print(f"The original folder '{base_name}' still contains {remaining} items (likely subfolders).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python split_folder_resumable.py <path_to_folder> [path_to_output_parent] [mode]")
        print("  mode: 'copy' (default, safe_mode=True) or 'move' (safe_mode=False)")
        print("Example 1 (Copy, default): split_folder_resumable.py /path/to/source")
        print("Example 2 (Move): split_folder_resumable.py /path/to/source move")
        print("Example 3 (Copy to specific output): split_folder_resumable.py /path/to/source /path/to/output copy")
        print("Example 4 (Move to specific output): split_folder_resumable.py /path/to/source /path/to/output move")
    else:
        BATCH_SIZE = 26000 
        source_path = sys.argv[1].strip('"')
        output_dir = None
        mode_str = "copy" # Default to "copy" (save_mode=True)
        
        # Parse optional arguments
        if len(sys.argv) > 2:
            arg2 = sys.argv[2].strip('"')
            
            # Check if it's a mode string or a path
            if arg2.lower() in ['copy', 'move']:
                mode_str = arg2.lower()
            elif os.path.isdir(arg2) or os.path.exists(arg2):
                output_dir = arg2
                if len(sys.argv) > 3:
                    mode_str = sys.argv[3].strip('"').lower()
            else:
                # Ambiguous: if it looks like a path (contains separators) treat as path, else mode
                if '/' in arg2 or '\\' in arg2:
                    output_dir = arg2
                    if len(sys.argv) > 3:
                        mode_str = sys.argv[3].strip('"').lower()
                else:
                    mode_str = arg2.lower()
        
        # Convert mode string to boolean for save_mode
        # save_mode=True means COPY (Safe)
        # save_mode=False means MOVE
        save_mode = (mode_str == 'copy')
        
        split_folder_resumable(source_path, batch_size=BATCH_SIZE, output_parent_dir=output_dir, save_mode=save_mode)