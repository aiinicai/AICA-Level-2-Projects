import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { NextResponse } from "next/server"

interface AssignmentRow {
  complianceId: string
}

interface ScheduleIdRow {
  id: string
}

interface ActivityRow {
  id: string
  complianceId: string
  user: { id: string; name: string } | null
}

interface ScheduleRow {
  id: string
  complianceId: string
  dueDate: string
  priority: string
  status: string
  entity: { entityName: string } | null
  countryId?: string | null
  entityId?: string | null
  country?: { name: string; code: string } | null
  source?: string | null
}

interface ApprovalRow {
  actionAt: string
  compliance: { submittedAt: string } | null
}

interface ApprovalItemRow {
  complianceId: string
  compliance: { countryId: string; entityId: string } | null
}

interface CountRow {
  count: number | null
}

interface UserRow {
  id: string
  name: string | null
  email: string | null
  role: string | null
}

interface OrgMemberRow {
  userId: string
  roles: string[]
}

interface StatusRow {
  status: string
}

interface IdRow {
  countryId?: string | null
  entityId?: string | null
  complianceTypeId?: string | null
}

interface NameRow {
  id: string
  name: string
  code?: string
  entityName?: string
  entityNumber?: string
  taxType?: string
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function endOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
}

async function getPreparerComplianceIds(userId: string, orgId: string): Promise<string[]> {
  const { data } = await supabaseAdmin
    .from("compliance_assignments")
    .select("complianceId")
    .eq("preparerId", userId)

  const ids = data?.map((a: AssignmentRow) => a.complianceId) || []
  if (ids.length === 0) return []

  const { data: schedules } = await supabaseAdmin
    .from("compliance_schedules")
    .select("id")
    .in("id", ids)
    .eq("orgId", orgId)

  return schedules?.map((s: ScheduleIdRow) => s.id) || []
}

async function getApproverComplianceIds(userId: string, orgId: string): Promise<string[]> {
  const { data } = await supabaseAdmin
    .from("compliance_approvals")
    .select("complianceId")
    .eq("approverId", userId)

  const ids = data?.map((a: AssignmentRow) => a.complianceId) || []
  if (ids.length === 0) return []

  const { data: schedules } = await supabaseAdmin
    .from("compliance_schedules")
    .select("id")
    .in("id", ids)
    .eq("orgId", orgId)

  return schedules?.map((s: ScheduleIdRow) => s.id) || []
}

async function getReviewerComplianceIds(userId: string, orgId: string): Promise<string[]> {
  const [{ data: approvals }, { data: schedulesWithReviewer }] = await Promise.all([
    supabaseAdmin.from("compliance_approvals").select("complianceId").eq("approverId", userId),
    supabaseAdmin.from("compliance_schedules").select("id").eq("orgId", orgId).eq("reviewerId", userId),
  ])
  const ids = Array.from(new Set([
    ...(approvals?.map((a: AssignmentRow) => a.complianceId) || []),
    ...(schedulesWithReviewer?.map((s: ScheduleIdRow) => s.id) || []),
  ]))
  if (ids.length === 0) return []

  const { data: schedules } = await supabaseAdmin
    .from("compliance_schedules")
    .select("id")
    .in("id", ids)
    .eq("orgId", orgId)

  return schedules?.map((s: ScheduleIdRow) => s.id) || []
}

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const url = new URL(request.url)
    const roleQuery = url.searchParams.get("role")
    const orgIdQuery = url.searchParams.get("orgId")

    const { orgId: cookieOrgId, activeRole: cookieRole } = getActiveContextFromRequest(request)
    const orgId = orgIdQuery || cookieOrgId
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const user = session.user
    const userId = user.id
    const role = roleQuery || cookieRole || user.role

    const now = new Date()
    const todayStart = startOfDay(now)
    const todayEnd = endOfDay(now)
    const weekEnd = new Date(todayStart.getTime() + 7 * 86400000)

    if (role === "PREPARER") {
      const prepIds = await getPreparerComplianceIds(userId, orgId)

      const countQuery = async (statusIn?: string[], statusNotIn?: string[], dateField?: string, dateGte?: Date, dateLt?: Date) => {
        let q = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
        if (prepIds.length > 0) q = q.in("id", prepIds)
        else q = q.in("id", [])
        if (statusIn) q = q.in("status", statusIn)
        if (statusNotIn) q = q.not("status", "in", `("${statusNotIn.join('","')}")`)
        if (dateField && dateGte) q = q.gte(dateField, dateGte.toISOString())
        if (dateField && dateLt) q = q.lt(dateField, dateLt.toISOString())
        const { count } = await q
        return count || 0
      }

      const [
        assignedCompliances,
        completed,
        pending,
        overdue,
        dueToday,
        dueThisWeek,
      ] = await Promise.all([
        supabaseAdmin.from("compliance_assignments").select("*", { count: "exact", head: true }).eq("preparerId", userId).then((r: CountRow) => r.count || 0),
        countQuery(["FILED", "APPROVED"]),
        countQuery(undefined, ["FILED", "APPROVED", "CLOSED"]),
        (async () => {
          let q = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
          if (prepIds.length > 0) q = q.in("id", prepIds)
          else q = q.in("id", [])
          q = q.lt("dueDate", now.toISOString())
          q = q.is("filedAt", null)
          const { count } = await q
          return count || 0
        })(),
        countQuery(undefined, undefined, "dueDate", todayStart, todayEnd),
        countQuery(undefined, undefined, "dueDate", todayStart, weekEnd),
      ])

      const [recentActivities, upcomingDueItems] = await Promise.all([
        (async () => {
          let q = supabaseAdmin.from("activities").select("*, user:users(id, name), compliance:compliance_schedules!inner(id, complianceId)")
          if (prepIds.length > 0) q = q.in("complianceId", prepIds)
          else q = q.in("complianceId", [])
          const { data } = await q.order("createdAt", { ascending: false }).limit(10)
          return data || []
        })(),
        (async () => {
          let q = supabaseAdmin.from("compliance_schedules").select("id, complianceId, dueDate, priority, status, entity:legal_entities(entityName)")
          if (prepIds.length > 0) q = q.in("id", prepIds)
          else q = q.in("id", [])
          q = q.not("status", "in", `("FILED","CLOSED")`)
          q = q.gte("dueDate", now.toISOString())
          const { data } = await q.order("dueDate", { ascending: true }).limit(5)
          return data || []
        })(),
      ])

      const months: { month: string; completed: number; pending: number }[] = []
      for (let i = 5; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
        const monthStart = new Date(d.getFullYear(), d.getMonth(), 1)
        const monthEnd = new Date(d.getFullYear(), d.getMonth() + 1, 1)
        const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`

        const monthCompleted = await countQuery(["FILED", "APPROVED"], undefined, "updatedAt", monthStart, monthEnd)

        let q = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
        if (prepIds.length > 0) q = q.in("id", prepIds)
        else q = q.in("id", [])
        q = q.not("status", "in", `("FILED","APPROVED","CLOSED")`)
        q = q.lt("createdAt", monthEnd.toISOString())
        const { count: monthPending } = await q

        months.push({ month: monthKey, completed: monthCompleted, pending: monthPending || 0 })
      }

      let totalPendingQ = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
      if (prepIds.length > 0) totalPendingQ = totalPendingQ.in("id", prepIds)
      else totalPendingQ = totalPendingQ.in("id", [])
      totalPendingQ = totalPendingQ.not("status", "in", `("FILED","APPROVED","CLOSED")`)
      const { count: totalPending } = await totalPendingQ

      return NextResponse.json({
        data: {
          role: "PREPARER",
          assignedCompliances,
          completed,
          pending,
          overdue,
          dueToday,
          dueThisWeek,
          monthlyProgress: months,
          pendingVsCompleted: { pending: totalPending || 0, completed },
          upcomingDueDates: upcomingDueItems,
          recentActivity: recentActivities,
        },
      })
    }

    if (role === "APPROVER") {
      const apprIds = await getApproverComplianceIds(userId, orgId)

      const [pendingApproval, rejected, approvedToday, recentActivities, approvalRecords] = await Promise.all([
        supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "PENDING_APPROVAL").then((r) => r.count || 0),
        (async () => {
          let q = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
          if (apprIds.length > 0) q = q.in("id", apprIds)
          else q = q.in("id", [])
          q = q.eq("status", "REJECTED")
          const { count } = await q
          return count || 0
        })(),
        supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "APPROVED").gte("actionAt", todayStart.toISOString()).lt("actionAt", todayEnd.toISOString()).then((r) => r.count || 0),
        (async () => {
          let q = supabaseAdmin.from("activities").select("*, user:users(id, name), compliance:compliance_schedules!inner(id, complianceId)")
          if (apprIds.length > 0) q = q.in("complianceId", apprIds)
          else q = q.in("complianceId", [])
          const { data } = await q.order("createdAt", { ascending: false }).limit(10)
          return (data || []) as unknown as ActivityRow[]
        })(),
        supabaseAdmin.from("compliance_approvals").select("actionAt, compliance:compliance_schedules!inner(submittedAt)").eq("approverId", userId).eq("status", "APPROVED").not("actionAt", "is", "null").then((r) => (r.data || []) as unknown as ApprovalRow[]),
      ])

      let avgApprovalTime = 0
      if (approvalRecords.length > 0) {
        const totalHours = approvalRecords.reduce((sum: number, item: ApprovalRow) => {
          const diff = new Date(item.actionAt).getTime() - new Date(item.compliance?.submittedAt || 0).getTime()
          return sum + diff / 3600000
        }, 0)
        avgApprovalTime = Math.round((totalHours / approvalRecords.length) * 10) / 10
      }

      const approvalTrend: { date: string; count: number }[] = []
      for (let i = 29; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
        const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate())
        const dayEnd = new Date(dayStart.getTime() + 86400000)
        const dateKey = d.toISOString().split("T")[0]
        const { count } = await supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "APPROVED").gte("actionAt", dayStart.toISOString()).lt("actionAt", dayEnd.toISOString())
        approvalTrend.push({ date: dateKey, count: count || 0 })
      }

      const { data: allPendingApprovals } = await supabaseAdmin
        .from("compliance_approvals")
        .select("complianceId, compliance:compliance_schedules!inner(countryId, entityId)")
        .eq("approverId", userId)
        .eq("status", "PENDING_APPROVAL")

      const countryCount: Record<string, number> = {}
      const entityCount: Record<string, number> = {}
      ;(allPendingApprovals as unknown as ApprovalItemRow[] | undefined)?.forEach((item) => {
        const cId = item.compliance?.countryId
        const eId = item.compliance?.entityId
        if (cId) countryCount[cId] = (countryCount[cId] || 0) + 1
        if (eId) entityCount[eId] = (entityCount[eId] || 0) + 1
      })

      const pendingByCountryIds = Object.keys(countryCount)
      const pendingByEntityIds = Object.keys(entityCount)

      const { data: countries } = pendingByCountryIds.length > 0
        ? await supabaseAdmin.from("countries").select("id, name, code").in("id", pendingByCountryIds)
        : { data: [] }
      const { data: entities } = pendingByEntityIds.length > 0
        ? await supabaseAdmin.from("legal_entities").select("id, entityName, entityNumber").in("id", pendingByEntityIds)
        : { data: [] }

      const countryMap = new Map<string, NameRow>(((countries || []) as unknown as NameRow[]).map((c) => [c.id, c] as const))
      const entityMap = new Map<string, NameRow>(((entities || []) as unknown as NameRow[]).map((e) => [e.id, e] as const))

      const enrichedPendingByCountry = pendingByCountryIds.map((id) => ({
        country: countryMap.get(id) || null,
        count: countryCount[id],
      }))

      const enrichedPendingByEntity = pendingByEntityIds.map((id) => ({
        entity: entityMap.get(id) || null,
        count: entityCount[id],
      }))

      return NextResponse.json({
        data: {
          role: "APPROVER",
          pendingApproval,
          rejected,
          approvedToday,
          avgApprovalTime,
          approvalTrend,
          pendingByCountry: enrichedPendingByCountry,
          pendingByEntity: enrichedPendingByEntity,
          recentActivities,
        },
      })
    }

    if (role === "REVIEWER") {
      const revIds = await getReviewerComplianceIds(userId, orgId)

      const [pendingApproval, rejected, approvedToday, recentActivities, approvalRecords] = await Promise.all([
        (async () => {
          const [{ count: appCount }, { count: schedCount }] = await Promise.all([
            supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "PENDING_APPROVAL"),
            supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).eq("reviewerId", userId).eq("status", "PENDING_REVIEW"),
          ])
          return (appCount || 0) + (schedCount || 0)
        })(),
        (async () => {
          let q = supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true })
          if (revIds.length > 0) q = q.in("id", revIds)
          else q = q.in("id", [])
          q = q.eq("status", "REJECTED")
          const { count } = await q
          return count || 0
        })(),
        supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "APPROVED").gte("actionAt", todayStart.toISOString()).lt("actionAt", todayEnd.toISOString()).then((r) => r.count || 0),
        (async () => {
          let q = supabaseAdmin.from("activities").select("*, user:users(id, name), compliance:compliance_schedules!inner(id, complianceId)")
          if (revIds.length > 0) q = q.in("complianceId", revIds)
          else q = q.in("complianceId", [])
          const { data } = await q.order("createdAt", { ascending: false }).limit(10)
          return (data || []) as unknown as ActivityRow[]
        })(),
        supabaseAdmin.from("compliance_approvals").select("actionAt, compliance:compliance_schedules!inner(submittedAt)").eq("approverId", userId).eq("status", "APPROVED").not("actionAt", "is", "null").then((r) => (r.data || []) as unknown as ApprovalRow[]),
      ])

      let avgApprovalTime = 0
      if (approvalRecords.length > 0) {
        const totalHours = approvalRecords.reduce((sum: number, item: ApprovalRow) => {
          const diff = new Date(item.actionAt).getTime() - new Date(item.compliance?.submittedAt || 0).getTime()
          return sum + diff / 3600000
        }, 0)
        avgApprovalTime = Math.round((totalHours / approvalRecords.length) * 10) / 10
      }

      const approvalTrend: { date: string; count: number }[] = []
      for (let i = 29; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
        const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate())
        const dayEnd = new Date(dayStart.getTime() + 86400000)
        const dateKey = d.toISOString().split("T")[0]
        const { count } = await supabaseAdmin.from("compliance_approvals").select("*", { count: "exact", head: true }).eq("approverId", userId).eq("status", "APPROVED").gte("actionAt", dayStart.toISOString()).lt("actionAt", dayEnd.toISOString())
        approvalTrend.push({ date: dateKey, count: count || 0 })
      }

      const { data: allPendingApprovals } = await supabaseAdmin
        .from("compliance_approvals")
        .select("complianceId, compliance:compliance_schedules!inner(countryId, entityId)")
        .eq("approverId", userId)
        .eq("status", "PENDING_APPROVAL")

      const countryCount: Record<string, number> = {}
      const entityCount: Record<string, number> = {}
      ;(allPendingApprovals as unknown as ApprovalItemRow[] | undefined)?.forEach((item) => {
        const cId = item.compliance?.countryId
        const eId = item.compliance?.entityId
        if (cId) countryCount[cId] = (countryCount[cId] || 0) + 1
        if (eId) entityCount[eId] = (entityCount[eId] || 0) + 1
      })

      const pendingByCountryIds = Object.keys(countryCount)
      const pendingByEntityIds = Object.keys(entityCount)

      const { data: countries } = pendingByCountryIds.length > 0
        ? await supabaseAdmin.from("countries").select("id, name, code").in("id", pendingByCountryIds)
        : { data: [] }
      const { data: entities } = pendingByEntityIds.length > 0
        ? await supabaseAdmin.from("legal_entities").select("id, entityName, entityNumber").in("id", pendingByEntityIds)
        : { data: [] }

      const countryMap = new Map<string, NameRow>(((countries || []) as unknown as NameRow[]).map((c) => [c.id, c] as const))
      const entityMap = new Map<string, NameRow>(((entities || []) as unknown as NameRow[]).map((e) => [e.id, e] as const))

      const enrichedPendingByCountry = pendingByCountryIds.map((id) => ({
        country: countryMap.get(id) || null,
        count: countryCount[id],
      }))

      const enrichedPendingByEntity = pendingByEntityIds.map((id) => ({
        entity: entityMap.get(id) || null,
        count: entityCount[id],
      }))

      return NextResponse.json({
        data: {
          role: "REVIEWER",
          pendingApproval,
          rejected,
          approvedToday,
          avgApprovalTime,
          approvalTrend,
          pendingByCountry: enrichedPendingByCountry,
          pendingByEntity: enrichedPendingByEntity,
          recentActivities,
        },
      })
    }

    // ADMINISTRATOR or MANAGER
    const [
      totalCompliances,
      completedCount,
      rejectedCount,
      awaitingApproval,
      recentActivities,
    ] = await Promise.all([
      supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).then((r) => r.count || 0),
      supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).in("status", ["FILED", "APPROVED"]).then((r) => r.count || 0),
      supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).eq("status", "REJECTED").then((r) => r.count || 0),
      supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).eq("status", "PENDING_APPROVAL").then((r) => r.count || 0),
      supabaseAdmin.from("activities").select("*, user:users(id, name), compliance:compliance_schedules!inner(id, complianceId)").eq("compliance_schedules.orgId", orgId).order("createdAt", { ascending: false }).limit(10).then((r) => (r.data || []) as unknown as ActivityRow[]),
    ])

    const pending = totalCompliances - completedCount

    const { count: overdue } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*", { count: "exact", head: true })
      .eq("orgId", orgId)
      .lt("dueDate", now.toISOString())
      .not("status", "in", `("FILED","APPROVED","CLOSED")`)

    const { count: filedLate } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*", { count: "exact", head: true })
      .eq("orgId", orgId)
      .not("filedAt", "is", null)
      .or("filedAt.gt.dueDate")

    const { count: paidLate } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*", { count: "exact", head: true })
      .eq("orgId", orgId)
      .eq("requiresPayment", true)
      .not("paymentDate", "is", null)
      .not("paymentDueDate", "is", null)
      .or("paymentDate.gt.paymentDueDate")

    const monthlyTrend: { month: string; total: number; completed: number }[] = []
    for (let i = 11; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const monthStart = new Date(d.getFullYear(), d.getMonth(), 1)
      const monthEnd = new Date(d.getFullYear(), d.getMonth() + 1, 1)
      const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`

      const [totalInMonth, completedInMonth] = await Promise.all([
        supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).lt("createdAt", monthEnd.toISOString()).then((r) => r.count || 0),
        supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).eq("orgId", orgId).in("status", ["FILED", "CLOSED"]).gte("updatedAt", monthStart.toISOString()).lt("updatedAt", monthEnd.toISOString()).then((r) => r.count || 0),
      ])
      monthlyTrend.push({ month: monthKey, total: totalInMonth, completed: completedInMonth })
    }

    const { data: allStatuses } = await supabaseAdmin.from("compliance_schedules").select("status").eq("orgId", orgId)
    const statusCounts: Record<string, number> = {}
    allStatuses?.forEach((s: StatusRow) => {
      statusCounts[s.status] = (statusCounts[s.status] || 0) + 1
    })
    const statusDistribution = Object.entries(statusCounts).map(([status, count]) => ({ status, count }))

    const { data: allCountryIds } = await supabaseAdmin.from("compliance_schedules").select("countryId").eq("orgId", orgId)
    const countryCounts: Record<string, number> = {}
    allCountryIds?.forEach((s: IdRow) => {
      if (s.countryId) countryCounts[s.countryId] = (countryCounts[s.countryId] || 0) + 1
    })
    const countryIdsList = Object.keys(countryCounts)
    const { data: countriesData } = countryIdsList.length > 0
      ? await supabaseAdmin.from("countries").select("id, name, code").in("id", countryIdsList)
      : { data: [] }
    const countryMap = new Map<string, NameRow>(((countriesData || []) as unknown as NameRow[]).map((c) => [c.id, c] as const))
    const countryWiseCompliance = countryIdsList.map((id) => ({
      country: countryMap.get(id) || null,
      count: countryCounts[id],
    }))

    const { data: allEntityIds } = await supabaseAdmin.from("compliance_schedules").select("entityId").eq("orgId", orgId)
    const entityCounts: Record<string, number> = {}
    allEntityIds?.forEach((s: IdRow) => {
      if (s.entityId) entityCounts[s.entityId] = (entityCounts[s.entityId] || 0) + 1
    })
    const entityIdsList = Object.keys(entityCounts)
    const { data: entitiesData } = entityIdsList.length > 0
      ? await supabaseAdmin.from("legal_entities").select("id, entityName, entityNumber").in("id", entityIdsList)
      : { data: [] }
    const entityMap = new Map<string, NameRow>(((entitiesData || []) as unknown as NameRow[]).map((e) => [e.id, e] as const))
    const entityWiseCompliance = entityIdsList.map((id) => ({
      entity: entityMap.get(id) || null,
      count: entityCounts[id],
    }))

    const { data: allComplianceTypeIds } = await supabaseAdmin.from("compliance_schedules").select("complianceTypeId").eq("orgId", orgId)
    const ctCounts: Record<string, number> = {}
    allComplianceTypeIds?.forEach((s: IdRow) => {
      if (s.complianceTypeId) ctCounts[s.complianceTypeId] = (ctCounts[s.complianceTypeId] || 0) + 1
    })
    const ctIdsList = Object.keys(ctCounts)
    const { data: ctData } = ctIdsList.length > 0
      ? await supabaseAdmin.from("compliance_types").select("id, name, taxType").in("id", ctIdsList)
      : { data: [] }
    const ctMap = new Map<string, NameRow>(((ctData || []) as unknown as NameRow[]).map((c) => [c.id, c] as const))
    const taxTypeDistribution = ctIdsList.map((id) => ({
      complianceType: ctMap.get(id) || null,
      count: ctCounts[id],
    }))

    // Employees in the org
    const { data: orgMembers } = await supabaseAdmin
      .from("organization_members")
      .select("userId, roles")
      .eq("orgId", orgId)

    const memberUserIds = (orgMembers || []).map((m: OrgMemberRow) => m.userId)
    const { data: employees } = memberUserIds.length > 0
      ? await supabaseAdmin.from("users").select("id, name, email, role").in("id", memberUserIds).eq("isActive", true)
      : { data: [] }

    const employeeWorkload = await Promise.all(
      ((employees || []) as unknown as UserRow[]).map(async (emp) => {
        const [assigned, pendingCount, completedCount, overdueCount] = await Promise.all([
          supabaseAdmin.from("compliance_assignments").select("*", { count: "exact", head: true }).eq("preparerId", emp.id).then((r) => r.count || 0),
          (async () => {
            const { data: ids } = await supabaseAdmin.from("compliance_assignments").select("complianceId").eq("preparerId", emp.id)
            const cIds = ids?.map((a: AssignmentRow) => a.complianceId) || []
            if (cIds.length === 0) return 0
            const { count } = await supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).in("id", cIds).not("status", "in", `("FILED","APPROVED","CLOSED")`)
            return count || 0
          })(),
          (async () => {
            const { data: ids } = await supabaseAdmin.from("compliance_assignments").select("complianceId").eq("preparerId", emp.id)
            const cIds = ids?.map((a: AssignmentRow) => a.complianceId) || []
            if (cIds.length === 0) return 0
            const { count } = await supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).in("id", cIds).in("status", ["FILED", "APPROVED"])
            return count || 0
          })(),
          (async () => {
            const { data: ids } = await supabaseAdmin.from("compliance_assignments").select("complianceId").eq("preparerId", emp.id)
            const cIds = ids?.map((a: AssignmentRow) => a.complianceId) || []
            if (cIds.length === 0) return 0
            const { count } = await supabaseAdmin.from("compliance_schedules").select("*", { count: "exact", head: true }).in("id", cIds).lt("dueDate", now.toISOString()).not("status", "in", `("FILED","APPROVED","CLOSED")`)
            return count || 0
          })(),
        ])
        return { employee: emp, assigned, pending: pendingCount, completed: completedCount, overdue: overdueCount }
      })
    )

    const { data: overdueItems } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, dueDate, priority, status, countryId, entityId")
      .eq("orgId", orgId)
      .lt("dueDate", now.toISOString())
      .not("status", "in", `("FILED","APPROVED","CLOSED")`)
      .order("dueDate", { ascending: true })

    const overdueHeatMap = ((overdueItems || []) as unknown as ScheduleRow[]).map((item) => ({
      ...item,
      daysOverdue: Math.floor((now.getTime() - new Date(item.dueDate).getTime()) / 86400000),
    }))

    const { data: approvalBottlenecks } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, submittedAt, entity:legal_entities(entityName), country:countries(name), approvals:compliance_approvals!inner(id, approver:users!inner(id, name, email))")
      .eq("orgId", orgId)
      .eq("status", "PENDING_APPROVAL")
      .order("submittedAt", { ascending: true })
      .limit(20)

    const delayedCountryCounts: Record<string, number> = {}
    ;((overdueItems || []) as unknown as ScheduleRow[]).forEach((item) => {
      if (item.countryId) delayedCountryCounts[item.countryId] = (delayedCountryCounts[item.countryId] || 0) + 1
    })
    const delayedCountrySorted = Object.entries(delayedCountryCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
    const delayedCountryIds = delayedCountrySorted.map(([id]) => id)
    const { data: delayedCountriesData } = delayedCountryIds.length > 0
      ? await supabaseAdmin.from("countries").select("id, name, code").in("id", delayedCountryIds)
      : { data: [] }
    const delayedCountryMap = new Map<string, NameRow>(((delayedCountriesData || []) as unknown as NameRow[]).map((c) => [c.id, c] as const))
    const topDelayedCountries = delayedCountrySorted.map(([id, count]) => ({
      country: delayedCountryMap.get(id) || null,
      overdueCount: count,
    }))

    const delayedEntityCounts: Record<string, number> = {}
    ;((overdueItems || []) as unknown as ScheduleRow[]).forEach((item) => {
      if (item.entityId) delayedEntityCounts[item.entityId] = (delayedEntityCounts[item.entityId] || 0) + 1
    })
    const delayedEntitySorted = Object.entries(delayedEntityCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
    const delayedEntityIds = delayedEntitySorted.map(([id]) => id)
    const { data: delayedEntitiesData } = delayedEntityIds.length > 0
      ? await supabaseAdmin.from("legal_entities").select("id, entityName, entityNumber").in("id", delayedEntityIds)
      : { data: [] }
    const delayedEntityMap = new Map<string, NameRow>(((delayedEntitiesData || []) as unknown as NameRow[]).map((e) => [e.id, e] as const))
    const topDelayedEntities = delayedEntitySorted.map(([id, count]) => ({
      entity: delayedEntityMap.get(id) || null,
      overdueCount: count,
    }))

    const { data: sourceRows } = await supabaseAdmin
      .from("compliance_schedules")
      .select("source")
      .eq("orgId", orgId)
    const sourceCounts: Record<string, number> = {}
    sourceRows?.forEach((row: { source: string | null }) => {
      const key = row.source || "MANUAL"
      sourceCounts[key] = (sourceCounts[key] || 0) + 1
    })
    const complianceSource = (["TEMPLATE", "MANUAL", "IMPORT"] as const)
      .map((s) => ({ name: s, value: sourceCounts[s] || 0 }))
      .filter((s) => s.value > 0)

    const { data: allFiltersCountries } = await supabaseAdmin.from("countries").select("id, name, code").order("name")
    const { data: allFiltersEntities } = await supabaseAdmin.from("legal_entities").select("id, entityName, entityNumber").eq("orgId", orgId).order("entityName")
    const { data: allFiltersTaxTypes } = await supabaseAdmin.from("compliance_types").select("id, name, taxType").eq("orgId", orgId).order("name")
    const { data: allFiltersCtypes } = await supabaseAdmin.from("compliance_types").select("id, name").eq("orgId", orgId).order("name")

    return NextResponse.json({
      data: {
        role: "ADMINISTRATOR",
        totalCompliances,
        completed: completedCount,
        pending,
        overdue: overdue || 0,
        filedLate: filedLate || 0,
        paidLate: paidLate || 0,
        rejected: rejectedCount,
        awaitingApproval,
        complianceStatus: statusDistribution,
        countryWiseCompliance,
        entityWiseCompliance,
        taxTypeDistribution,
        monthlyComplianceTrend: monthlyTrend,
        employeeWorkload,
        overdueHeatMap,
        approvalBottlenecks: approvalBottlenecks || [],
        topDelayedCountries,
        topDelayedEntities,
        complianceSource,
        recentActivities,
      },
      filters: {
        countries: allFiltersCountries || [],
        entities: allFiltersEntities || [],
        taxTypes: allFiltersTaxTypes || [],
        complianceTypes: allFiltersCtypes || [],
        employees: employees || [],
      },
    })
  } catch (error) {
    console.error("GET /api/kpi/dashboard error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
