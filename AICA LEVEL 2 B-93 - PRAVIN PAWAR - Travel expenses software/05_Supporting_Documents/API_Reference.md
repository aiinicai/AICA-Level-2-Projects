# ABC Travel & Expense – REST API Reference

Base URL: `http://<server>:8080`. All requests and responses are JSON. After login, send the token as
`Authorization: Bearer <token>` (file downloads also accept `?token=<token>`). Sessions last 7 days.

## Authentication
| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | /api/auth/status | Public | `{has_users}` – whether the first (admin) sign-up has happened |
| POST | /api/auth/signup | Public | `{name,email,password}` – first user becomes Admin; later only admin-added emails can sign up |
| POST | /api/auth/login | Public | `{email,password}` → `{token,user}`. 5 failed attempts lock the email for 5 minutes |
| POST | /api/auth/logout | User | Ends the session |
| GET | /api/me | User | Current user, unread notifications, travel entitlement |
| POST | /api/me/password | User | `{current,password}` change password |
| GET | /api/meta | User | Settings, roles, stages, Matrix of Authority, Business Heads list |

## Employees (Admin only)
| Method | Path | Purpose |
|---|---|---|
| GET | /api/employees | List employees with sign-up status, trips and spend |
| POST | /api/employees | Add employee `{name,email,role,department,grade,phone,base_city,business_head_id,is_admin,is_active}` |
| PUT | /api/employees/:id | Edit employee / deactivate / grant admin |
| POST | /api/employees/:id/reset-password | `{password}` set a temporary password |
| POST | /api/employees/import | `{csv}` bulk import (see Sample_Employee_Import.csv) |

## Travel requests & workflow
| Method | Path | Purpose |
|---|---|---|
| GET | /api/requests?scope=mine\|approvals\|processed\|advances\|all | Lists (`all` = Admin; `advances` = Accountant) |
| POST | /api/requests | Create; `submit:true` sends it for approval |
| GET | /api/requests/:id | Full detail: items, attachments, history, exceptions, permitted actions |
| PUT | /api/requests/:id | Employee edit while Draft / Sent back / Pending BH (before any action) |
| POST | /api/requests/:id/action | Workflow action (below) |
| POST | /api/requests/:id/items | Add expense line `{exp_date,category,description,vendor,bill_no,currency,fx_rate,amount}` |
| PUT / DELETE | /api/items/:id | Edit / delete an expense line (before claim submission) |
| POST | /api/requests/:id/attachments | `{name,mime,data(base64),kind,item_id}` – PDF/JPG/PNG/WEBP/HEIC, max 5 MB |
| GET / DELETE | /api/attachments/:id | View / remove a document |

### Workflow actions (`POST /api/requests/:id/action`)
| action | Who | Stage | Body |
|---|---|---|---|
| APPROVE | Business Head, MD | PENDING_BH, PENDING_MD | `approved_amount` (optional revision), `comment` |
| APPROVE | Business Head, HR Head | CLAIM_PENDING_BH, CLAIM_PENDING_HR | `items:[{id,approved_inr,note}]`, `comment` |
| SEND_BACK / REJECT | Current approver | any approval stage | `comment` (mandatory) |
| BOOK | Travel Assistant | PENDING_BOOKING | `booking:{airline,flight_no,return_flight_no,pnr,flight_class,ticket_cost,onward_time,hotel_name,hotel_category,hotel_nights,hotel_rate,booking_ref}`, `comment` (mandatory if above entitlement) |
| PAY_ADVANCE | Accountant | PENDING_BOOKING, BOOKED | `amount`, `reference` |
| SUBMIT_CLAIM | Employee | BOOKED, CLAIM_SENT_BACK | `comment` (mandatory if a bill above the limit is missing) |
| PROCESS_PAYMENT | Accountant | CLAIM_PENDING_ACCOUNTS | `payment:{voucher_no,gl_code,cost_center,payment_mode,payment_ref,payment_date,accounting_notes}` |
| CANCEL | Employee | before booking | – |

Admin can perform any stage action (recorded as *Admin override*). Nobody can approve their own request.

## Admin analytics & settings
| Method | Path | Purpose |
|---|---|---|
| GET | /api/analytics?from=&to= | KPIs, employee / destination / airline / department / month / category / stage breakdowns, lead-time vs fare, exception list |
| GET | /api/export/requests.csv | Full register as CSV (Excel-ready) |
| GET | /api/backup | Download a consistent copy of the SQLite database |
| GET | /api/auth-logs | Last 500 sign-in / sign-up / security events |
| GET / PUT | /api/settings | Policy rules, roles, departments, categories, airlines, currencies, feature switches |
| PUT | /api/matrix | `{rows:[{role,flight_class,hotel_category,hotel_max_per_night,da_per_day,local_per_day}]}` |

## Other
`GET /api/dashboard` (personal KPIs) · `GET /api/notifications` · `POST /api/notifications/read` ·
`GET/POST /api/features` · `POST /api/features/:id/vote` · `PUT /api/features/:id` (Admin status) · `GET /api/health`

## Workflow stages
DRAFT → PENDING_BH → PENDING_MD → PENDING_BOOKING → BOOKED → CLAIM_PENDING_BH → CLAIM_PENDING_HR →
CLAIM_PENDING_ACCOUNTS → PAID. Side states: SENT_BACK, CLAIM_SENT_BACK, REJECTED, CANCELLED.
A Business Head's own request skips PENDING_BH (and CLAIM_PENDING_BH); an MD's own request goes straight to booking.

## Exception flags (computed automatically)
LATE_BOOKING, HOTEL_ABOVE_GRADE, HOTEL_RATE, FLIGHT_ABOVE_GRADE, LONG_TRIP, OVER_BUDGET, MISSING_BILLS,
FOOD_OVER_DA, DUPLICATE_BILL, DATE_OUTSIDE_TRIP, LATE_CLAIM, CLAIM_OVERDUE.
