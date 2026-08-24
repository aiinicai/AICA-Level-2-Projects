# SSA Kartavya

SSA Kartavya is a front-end practice management portal designed for a Chartered Accountancy firm. It brings client records, team operations, service engagements, timesheets, compliance jobs, and management reporting into one browser-based dashboard.

> Academic capstone project — built for demonstration and learning purposes.

## Features

- Practice dashboard with operational KPIs, alerts, workload indicators, and profitability visualisation
- Client master with onboarding, GSTIN validation, contacts, engagements, archive/restore, CSV import, and bulk updates
- Team and roster management with role-based views, employee profiles, organisational structure, and profitability metrics
- Service catalogue for defining recurring and one-time service offerings
- Timesheet logging, daily hour limits, approval/rejection workflow, and employee-specific ledgers
- Compliance jobs board with card/list views, priorities, due dates, review flow, notifications, and role-based task controls
- Client and profitability reports based on budgeted engagements and recorded time
- Light and dark themes, plus responsive styling for smaller screens

## Technology

- HTML5
- CSS3
- Vanilla JavaScript
- [Chart.js](https://www.chartjs.org/) for dashboard charts
- Browser Local Storage for demonstration data persistence

## Run locally

No build step or package installation is required.

1. Download or clone this repository.
2. Open `index.html` in a modern browser.
3. Sign in using one of the included demo profiles.

For the most reliable experience, serve the project through a simple local web server (for example, VS Code Live Server).

## Demo access

All seeded demo profiles use the following password:

```text
password123
```

Example profiles:

| Role | Profile |
| --- | --- |
| Partner | Sheth Solani |
| Partner | Munjal Solani |
| Manager | Riddhi Desai |
| Staff Associate | Vikram Patel |

## Data storage

The project stores working data in the browser under the local-storage key `SSA_KARTAVYA_STATE`.

This means data is local to the browser profile and device. Clearing browser/site data, using a different browser, or opening the application under a different address can reset the project to its seeded demo data.

## Important limitations

This application is a front-end prototype, not a production system. It does not include a server-side database, real authentication, encrypted passwords, or server-enforced access control. Do not use it to store real client, financial, tax, or personal data.

## Project files

| File | Purpose |
| --- | --- |
| `index.html` | Application structure and interface markup |
| `style.css` | Visual system, themes, responsive layout, and component styling |
| `app.js` | Central state, dashboard, jobs, timesheets, reports, and authentication flow |
| `clients.js` | Client master, onboarding, CSV import, bulk actions, and client profiles |
| `team.js` | Team management, employee profiles, roster, and profitability logic |
| `tests.html` | Browser-based verification test runner |

## Future enhancements

- Add a secure backend and database
- Implement real password hashing and authenticated sessions
- Move authorization checks to the server
- Sanitize all user-generated content before rendering
- Add automated browser tests and continuous integration
- Deploy the application using GitHub Pages or another hosting platform

## Author

Capstone project submission by **[Your Name]**.

