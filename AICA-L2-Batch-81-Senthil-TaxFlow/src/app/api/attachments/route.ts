import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"
import { writeFile, mkdir } from "fs/promises"
import { existsSync } from "fs"
import { join } from "path"

const UPLOAD_DIR = join(process.cwd(), "public", "uploads")

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const formData = await request.formData()
    const file = formData.get("file")
    const complianceId = formData.get("complianceId") as string

    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "File is required" }, { status: 400 })
    }
    if (!complianceId) {
      return NextResponse.json({ error: "complianceId is required" }, { status: 400 })
    }

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id")
      .eq("id", complianceId)
      .maybeSingle()

    if (existingError) throw existingError
    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    if (!existsSync(UPLOAD_DIR)) {
      await mkdir(UPLOAD_DIR, { recursive: true })
    }

    const ext = file.name.includes(".") ? file.name.split(".").pop() : ""
    const fileName = `${complianceId}_${Date.now()}_${Math.floor(Math.random() * 1000)}${ext ? `.${ext}` : ""}`
    const filePath = join(UPLOAD_DIR, fileName)
    const buffer = Buffer.from(await file.arrayBuffer())
    await writeFile(filePath, buffer)

    const { data, error } = await supabaseAdmin
      .from("attachments")
      .insert({
        id: newId(),
        complianceId,
        userId: session.user.id,
        fileName,
        originalName: file.name,
        fileType: file.type || "application/octet-stream",
        fileSize: file.size,
        filePath,
        createdAt: now(),
      })
      .select("id, originalName, fileType, fileSize, version, createdAt")
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/attachments error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
