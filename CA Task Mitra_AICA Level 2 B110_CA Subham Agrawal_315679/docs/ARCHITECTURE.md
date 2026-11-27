# Architecture

```mermaid
flowchart LR
  subgraph PC[Firm PC - CA Task Mitra]
    UI[Browser UI - Chrome app window] --> API[Python server - http.server]
    API --> CORE[Core: auth, roles, audit, module registry, event bus]
    CORE --> MODS[12 modules - one file each]
    MODS --> DB[(SQLite database)]
  end
  STAFF[Staff browsers - same Wi-Fi] --> API
  MODS -->|XML port 9000| TALLY[TallyPrime]
  MODS -->|webhook| N8N[n8n] --> MAIL[CA e-mail]
  MODS -->|SMTP or .eml file| CLIENT[Client e-mail after CA approval]
  UI -->|prompt link| AI[Claude / ChatGPT]
```

## Workflow
```mermaid
flowchart TD
  A[Compliance master + applicability] --> B[Generate assignments]
  B --> C[Employee works: checklist, documents]
  C -->|documents missing| D[Draft e-mail] --> E{CA approves?} -->|yes| F[Sent to client]
  C --> G[Submit for review] --> H{CA review}
  H -->|send back| C
  H -->|approve and close| I[Auto invoice] --> J[Tally queue] --> K[Posted now or with next bill]
  A --> L[Alerts via n8n to CA]
```

## Design points
- **Modular monolith:** each module exposes `MANIFEST`, `SCHEMA`, a router and optional `seed`/`demo`; the registry loads them and keeps on/off state per module and sub-module, with dependency checks.
- **Loose coupling:** modules talk through an event bus (e.g. `assignment.closed` → invoice → `invoice.created` → Tally queue).
- **Security:** pbkdf2 password hashing, cookie sessions, role checks on every route, audit log of every change, secrets masked.
- **Standard library only:** Python http.server, sqlite3, urllib, smtplib – easy to package as an EXE.
