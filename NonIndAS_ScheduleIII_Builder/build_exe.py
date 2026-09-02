import os
import subprocess
import sys

def build_installer():
    print("Building standalone Windows executable (.exe) for Non Ind AS Schedule III Financial Statements Builder...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base_dir, "src", "app.py")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=Non_Ind_AS_Schedule_III_Builder",
        f"--add-data={os.path.join(base_dir, 'static')};static",
        f"--add-data={os.path.join(base_dir, 'templates')};templates",
        main_script
    ]
    
    print("Running PyInstaller command:")
    print(" ".join(cmd))
    
    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode == 0:
        print("\nSuccess! Windows application package created in 'dist/Non_Ind_AS_Schedule_III_Builder'")
    else:
        print("\nBuild failed with exit code:", result.returncode)

if __name__ == '__main__':
    build_installer()
