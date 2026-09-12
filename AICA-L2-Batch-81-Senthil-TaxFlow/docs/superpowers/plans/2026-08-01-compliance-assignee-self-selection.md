# Compliance Assignee Self-Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any compliance schedule creator/editor assign themselves as preparer, pick approvers via a single-select dropdown, and let admins add themselves as both preparer and approver.

**Architecture:** Client-side changes in the create/edit pages build the preparer/approver option lists so the current user is always included (merged + deduped against the role-filtered org-member lists). The Preparer field becomes a dropdown for all roles (defaulting to self); the Approvers field becomes a single-select dropdown. The POST API is relaxed by one line so a non-admin's chosen `preparerId` is respected.

**Tech Stack:** Next.js 16 (App Router, `"use client"` pages), React 19, shadcn/ui (`Select`, `Checkbox`), Tailwind v4, Supabase (via `supabaseAdmin`), deployed to Cloudflare Workers via OpenNext.

## Global Constraints

- **Next.js is NOT the standard version.** Read the relevant guide in `node_modules/next/dist/docs/` before writing any code; heed deprecation notices. The patterns used here (App Router route handlers, `"use client"` pages, shadcn `Select`) already exist in the codebase — mirror them exactly.
- **No test framework is configured** in `package.json` (no test script, no vitest/jest). Do NOT add one. Verification is via `npx tsc --noEmit` and scoped `npx eslint`.
- **The working tree is dirty** with unrelated in-progress work. Each task's commit must stage ONLY the files listed in that task. Never `git add -A` or `git add .`.
- **The edit page has one pre-existing lint error** (`react-hooks/set-state-in-effect` at `src/app/compliance/[id]/edit/page.tsx:176`). It is fixed in Task 3 by removing the redundant `setLoading(true)`. Do not introduce any new lint errors.
- **Do not change the shared `/api/users` route** or the DB schema. `ensureOrgMember` in the compliance API already adds assigned preparers/approvers (including admins) to the active org.
- **Do not use `useEffect` to set state synchronously** (triggers `react-hooks/set-state-in-effect`). Use derived values or async callbacks instead.

---

### Task 1: Respect the submitted `preparerId` in POST /api/compliance

**Files:**
- Modify: `src/app/api/compliance/route.ts` (POST handler, lines ~153-200)

**Interfaces:**
- Consumes: `getActiveContextFromRequest(request)` returns `{ orgId }` (the `activeRole` field becomes unused here).
- Produces: `POST /api/compliance` accepts an optional `preparerId` string for ALL roles; if absent it defaults to the creator's id.

- [ ] **Step 1: Remove the now-unused `isAdmin`/`activeRole`**

In the POST handler, change:

```ts
    const { orgId, activeRole } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const isAdmin = activeRole === "ADMINISTRATOR"
```

to:

```ts
    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }
```

- [ ] **Step 2: Let any creator choose the preparer**

Change:

```ts
    // Non-admin creators are automatically tagged as the preparer.
    // Admins can tag any preparer (defaults to themselves if not provided).
    const preparerId = isAdmin ? (bodyPreparerId || session.user.id) : session.user.id
```

to:

```ts
    // The creator can tag any preparer (defaults to themselves if not provided).
    const preparerId = bodyPreparerId || session.user.id
```

- [ ] **Step 3: Verify typecheck + lint**

Run: `npx tsc --noEmit`
Expected: no errors.

Run: `npx eslint src/app/api/compliance/route.ts`
Expected: no problems.

- [ ] **Step 4: Commit**

```bash
git add src/app/api/compliance/route.ts
git commit -m "fix(api): respect submitted preparerId for all compliance creators"
```

---

### Task 2: Create page — dropdowns with current-user inclusion

**Files:**
- Modify: `src/app/compliance/create/page.tsx`

**Interfaces:**
- Consumes: `useAuth()` → `{ user: sessionUser }`; existing fetches to `/api/entities`, `/api/users?role=PREPARER`, `/api/users?role=APPROVER`.
- Produces: `POST /api/compliance` payload now always includes `preparerId` (string) and `approverIds` (array of 0 or 1 strings).

- [ ] **Step 1: Update the auth destructure and remove `isAdmin`**

Change:

```tsx
  const { user: sessionUser, activeRole } = useAuth()
  const isAdmin = activeRole === "ADMINISTRATOR"
```

to:

```tsx
  const { user: sessionUser } = useAuth()
```

- [ ] **Step 2: Replace approver state with a single id**

Change:

```tsx
  const [approverIds, setApproverIds] = useState<string[]>([])
```

to:

```tsx
  const [approverId, setApproverId] = useState("")
```

- [ ] **Step 3: Remove `toggleApprover`**

Delete:

```tsx
  function toggleApprover(id: string) {
    setApproverIds((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    )
  }
```

- [ ] **Step 4: Build option lists that always include the current user**

Add the `User` type field union and `useMemo` options right after the existing state declarations (after `const [approvers, setApprovers] = useState<User[]>([])`):

```tsx
  const preparerOptions = useMemo(() => {
    const map = new Map<string, User>()
    preparers.forEach((p) => map.set(p.id, { id: p.id, name: p.name, email: p.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [preparers, sessionUser])

  const approverOptions = useMemo(() => {
    const map = new Map<string, User>()
    approvers.forEach((a) => map.set(a.id, { id: a.id, name: a.name, email: a.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [approvers, sessionUser])

  // Default the preparer to the current user without a state-sync effect.
  const effectivePreparerId = preparerId || sessionUser?.id || ""
```

- [ ] **Step 5: Replace the conditional preparer field with an always-on dropdown**

Replace the entire `{isAdmin ? ( ... ) : ( ... )}` block for the Preparer field with:

```tsx
                <div className="space-y-2">
                  <Label htmlFor="preparer">
                    Preparer <span className="text-red-500">*</span>
                  </Label>
                  <Select value={effectivePreparerId} onValueChange={setPreparerId} required>
                    <SelectTrigger id="preparer">
                      <SelectValue placeholder="Select preparer" />
                    </SelectTrigger>
                    <SelectContent>
                      {preparerOptions.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name} ({p.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
```

- [ ] **Step 6: Replace the approvers checkbox grid with a single-select dropdown**

Replace the entire Approvers block (the `{approvers.length === 0 ? ... : (checkbox grid)}` section) with:

```tsx
              <div className="space-y-2">
                <Label htmlFor="approver">Approver</Label>
                <Select value={approverId} onValueChange={setApproverId}>
                  <SelectTrigger id="approver">
                    <SelectValue placeholder="Select approver" />
                  </SelectTrigger>
                  <SelectContent>
                    {approverOptions.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.name} ({a.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {approverOptions.length === 0 && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">No approvers available</p>
                )}
              </div>
```

- [ ] **Step 7: Update validation**

Change:

```tsx
    if (isAdmin && !preparerId) {
```

to:

```tsx
    if (!effectivePreparerId) {
```

- [ ] **Step 8: Update the submit payload**

Change:

```tsx
        preparerId: isAdmin ? preparerId : undefined,
        approverIds,
```

to:

```tsx
        preparerId: effectivePreparerId || undefined,
        approverIds: approverId ? [approverId] : [],
```

- [ ] **Step 9: Verify typecheck + lint**

Run: `npx tsc --noEmit`
Expected: no errors.

Run: `npx eslint src/app/compliance/create/page.tsx`
Expected: no problems.

- [ ] **Step 10: Commit**

```bash
git add src/app/compliance/create/page.tsx
git commit -m "feat(compliance): preparer self-selection and single-select approver on create"
```

---

### Task 3: Edit page — same dropdowns + current-user inclusion

**Files:**
- Modify: `src/app/compliance/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `useAuth()` → `{ user: sessionUser }` (newly imported); existing fetches to `/api/countries`, `/api/entities`, `/api/users?role=PREPARER`, `/api/users?role=APPROVER`, and `GET /api/compliance/:id` (returns `assignments[0].preparerId`, `approvals[].approverId`).
- Produces: `PUT /api/compliance/:id` payload now includes `preparerId` (string) and `approverIds` (array of 0 or 1 strings).

- [ ] **Step 1: Import and use `useAuth`**

Add to the imports:

```tsx
import { useAuth } from "@/components/layout/providers"
```

In the component body, after `const params = useParams()` / `const id = ...`, add:

```tsx
  const { user: sessionUser } = useAuth()
```

- [ ] **Step 2: Replace approver state with a single id**

Change:

```tsx
  const [approverIds, setApproverIds] = useState<string[]>([])
```

to:

```tsx
  const [approverId, setApproverId] = useState("")
```

- [ ] **Step 3: Remove the redundant `setLoading(true)` (fixes pre-existing lint error)**

In the load effect, delete the line `setLoading(true)` (currently at line 176). The component initializes `loading` to `true`, so behavior is unchanged.

- [ ] **Step 4: Prefill from existing assignment / first approval**

In the `.then((result) => {...})` callback of the load effect, change:

```tsx
        setPreparerId(d.assignments?.[0]?.preparerId || "")
        setApproverIds((d.approvals || []).map((a) => a.approverId))
```

to:

```tsx
        setPreparerId(d.assignments?.[0]?.preparerId || "")
        setApproverId(d.approvals?.[0]?.approverId || "")
```

- [ ] **Step 5: Remove `toggleApprover`**

Delete:

```tsx
  function toggleApprover(approverId: string) {
    setApproverIds((prev) =>
      prev.includes(approverId) ? prev.filter((a) => a !== approverId) : [...prev, approverId]
    )
  }
```

- [ ] **Step 6: Build option lists that always include the current user**

Add the same `useMemo` blocks and derived default as in Task 2, placed after the fetch `useEffect` (after line ~172). Use this exact code (note `sessionUser`):

```tsx
  const preparerOptions = useMemo(() => {
    const map = new Map<string, User>()
    preparers.forEach((p) => map.set(p.id, { id: p.id, name: p.name, email: p.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [preparers, sessionUser])

  const approverOptions = useMemo(() => {
    const map = new Map<string, User>()
    approvers.forEach((a) => map.set(a.id, { id: a.id, name: a.name, email: a.email }))
    if (sessionUser?.id) {
      map.set(sessionUser.id, {
        id: sessionUser.id,
        name: sessionUser.name || sessionUser.username || sessionUser.email,
        email: sessionUser.email,
      })
    }
    return Array.from(map.values()).sort((a, b) => (a.name || "").localeCompare(b.name || ""))
  }, [approvers, sessionUser])

  const effectivePreparerId = preparerId || sessionUser?.id || ""
```

- [ ] **Step 7: Point the preparer dropdown at the merged options**

In the Preparer `SelectContent`, change `{preparers.map((p) => (` to `{preparerOptions.map((p) => (` and change the `Select` value to `value={effectivePreparerId}`.

- [ ] **Step 8: Replace the approvers checkbox grid with a single-select dropdown**

Replace the entire Approvers block with:

```tsx
              <div className="space-y-2">
                <Label htmlFor="approver">Approver</Label>
                <Select value={approverId} onValueChange={setApproverId}>
                  <SelectTrigger id="approver">
                    <SelectValue placeholder="Select approver" />
                  </SelectTrigger>
                  <SelectContent>
                    {approverOptions.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.name} ({a.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {approverOptions.length === 0 && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">No approvers available</p>
                )}
              </div>
```

- [ ] **Step 9: Update validation and submit payload**

In `handleSubmit`, change:

```tsx
    if (entityIds.length === 0 || !countryId || !taxType || !taxPeriodStart || !taxPeriodEnd || !dueDate || !preparerId) {
```

to:

```tsx
    if (entityIds.length === 0 || !countryId || !taxType || !taxPeriodStart || !taxPeriodEnd || !dueDate || !effectivePreparerId) {
```

and change:

```tsx
        preparerId,
        approverIds,
```

to:

```tsx
        preparerId: effectivePreparerId,
        approverIds: approverId ? [approverId] : [],
```

- [ ] **Step 10: Verify typecheck + lint**

Run: `npx tsc --noEmit`
Expected: no errors.

Run: `npx eslint src/app/compliance/[id]/edit/page.tsx`
Expected: no problems (the pre-existing `set-state-in-effect` error should be gone).

- [ ] **Step 11: Commit**

```bash
git add "src/app/compliance/[id]/edit/page.tsx"
git commit -m "feat(compliance): preparer self-selection and single-select approver on edit"
```

---

### Task 4: End-to-end manual verification

**Files:** none (verification only).

- [ ] **Step 1: Run the dev server**

Run: `npm run dev`
Open `http://localhost:3000` in a browser and log in as a **PREPARER**-role user.

- [ ] **Step 2: Verify preparer self-selection on create**

Navigate to Compliance → **Add New Compliance Template**. Fill required fields. Confirm:
- The Preparer field is a dropdown (not read-only) and is pre-selected to the logged-in user.
- The logged-in user's name appears in the dropdown.
- Saving creates the schedule with the logged-in user as preparer (check the Compliance Tracker list's Preparer column).

- [ ] **Step 3: Verify approver single-select dropdown**

On the same form, confirm the Approver field is a single-select dropdown (not a checkbox grid) containing `APPROVER`-role members. Select one and save; the schedule's detail page shows that single approver.

- [ ] **Step 4: Verify admin self-assignment**

Log out, log in as an **ADMINISTRATOR**. On create, confirm the admin can:
- Select themselves in the Preparer dropdown.
- Select themselves in the Approver dropdown (the admin's name must appear even though their role is `ADMINISTRATOR`).
Save and confirm both are set on the schedule.

- [ ] **Step 5: Verify edit page parity**

Open the created schedule's **Edit** page. Confirm the Preparer dropdown is pre-filled from the existing assignment and the Approver dropdown from the existing approval, and that the admin's name is still available in both dropdowns.

- [ ] **Step 6: Report results**

Summarize which checks passed/failed. If any fail, report the exact repro before considering the plan complete.
