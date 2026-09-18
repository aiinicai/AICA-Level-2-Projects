import { createServerFn } from "@tanstack/react-start";

export const apiCall = createServerFn({ method: "POST" })
  .inputValidator((input: { path: string; method: string; body?: unknown; token?: string | null }) => {
    if (!input || typeof input.path !== "string" || typeof input.method !== "string") {
      throw new Error("Invalid request");
    }
    return input;
  })
  .handler(async ({ data }) => {
    const { handleApi } = await import("./api-handlers.server");
    const res = await handleApi(data);
    return { status: res.status, json: JSON.stringify(res.body ?? null) };
  });
