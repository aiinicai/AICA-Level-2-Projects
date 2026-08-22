# Direct Tax Litigation Tracker

## Capstone Project – Evaluator Guide

The **Direct Tax Litigation Tracker** is a full-stack web application designed to help manage and monitor direct tax proceedings across client groups, entities and assessment years.

### 1. Project Objective

The application centralizes key information relating to direct tax proceedings, including:

- Proceedings and assessment years
- Nature of proceeding
- Relevant legal section
- Current litigation stage
- Hearing dates and statutory timelines
- Raised demand and estimated demand
- Overdue/action-required matters
- Client groups, entities and users
- Dashboard analytics and summaries

The application is intended as an academic capstone project demonstrating a practical professional use case.

---

## 2. Technology Stack

### Frontend
- React
- Vite
- JavaScript / JSX
- Responsive dashboard UI

### Backend
- Node.js
- Express
- REST API architecture

### Database
- SQLite for the local demonstration environment

### Other
- npm for dependency management
- Git/GitHub for version control and submission

---

## 3. Application Architecture

```text
Browser
   |
   v
React + Vite
   |
   v
Node.js + Express REST API
   |
   v
SQLite Database
```

The frontend communicates with the backend API. Database operations are performed by the server rather than directly by the browser.

---

## 4. Requirements

Install:

- Node.js 18 or later
- npm (included with Node.js)
- A modern web browser such as Chrome, Edge or Firefox

No Python installation is required for this application.

---

## 5. How to Run the Application

### Option A – From the GitHub repository

Clone the repository:

```bash
git clone https://github.com/jyotikauricai-blip/AICA-Level-2-Projects.git
```

Go to the project folder:

```bash
cd AICA-Level-2-Projects\Direct-Tax-Litigation-Tracker
```

Install dependencies:

```bash
npm install
```

Start the application:

```bash
npm run dev
```

The terminal should display:

```text
Litigation Tracker API listening on http://localhost:4000
```

and a Vite URL similar to:

```text
http://localhost:5173/
```

Open the displayed frontend URL in your browser.

### Important

Keep the terminal window open while using the application. Closing it stops the local development servers.

---

## 6. Demo Login

For the academic demonstration environment:

```text
User ID: admin
Password: Admin@123
```

Use only the supplied demo credentials for evaluation. Do not place real client or taxpayer information into the demonstration database.

---

## 7. Main Modules

### Litigation Dashboard

The dashboard provides a consolidated view of:

- Total proceedings
- Ongoing proceedings
- Raised demand
- Estimated demand
- Statutory/overdue alerts
- Assessment-year and other filters
- Litigation progression by stage

### Proceedings

A proceeding can capture:

- Client group / entity
- Assessment year
- Nature of proceeding
- Relevant section
- Act
- Current stage
- Hearing date
- Status
- Demand classification
- Raised demand
- Estimated demand
- Notes and supporting details

### Demand Tracking

The application distinguishes between:

- **Raised demand** – formal demand recorded for the proceeding
- **Estimated demand** – provisional or working exposure recorded separately

This prevents estimated amounts from being presented as though they were necessarily formal statutory demand.

### Timeline and Alerts

The dashboard highlights:

- Upcoming hearings
- Hearings within the alert window
- Overdue timelines
- Action-required matters

### User and Access Management

The application supports role/group-oriented access so that different users can be restricted to the matters relevant to their assigned group.

---

## 8. Privacy and Security

Privacy was treated as a key design consideration for this project.

The demonstration application includes server-side authentication and authorization concepts, with application data handled through the backend/API layer.

The GitHub submission intentionally excludes:

- `node_modules`
- Local SQLite database files
- Local database journal files
- Secrets and environment credentials
- Real client/taxpayer data

### Production note

This academic version uses SQLite for local demonstration. For a production internet-facing deployment, the architecture should be further hardened with HTTPS, a managed production database, secure environment-managed secrets, backup/recovery procedures, secure session configuration, monitoring and additional operational controls.

---

## 9. Project Structure

```text
Direct-Tax-Litigation-Tracker/
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── README.md
├── START_HERE.txt
├── run_app.bat
├── vite.config.js
├── server/
│   └── server.js
└── src/
    ├── App.jsx
    ├── LitigationTracker.jsx
    └── main.jsx
```

The local `data/` directory is intentionally not included in the GitHub submission. The application can create the required local database at runtime.

---

## 10. Troubleshooting

### `npm is not recognized`

Install Node.js, close Command Prompt, open a new Command Prompt, and verify:

```bash
node --version
npm --version
```

### `This site can't be reached` / `ERR_CONNECTION_REFUSED`

Make sure the development server is running:

```bash
npm run dev
```

Then open the exact Vite URL shown in the terminal, normally:

```text
http://localhost:5173/
```

Do not close the terminal while the application is running.

### `package.json` not found

Make sure Command Prompt is opened in the **Direct-Tax-Litigation-Tracker** folder containing `package.json`.

### Port already in use

Close any previous development server or use the new port displayed by Vite.

---

## 11. Academic Submission

The source code is submitted through the AICA Level 2 project repository using the Fork + Pull Request workflow.

GitHub repository:

https://github.com/jyotikauricai-blip/AICA-Level-2-Projects

Project folder:

```text
Direct-Tax-Litigation-Tracker
```

---

## 12. Capstone Demonstration

The project demonstration covers:

1. Problem statement and objective
2. Technology stack and architecture
3. Authentication and role-based access
4. Litigation dashboard
5. Proceedings management
6. Relevant section and assessment-year tracking
7. Raised versus estimated demand
8. Hearing and statutory timeline alerts
9. Privacy/security considerations
10. GitHub-based project submission

---

## 13. Important Evaluation Note

This repository contains the **source code and setup instructions** for the application. `localhost` URLs are local-development addresses and are available only on the computer where the application servers are running.

For an internet-accessible production deployment, the application must be deployed to a hosting environment and configured with a production database and security controls.
