import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

const COMPLIANCE_STATUSES = [
  "DRAFT", "PENDING_PREPARATION", "PREPARED", "PENDING_APPROVAL",
  "APPROVED", "REJECTED", "FILED", "CLOSED",
] as const

const TAX_TYPES = [
  "GST", "VAT", "SALES_TAX", "WHT", "CORPORATE_TAX", "STATUTORY",
] as const

interface IdRow {
  id: string
}

interface EntityRow {
  id: string
  entityName: string
  entityNumber: string | null
}

interface CountryRow {
  id: string
  name: string
  code: string | null
}

interface ComplianceScheduleRow {
  id: string
  complianceId: string
  entity: { entityName: string } | null
  complianceType: { name: string; taxType: string | null } | null
}

interface FormRow {
  id: string
  formNumber: string
  formName: string
  description: string | null
}

interface EmployeeRow {
  id: string
  name: string | null
  email: string | null
  role: string | null
}

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const q = searchParams.get("q") || ""

    if (!q || q.length < 2) {
      return NextResponse.json({ results: [] })
    }

    const matchingStatuses = COMPLIANCE_STATUSES.filter(
      (s) => s.toLowerCase().includes(q.toLowerCase())
    )
    const matchingTaxTypes = TAX_TYPES.filter(
      (t) => t.toLowerCase().includes(q.toLowerCase())
    )

    let matchingTaxTypeIds: string[] = []
    if (matchingTaxTypes.length > 0) {
      const { data: taxTypes } = await supabaseAdmin
        .from("compliance_types")
        .select("id")
        .in("taxType", matchingTaxTypes)
      if (taxTypes) matchingTaxTypeIds = taxTypes.map((t: IdRow) => t.id)
    }

    const { data: matchingEntities } = await supabaseAdmin
      .from("legal_entities")
      .select("id")
      .ilike("entityName", `%${q}%`)
      .limit(10)
    const matchingEntityIds = matchingEntities?.map((e: IdRow) => e.id) || []

    const { data: matchingComplianceTypes } = await supabaseAdmin
      .from("compliance_types")
      .select("id")
      .ilike("name", `%${q}%`)
      .limit(10)
    const matchingComplianceTypeIds = matchingComplianceTypes?.map((t: IdRow) => t.id) || []

    const combinedComplianceTypeIds = [
      ...new Set([...matchingTaxTypeIds, ...matchingComplianceTypeIds]),
    ]

    const results = await Promise.all([
      supabaseAdmin
        .from("legal_entities")
        .select("id, entityName, entityNumber")
        .or(`entityName.ilike.%${q}%,entityNumber.ilike.%${q}%,taxRegistrationNumber.ilike.%${q}%`)
        .limit(10),
      supabaseAdmin
        .from("countries")
        .select("id, name, code")
        .or(`name.ilike.%${q}%,code.ilike.%${q}%`)
        .limit(10),
      (() => {
        const orParts: string[] = [
          `complianceId.ilike.%${q}%`,
          `taxPeriod.ilike.%${q}%`,
          ...(matchingStatuses.length > 0
            ? [`status.in.(${matchingStatuses.join(",")})`]
            : []),
          ...(combinedComplianceTypeIds.length > 0
            ? [`complianceTypeId.in.(${combinedComplianceTypeIds.join(",")})`]
            : []),
          `notes.ilike.%${q}%`,
          ...(matchingEntityIds.length > 0
            ? [`entityId.in.(${matchingEntityIds.join(",")})`]
            : []),
        ]
        return supabaseAdmin
          .from("compliance_schedules")
          .select("id, complianceId, dueDate, priority, status, entity:legal_entities!entityId(entityName), complianceType:compliance_types!complianceTypeId(name, taxType)")
          .or(orParts.join(","))
          .order("dueDate", { ascending: true })
          .limit(10)
      })(),
      supabaseAdmin
        .from("form_master")
        .select("id, formNumber, formName, description")
        .or(`formNumber.ilike.%${q}%,formName.ilike.%${q}%`)
        .limit(10),
      supabaseAdmin
        .from("users")
        .select("id, name, email, role")
        .or(`name.ilike.%${q}%,email.ilike.%${q}%,username.ilike.%${q}%,employeeId.ilike.%${q}%`)
        .limit(10),
    ])

    for (const r of results) {
      if (r.error) throw r.error
    }

    const [entities, countries, complianceSchedules, forms, employees] = results.map(
      (r) => r.data || []
    )

    const output: {
      type: string
      id: string
      title: string
      subtitle: string
      url: string
    }[] = []

    ;(entities as unknown as EntityRow[]).forEach((e) => {
      output.push({
        type: "Entity",
        id: e.id,
        title: e.entityName,
        subtitle: e.entityNumber || "",
        url: `/master/entities/${e.id}`,
      })
    })

    ;(countries as unknown as CountryRow[]).forEach((c) => {
      output.push({
        type: "Country",
        id: c.id,
        title: c.name,
        subtitle: c.code || "",
        url: `/master/countries/${c.id}`,
      })
    })

    ;(complianceSchedules as unknown as ComplianceScheduleRow[]).forEach((cs) => {
      output.push({
        type: "Compliance Schedule",
        id: cs.id,
        title: cs.complianceId,
        subtitle: `${cs.entity?.entityName || "—"} | ${cs.complianceType?.name || ""} (${cs.complianceType?.taxType || ""})`,
        url: `/compliance/${cs.id}`,
      })
    })

    ;(forms as unknown as FormRow[]).forEach((f) => {
      output.push({
        type: "Form",
        id: f.id,
        title: `${f.formNumber} - ${f.formName}`,
        subtitle: f.description || "",
        url: `/master/forms/${f.id}`,
      })
    })

    ;(employees as unknown as EmployeeRow[]).forEach((emp) => {
      output.push({
        type: "Employee",
        id: emp.id,
        title: emp.name || emp.email || "",
        subtitle: `${emp.role || ""} | ${emp.email || ""}`,
        url: `/master/employees/${emp.id}`,
      })
    })

    return NextResponse.json({ results: output })
  } catch (error) {
    console.error("GET /api/search error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
