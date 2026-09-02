#!/bin/bash
# MSME Debtors Management - Mac/Linux Launcher
echo "Opening MSME Debtors Management System..."
if which open >/dev/null; then
  # MacOS
  open "https://msme-debtors-manager.ai.studio"
elif which xdg-open >/dev/null; then
  # Linux
  xdg-open "https://msme-debtors-manager.ai.studio"
else
  echo "Please open your browser and navigate to: https://msme-debtors-manager.ai.studio"
fi
