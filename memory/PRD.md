# Cosmetic Inventory Management System - PRD

## Project Overview
Stage-wise inventory management software for cosmetic manufacturing unit (shampoo, facewash, serum, moisturizer).

## Date
- **Created**: January 27, 2026
- **Last Updated**: January 27, 2026

## User Personas
1. **Admin** - Full system access, user management, all CRUD operations
2. **Production Manager** - Products, chemist reports, production batches, packaging
3. **Store Keeper** - Suppliers, materials, purchase orders, dispatch, material issuance
4. **Viewer** - Read-only access to all data

## Core Requirements (Static)
### Manufacturing Stages Flow
1. Raw Material Purchase
2. Store Inventory  
3. Material Issued (as per chemist report for production)
4. After Processing (WIP)
5. Packaging
6. Dispatch

### Raw Material Types
- Chemicals
- Packing Materials

### Features Required
- Stock in/out tracking
- Stage tracking
- Low stock alerts
- Batch tracking with expiry dates
- Supplier management
- Production planning
- Detailed reports (stage-wise analysis, consumption patterns)

### Product Categories
- Shampoo
- Facewash
- Serum
- Moisturizer

## What's Been Implemented (MVP - v1.0)

### Backend (FastAPI + MongoDB)
- [x] JWT Authentication with role-based access control
- [x] User management (CRUD with first user auto-admin)
- [x] Suppliers CRUD (chemicals/packing material type)
- [x] Raw Materials CRUD with stock tracking
- [x] Batch management with expiry dates
- [x] Purchase Orders (create, approve, receive with auto stock update)
- [x] Products/Formula management
- [x] Chemist Reports (create, approve, issue materials)
- [x] Production Batches with stage tracking
- [x] Packaging Records
- [x] Dispatch Records
- [x] Stock Movements tracking
- [x] Dashboard statistics API
- [x] Reports APIs (consumption, stage-wise, inventory summary)

### Frontend (React + Tailwind)
- [x] Login/Registration with auto-redirect
- [x] Dashboard with stage cards, alerts, manufacturing flow visualization
- [x] Suppliers management page
- [x] Raw Materials page with stock status indicators
- [x] Products catalog page
- [x] Purchase Orders with approval workflow
- [x] Store Inventory (stock levels, batches, movements tabs)
- [x] Chemist Reports with material issuance
- [x] Production page with stage progression
- [x] Packaging management
- [x] Dispatch management
- [x] Reports page with charts (recharts)
- [x] User Management (admin only)
- [x] Role-based UI (hide/show features)
- [x] Dark sidebar, clean "Clinical Industrial" design

### Design
- "Clinical Industrial" theme - precision-first aesthetic
- Chivo (headings), Inter (body), JetBrains Mono (data)
- Stage-based color coding (Violet=Raw, Cyan=Store, Blue=Production, Amber=Packaging, Rose=Dispatch)
- Sharp edges (rounded-sm), high-density data tables

## Test Results
- Backend: 97.6% success rate (41/42 tests passed)
- Frontend: 90% success rate
- Integration: 95% success rate

## Prioritized Backlog

### P0 (Critical) - Completed in MVP
- ✅ Basic auth and roles
- ✅ Complete manufacturing flow from PO to Dispatch
- ✅ Stock tracking and alerts

### P1 (High Priority) - Future
- [ ] Barcode/QR code generation for batches
- [ ] Export reports to PDF/Excel
- [ ] Email notifications for low stock
- [ ] Advanced search and filtering
- [ ] Batch-wise traceability report

### P2 (Medium Priority) - Future
- [ ] Mobile responsive optimization
- [ ] Wastage tracking module
- [ ] Quality check integration
- [ ] Supplier performance analytics
- [ ] Production planning/scheduling

### P3 (Nice to Have) - Future
- [ ] Multi-warehouse support
- [ ] Formula versioning
- [ ] Integration with accounting software
- [ ] Machine/equipment tracking
- [ ] Predictive stock reordering

## Architecture

### Tech Stack
- **Frontend**: React 19, Tailwind CSS, Recharts, Sonner (toasts)
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Auth**: JWT with bcrypt

### API Routes
- `/api/auth/*` - Authentication
- `/api/users` - User management
- `/api/suppliers` - Supplier CRUD
- `/api/materials` - Raw materials CRUD
- `/api/batches` - Batch management
- `/api/purchase-orders` - PO workflow
- `/api/products` - Product catalog
- `/api/chemist-reports` - Material issue requests
- `/api/production-batches` - Production tracking
- `/api/packaging-records` - Packaging management
- `/api/dispatch-records` - Dispatch tracking
- `/api/stock-movements` - Stock movement history
- `/api/dashboard/stats` - Dashboard metrics
- `/api/reports/*` - Analytics endpoints

## Next Tasks
1. Add barcode/QR generation for batch labels
2. Implement PDF report export
3. Add email notifications for low stock alerts
4. Mobile responsiveness improvements
