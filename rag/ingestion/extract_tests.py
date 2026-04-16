import os

def get_test_files(repo_path: str):
    test_files = []

    for root, _, files in os.walk(repo_path):
        if "tests" in root:
            for f in files:
                if f.endswith(".py"):
                    test_files.append(os.path.join(root, f))

    return test_files
