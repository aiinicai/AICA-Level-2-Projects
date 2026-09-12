import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { buildApprovalRecords, effectiveApprovalFlow, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber, currency, approvalFlow),
  entities:compliance_entities(*, entity:legal_entities(id, entityName, entityNumber, currency, country:countries(name), approvalFlow)),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName, approvalFlow),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  confirmations:compliance_payment_confirmations(*, confirmedBy:users(id, name)),
  attachments:attachments(id, originalName, fileType, fileSize, version, createdAt),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

function sortNestedRelations(item: {
  comments?: { createdAt: string }[]
  activities?: { createdAt: string }[]
}) {
  if (item.comments) {
    item.comments.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
  }
  if (item.activities) {
    item.activities.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
  }
  return item
}

async function ensureOrgMember(orgId: string, userId: string, roles: string[]) {
  if (!orgId || !userId) return
  const { data: existing } = await supabaseAdmin
    .from("organization_members")
    .select("id, roles")
    .eq("orgId", orgId)
    .eq("userId", userId)
    .maybeSingle()

  if (existing) {
    const merged = Array.from(new Set([...(existing.roles || []), ...roles]))
    if (merged.length === (existing.roles || []).length) return
    await supabaseAdmin
      .from("organization_members")
      .update({ roles: merged, updatedAt: now() })
      .eq("id", existing.id)
    return
  }

  await supabaseAdmin
    .from("organization_members")
    .insert({
      id: newId(),
      orgId,
      userId,
      roles,
      updatedAt: now(),
    })
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    // IDOR check: verify user belongs to the compliance's organization
    const isMember = session.user.orgs.some((o) => o.id === data.orgId)
    if (!isMember) {
      return NextResponse.json({ error: "Forbidden: Not a member of this organization" }, { status: 403 })
    }

    return NextResponse.json({ data: sortNestedRelations(data) })
  } catch (error) {
    console.error("GET /api/compliance/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params
    const { orgId } = getActiveContextFromRequest(request)
    const body = await request.json()
    const {
      entityId,
      entityIds,
      countryId,
      taxType,
      formId,
      taxPeriod,
      frequency,
      dueDate,
      paymentDueDate,
      priority,
      status,
      isRecurring,
      notes,
      preparerId,
      reviewerId,
      approverId,
      filingEntityId,
      recurringEndDate,
      requiresPayment,
      approvalFlow: bodyApprovalFlow,
    } = body

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*), approvals:compliance_approvals(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    // IDOR check: verify user belongs to the compliance's organization
    const isMember = session.user.orgs.some((o) => o.id === existing.orgId)
    if (!isMember) {
      return NextResponse.json({ error: "Forbidden: Not a member of this organization" }, { status: 403 })
    }

    const oldStatus = existing.status
    const statusChanged = status && status !== oldStatus

    let nextEntityIds: string[] | null = null
    if (Array.isArray(entityIds)) {
      nextEntityIds = Array.from(new Set(entityIds.filter(Boolean)))
    } else if (entityId !== undefined) {
      nextEntityIds = entityId ? [entityId] : []
    }

    const updateData: Record<string, unknown> = {}
    if (filingEntityId !== undefined) {
      updateData.entityId = filingEntityId || null
    } else if (nextEntityIds !== null) {
      updateData.entityId = nextEntityIds[0] || null
    } else if (entityId !== undefined) {
      updateData.entityId = entityId
    }
    if (countryId !== undefined) updateData.countryId = countryId
    if (taxType !== undefined) updateData.taxType = taxType
    if (formId !== undefined) updateData.formId = formId || null
    if (taxPeriod !== undefined) updateData.taxPeriod = taxPeriod
    if (frequency !== undefined) updateData.frequency = frequency
    if (dueDate !== undefined) updateData.dueDate = new Date(dueDate).toISOString()
    if (paymentDueDate !== undefined && requiresPayment !== false) {
      updateData.paymentDueDate = paymentDueDate ? new Date(paymentDueDate).toISOString() : null
    }
    if (requiresPayment !== undefined) {
      updateData.requiresPayment = requiresPayment === true
      if (!requiresPayment) updateData.paymentDueDate = null
    }
    if (priority !== undefined) updateData.priority = priority
    if (status !== undefined) updateData.status = status
    if (isRecurring !== undefined) updateData.isRecurring = isRecurring
    if (notes !== undefined) updateData.notes = notes
    if (recurringEndDate !== undefined) {
      updateData.recurringEndDate = recurringEndDate ? new Date(recurringEndDate).toISOString() : null
    }
    updateData.updatedAt = now()

    const { error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update(updateData)
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    if (statusChanged) {
      const { error: activityError } = await supabaseAdmin
        .from("activities")
        .insert({
          id: newId(),
          complianceId: id,
          userId: session.user.id,
          action: "STATUS_CHANGED",
          fromStatus: oldStatus,
          toStatus: status,
        })

      if (activityError) throw activityError

      const { error: auditError } = await supabaseAdmin
        .from("audit_trails")
        .insert({
          id: newId(),
          userId: session.user.id,
          action: "STATUS_CHANGE",
          entity: "ComplianceSchedule",
          entityId: id,
          oldValue: oldStatus,
          newValue: status,
        })

      if (auditError) throw auditError
    }

    if (nextEntityIds !== null) {
      const { error: deleteEntityError } = await supabaseAdmin
        .from("compliance_entities")
        .delete()
        .eq("complianceId", id)

      if (deleteEntityError) throw deleteEntityError

      if (nextEntityIds.length > 0) {
        const { error: createEntityError } = await supabaseAdmin
          .from("compliance_entities")
          .insert(
            nextEntityIds.map((eid: string) => ({
              id: newId(),
              complianceId: id,
              entityId: eid,
            }))
          )

        if (createEntityError) throw createEntityError
      }
    }

    if (preparerId !== undefined) {
      const { error: deleteAssignError } = await supabaseAdmin
        .from("compliance_assignments")
        .delete()
        .eq("complianceId", id)

      if (deleteAssignError) throw deleteAssignError

      if (preparerId) {
        const { error: createAssignError } = await supabaseAdmin
          .from("compliance_assignments")
          .insert({ id: newId(), complianceId: id, preparerId, updatedAt: now() })

        if (createAssignError) throw createAssignError

        if (orgId) await ensureOrgMember(orgId, preparerId, ["PREPARER"])
      }
    }

    if (reviewerId !== undefined || bodyApprovalFlow !== undefined) {
      let flow: ApprovalFlow
      if (bodyApprovalFlow) {
        flow = normalizeApprovalFlow(bodyApprovalFlow as string)
      } else if (existing.approvalFlow) {
        flow = normalizeApprovalFlow(existing.approvalFlow as string)
      } else {
        let entityFlow: ApprovalFlow = "ONE_LEVEL"
        const flowEntityId = filingEntityId ?? existing.entityId
        if (flowEntityId) {
          const { data: entity } = await supabaseAdmin
            .from("legal_entities")
            .select("approvalFlow")
            .eq("id", flowEntityId)
            .maybeSingle()
          entityFlow = normalizeApprovalFlow((entity?.approvalFlow as string) || undefined)
        }

        const effectiveFormId = formId !== undefined ? formId || null : (existing.formId as string | null) || null
        let formFlow: ApprovalFlow | undefined
        if (effectiveFormId) {
          const { data: formRow } = await supabaseAdmin
            .from("form_master")
            .select("approvalFlow")
            .eq("id", effectiveFormId)
            .maybeSingle()
          if (formRow?.approvalFlow) {
            formFlow = normalizeApprovalFlow(formRow.approvalFlow as string)
          }
        }

        flow = effectiveApprovalFlow(formFlow, entityFlow)
      }

      const { error: deleteApprovalError } = await supabaseAdmin
        .from("compliance_approvals")
        .delete()
        .eq("complianceId", id)

      if (deleteApprovalError) throw deleteApprovalError

      const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)

      if (approvalRecords.length > 0) {
        const { error: createApprovalError } = await supabaseAdmin
          .from("compliance_approvals")
          .insert(
            approvalRecords.map((record) => ({
              id: newId(),
              complianceId: id,
              approverId: record.approverId,
              step: record.step,
              status: "PENDING_APPROVAL",
              updatedAt: now(),
            }))
          )

        if (createApprovalError) throw createApprovalError

        if (orgId) {
          for (const record of approvalRecords) {
            await ensureOrgMember(orgId, record.approverId, record.step === 1 ? ["REVIEWER"] : ["APPROVER"])
          }
        }
      }
    }

    const { data: data, error: refetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", id)
      .single()

    if (refetchError) throw refetchError

    return NextResponse.json({ data: sortNestedRelations(data) })
  } catch (error) {
    console.error("PUT /api/compliance/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { activeRole } = getActiveContextFromRequest(request)
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can delete compliances" }, { status: 403 })
    }

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("complianceId")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    const { error: delAssignError } = await supabaseAdmin
      .from("compliance_assignments")
      .delete()
      .eq("complianceId", id)

    if (delAssignError) throw delAssignError

    const { error: delApprovalError } = await supabaseAdmin
      .from("compliance_approvals")
      .delete()
      .eq("complianceId", id)

    if (delApprovalError) throw delApprovalError

    const { error: delEntityError } = await supabaseAdmin
      .from("compliance_entities")
      .delete()
      .eq("complianceId", id)

    if (delEntityError) throw delEntityError

    const { error: delAttachError } = await supabaseAdmin
      .from("attachments")
      .delete()
      .eq("complianceId", id)

    if (delAttachError) throw delAttachError

    const { error: delCommentError } = await supabaseAdmin
      .from("comments")
      .delete()
      .eq("complianceId", id)

    if (delCommentError) throw delCommentError

    const { error: delActivityError } = await supabaseAdmin
      .from("activities")
      .delete()
      .eq("complianceId", id)

    if (delActivityError) throw delActivityError

    const { error: delError } = await supabaseAdmin
      .from("compliance_schedules")
      .delete()
      .eq("id", id)

    if (delError) throw delError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "DELETE",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: JSON.stringify({ complianceId: existing.complianceId }),
      })

    if (auditError) throw auditError

    return NextResponse.json({ data: { message: "Compliance deleted successfully" } })
  } catch (error) {
    console.error("DELETE /api/compliance/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
