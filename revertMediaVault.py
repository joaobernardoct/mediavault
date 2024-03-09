import csv
import os

'''
This script reverts the operation of MediaVault.py
It picks up all the new file paths and restores the old file path

BE AWARE: If you just want to revert a portion of the operation,
          i.e. just revert SOME of the new file paths, move all the
          files you don't want to revert into a separate folder        
'''


# log_file should be a CSV/MARKDOWN structured in the format of:
# | Old File Path     | New File Path                |
# | ----------------  | ---------------------------- |
# | old/path/file.txt | new/path/somefolder/name.txt |
#                    ...
def revertMediaVault(log_file):
    print("Starting the operation...")
    with open(log_file, 'r') as file:
        content = file.readlines()
        for line in content:
            # Split the line by the pipe character '|'
            parts = [part.strip() for part in line.split("|") if part.strip()]
            # Extract the values
            old_path = parts[0]
            new_path = parts[1]
            # Try to revert (new_path --> old_path)
            try:
                if os.path.exists(new_path):
                    os.rename(new_path, old_path)
                    print(f"Renamed {new_path} to {old_path}")
                else:
                    # File does not exist
                    pass
            except Exception as e:
                print(f"An error occurred while processing {new_path}: {e}")

if __name__ == "__main__":
    log_file = "_log.md"
    revertMediaVault(log_file)