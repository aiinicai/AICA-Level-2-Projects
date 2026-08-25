import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const schema = z.object({
  total: z.number(),
  counts: z.record(z.string(), z.number()),
  itcAtRisk: z.number(),
  topIssues: z
    .array(
      z.object({
        supplier: z.string(),
        gstin: z.string(),
        invoiceNumber: z.string(),
        category: z.string(),
        difference: z.number(),
      }),
    )
    .max(40),
});

export const generateSummaryNote = createServerFn({ method: "POST" })
  .inputValidator((data: unknown) => schema.parse(data))
  .handler(async ({ data }) => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) throw new Error("AI is not configured");

    const res = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          {
            role: "system",
            content:
              "You are a GST audit assistant for Indian Chartered Accountants. Write a crisp 3-4 sentence plain-English summary note of key ITC risk areas and suggested next steps, naming specific suppliers to follow up with. No markdown, no bullet points.",
          },
          { role: "user", content: JSON.stringify(data) },
        ],
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(res.status === 429 ? "Rate limit reached, please retry shortly." : text.slice(0, 200));
    }
    const json = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    return { note: json.choices?.[0]?.message?.content ?? "No summary generated." };
  });
