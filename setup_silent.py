import sys
import os

python_exe = sys.executable
pythonw_exe = os.path.join(os.path.dirname(python_exe), 'pythonw.exe')
if not os.path.exists(pythonw_exe):
    pythonw_exe = python_exe

base_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(base_dir, 'server_runner.py')

vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{base_dir}"
WshShell.Run """{pythonw_exe}"" ""{script_path}""", 0, False
'''

with open(os.path.join(base_dir, 'Start_Silent_Server.vbs'), 'w', encoding='ascii') as f:
    f.write(vbs_content)

print("Start_Silent_Server.vbs generated successfully.")
