import subprocess
import os

git_exe = r"C:\Program Files\Git\cmd\git.exe"
repo_dir = r"c:\Users\ADMIN\Desktop\Capstone\Application\source\FinstockEventScope"

def run_git(args):
    res = subprocess.run([git_exe] + args, cwd=repo_dir, capture_output=True, text=True)
    cmd_str = " ".join(args)
    print(f"git {cmd_str} -> code {res.returncode}")
    if res.stdout:
        print("STDOUT:\n" + res.stdout[:500])
    if res.stderr:
        print("STDERR:\n" + res.stderr[:500])
    return res

if __name__ == "__main__":
    run_git(["add", "."])
    run_git(["commit", "-m", "Initial commit: FinstockEventScope ICAI Capstone Project submission"])
    run_git(["branch", "-M", "main"])
    run_git(["status"])
