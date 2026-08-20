import os
import sys
import subprocess

def install_dependencies():
    """Checks and installs missing dependencies on first run."""
    try:
        import PyQt5
        import reportlab
    except ImportError:
        print("Required libraries (PyQt5, reportlab) are missing. Installing them now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt5", "reportlab"])
            print("Installation complete! Launching application...")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)

# Ensure required libraries are installed
install_dependencies()

from PyQt5.QtWidgets import QApplication, QDialog
from app.license_manager import check_license_status, get_base_dir
from app.database import get_database_dir
from app.gui.license_dialog import LicenseDialog
from app.gui.main_window import MainWindow
from app.gui.auth_dialogs import LoginDialog

def main():
    # Setup working folders in the directory of main.py or execution path
    base_dir = get_base_dir()
    db_dir = get_database_dir()
    pdf_dir = os.path.join(base_dir, "invoices_pdf")
    
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(os.path.join(db_dir, "invoices"), exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # Run License activation verification first
    valid, msg, remaining = check_license_status()
    if not valid:
        # Prompt user to input license key
        dialog = LicenseDialog()
        if dialog.exec_() != LicenseDialog.Accepted:
            sys.exit(0)  # Close app if dialog is canceled
            
    while True:
        # Login prompt
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            sys.exit(0)  # Close app if login is canceled or fails
            
        current_user = login_dialog.get_logged_in_user()
        current_role = login_dialog.get_logged_in_role()
        
        # If license is active and logged in, launch Main Window
        window = MainWindow(current_user=current_user, current_role=current_role)
        window.showMaximized()
        
        # Execute app event loop
        app.exec_()
        
        # If switch user was not requested, exit the loop to close the application
        if not getattr(window, "logout_requested", False):
            sys.exit(0)

if __name__ == "__main__":
    main()
