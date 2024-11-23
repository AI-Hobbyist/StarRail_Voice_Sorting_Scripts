import os
import argparse

def remove_empty_folders(path):
    if not os.path.isdir(path):
        return
    
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs:
            folder_path = os.path.join(root, name)
            if not os.listdir(folder_path):
                os.rmdir(folder_path)
                print(f"Deleted empty folder: {folder_path}")

def main():
    parser = argparse.ArgumentParser(description="Remove empty folders from a specified directory.")
    parser.add_argument("path", type=str, help="The root directory path to clean up.")
    args = parser.parse_args()
    
    remove_empty_folders(args.path)
    print("Done!")

if __name__ == "__main__":
    main()
