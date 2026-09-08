================================================================================
ICAI AICA LEVEL 2 CAPSTONE PROJECT SUBMISSION
================================================================================

Project Title:
CA Academy Mentorship & Examination Hub

Candidate Details:
• Name: CA Ramesh Bhandari
• ICAI Membership Number: 096548
• Batch Number: L2 B85
• Course: AICA Level 2

Video Walkthrough Link (Google Drive):
https://drive.google.com/file/d/1Pz5aypASQT70eUm0TUoGOGkUBjDYbpXR/view?usp=drive_link
(Access Setting: Anyone with the link can view)

--------------------------------------------------------------------------------
1. PROJECT OVERVIEW & SCOPE
--------------------------------------------------------------------------------
CA Academy Mentorship & Examination Hub is an institutional-grade coaching and 
examination management web portal designed specifically for Chartered Accountancy 
training institutes and aspirants.

Key Functional Modules:
1. Dynamic ICAI Syllabus Mapping:
   Covers CA Foundation (4 Papers), CA Intermediate (6 Papers), and CA Final (6 Papers).

2. Dual-Mode Test Paper Management:
   Faculty can generate test papers dynamically using AI prompts or publish custom 
   institutional test papers directly via PDF text extraction and manual input.

3. Exam Security & Model Solution Shielding:
   Suggested model answers and evaluation keys remain locked and inaccessible to 
   students until papers are formally reviewed and graded by faculty.

4. Multimodal Answer Submission & Grading:
   Students can submit typed working notes or upload camera scans of physical, 
   handwritten answer sheets for faculty evaluation and AI-assisted marking.

5. Synchronized Mentorship & Doubt Clearing:
   24/7 AI Tutor responses to student queries are automatically logged into the 
   faculty mentorship dashboard for teacher validation and endorsement.

6. ICAI Exemption & Gap Analytics:
   Interactive Plotly tracking for 40% individual paper passing minimums, 60% 
   exemption thresholds, and overall 50% aggregate benchmarks.

--------------------------------------------------------------------------------
2. TECHNICAL ARCHITECTURE & STACK
--------------------------------------------------------------------------------
• Programming Language: Python 3.10+
• User Interface: Streamlit
• Persistent Database: SQLite3 (`ca_academy.db`)
• Data Visualization: Plotly Express
• Document Processing: pypdf, Pillow (PIL)
• Generative AI Engine: Google Gemini API (gemini-3.6-flash / fallback)

--------------------------------------------------------------------------------
3. PROJECT FOLDER STRUCTURE
--------------------------------------------------------------------------------
├── app.py                  # Core Streamlit application logic
├── ca_academy.db           # Persistent SQLite database with seed records
├── run_app.bat             # 1-Click launcher script for Windows
├── requirements.txt        # Python library dependencies
├── project_title.html      # Title presentation slide (HTML/CSS)
└── README.txt              # Project summary and documentation

--------------------------------------------------------------------------------
4. HOW TO RUN THE APPLICATION LOCALLY
--------------------------------------------------------------------------------
Method A (Automated):
Double-click `run_app.bat` to launch the application in your default browser.

Method B (Manual):
1. Open Command Prompt or Terminal in the project directory.
2. Install dependencies:
   pip install -r requirements.txt
3. Run the Streamlit application:
   streamlit run app.py

--------------------------------------------------------------------------------
5. PRE-SEEDED TEST CREDENTIALS
--------------------------------------------------------------------------------
Faculty / Admin Account:
• Role: Teacher
• Username: admin
• Password: 123

Student Account:
• Role: Student
• Username: stu101
• Password: 123
================================================================================