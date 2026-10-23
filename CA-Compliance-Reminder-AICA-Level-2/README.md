# CA Compliance Reminder & Automation Syste
\# CA Compliance Reminder \& Automation System



\*\*AICA Level 2 Capstone Project\*\*



\*\*Developed by:\*\* CA Rajesh R



\## 1. Project Overview



The CA Compliance Reminder \& Automation System is a Python-based application designed to help Chartered Accountants track client compliance due dates and manage reminders.



The application integrates Google Sheets, Gmail, and Google Calendar to support compliance tracking, email reminders, and calendar event management.



\## 2. Problem Statement



Chartered Accountants manage multiple clients with different statutory and tax compliance deadlines. Manual tracking can lead to missed due dates, repetitive work, and difficulty monitoring reminder activity.



This project aims to simplify compliance monitoring through a central dashboard and automated reminder processing.



\## 3. Project Objectives



\- Track client compliance details and due dates.

\- Read compliance records from Google Sheets.

\- Send email reminders for qualifying upcoming due dates.

\- Create Google Calendar events and avoid duplicate events.

\- Maintain reminder and activity records.

\- Automate daily processing using Windows Task Scheduler.



\## 4. Main Features



\- Flask-based web dashboard.

\- Google Sheets integration.

\- Gmail API integration for reminder emails.

\- Google Calendar integration.

\- SQLite database for activity records and duplicate-reminder prevention.

\- Manual processing and test-email functionality.

\- CSV export of activity history.

\- Daily job execution through Windows Task Scheduler.



\## 5. Technology Stack



\- Python

\- Flask

\- Google Sheets API

\- Gmail API

\- Google Calendar API

\- SQLite

\- HTML templates

\- Windows Task Scheduler



\## 6. Application Workflow



1\. Client compliance details and due dates are maintained in Google Sheets.

2\. The application reads and validates the records.

3\. The dashboard displays compliance information.

4\. The daily job checks records against the reminder rules.

5\. Eligible reminders are sent through Gmail.

6\. Calendar events are created where applicable.

7\. SQLite stores reminder and activity information to help prevent duplicate processing.



\## 7. Project Structure



```text

CA\_Compliance\_Reminder\_App/

├── app.py

├── daily\_job.py

├── run\_daily\_job.bat

├── requirements.txt

├── README.md

├── templates/

├── .env

├── credentials.json

├── token.json

└── \[SQLite database file]

```



The exact files may differ depending on your local setup. Secret files and local databases should not be included in a public repository.



\## 8. Installation and Setup



Prerequisites:

\- Python installed on Windows.

\- A Google account.

\- A Google Cloud project with the required Google APIs configured.

\- Appropriate Google OAuth credentials and permissions.



Steps:



1\. Download or clone the project into a clearly named folder.

2\. Open Command Prompt in the project folder.

3\. Create a virtual environment:



&#x20;  `python -m venv .venv`



4\. Activate the virtual environment:



&#x20;  `.venv\\Scripts\\activate`



5\. Install dependencies:



&#x20;  `pip install -r requirements.txt`



6\. Configure the required environment variables and Google API credentials locally.

7\. Ensure the Google Sheet ID and required Google permissions are configured according to the application code.



Do not publish credentials, access tokens, passwords, or private client data.



\## 9. Running the Application



Start the dashboard:



`python app.py`



Open the local address displayed in the terminal, typically:



`http://127.0.0.1:5000`



Run the daily reminder job in a separate Command Prompt:



`python daily\_job.py`



For automatic daily processing, configure `run\_daily\_job.bat` or the Python job in Windows Task Scheduler.



The computer must be switched on and available for a locally scheduled job to execute.



\## 10. Testing Performed



The following functions have been tested during development:



\- Google Sheets connection.

\- Test email delivery.

\- Google Calendar event creation.

\- Manual execution of the daily reminder job.

\- Duplicate-reminder prevention logic.

\- Windows Task Scheduler execution.



The reminder job completed a test run without reported errors. Full end-to-end operation should be verified using controlled test records before production use.



\## 11. Security and Limitations



\- The application requires valid Google API authorization.

\- Email sending and Calendar access depend on configured permissions.

\- Daily processing on a local computer requires the computer to be running.

\- Reminder behaviour depends on the configured due-date rules.

\- Test data should be used during demonstrations.

\- The application is a prototype and should be further tested before being used for real client compliance management.

\- Credentials, OAuth tokens, and confidential client information must remain private.



\## 12. Future Enhancements



\- Cloud-based scheduled execution.

\- Multiple reminder intervals and escalation rules.

\- Improved reporting and compliance status indicators.

\- Role-based access control.

\- Stronger production security and deployment.

\- Additional statutory compliance categories.



\## 13. Conclusion



This project demonstrates how Python automation and Google services can assist Chartered Accountants in tracking compliance deadlines, sending reminders, managing calendar events, and reducing repetitive administrative work.



