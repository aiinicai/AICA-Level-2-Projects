# BESPOKE TAX ADVISOR - Setup Instructions
| AICA Level 2 Capstone 2026
## STEP 1 - Create folder structure
Create these folders on your laptop:
  C:\DTAA\
  C:\DTAA\treaties\

## STEP 2 - Copy all app files into C:\DTAA\
Copy these 4 files into C:\DTAA\:
  app.py
  advisor.py
  treaty_reader.py
  .env

## STEP 3 - Copy treaty PDFs
Copy ALL your downloaded treaty PDFs into:
  C:\DTAA\treaties\

## STEP 4 - Add your API key
Open C:\DTAA\.env in Notepad
Replace sk-ant-your-key-here with your actual key

## STEP 5 - Install libraries
Open Command Prompt and run:
  pip install streamlit pypdf2 anthropic python-dotenv pandas plotly

## STEP 6 - Run the app
Open Command Prompt and run:
  cd C:\DTAA
  streamlit run app.py

## App opens at:
  http://localhost:8501
