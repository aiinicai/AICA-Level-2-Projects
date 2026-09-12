import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"
import { readFile } from "fs/promises"
import { existsSync } from "fs"

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

    const { data: attachment, error } = await supabaseAdmin
      .from("attachments")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!attachment) {
      return NextResponse.json({ error: "Attachment not found" }, { status: 404 })
    }

    if (!existsSync(attachment.filePath)) {
      return NextResponse.json({ error: "File not found on disk" }, { status: 404 })
    }

    const fileBuffer = await readFile(attachment.filePath)

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": attachment.fileType || "application/octet-stream",
        "Content-Disposition": `attachment; filename="${attachment.originalName}"`,
        "Content-Length": String(fileBuffer.length),
      },
    })
  } catch (error) {
    console.error("GET /api/attachments/[id]/download error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
