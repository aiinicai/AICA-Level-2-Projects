// WhatsApp click-to-chat helpers (no API: WhatsApp opens with the message filled in, the user presses Send).

export const LINK_DAYS = 7;

/** Digits with country code for an Indian mobile ("98765 43210", "+91-98765-43210", "098765..."), or "" if not valid. */
export function normalizeIndianMobile(raw: string | null | undefined): string {
  let d = String(raw ?? "").replace(/\D/g, "");
  if (d.length === 11 && d.startsWith("0")) d = d.slice(1);
  if (d.length === 10) return /^[6-9]/.test(d) ? `91${d}` : "";
  if (d.length === 12 && d.startsWith("91")) return /^[6-9]/.test(d.slice(2)) ? d : "";
  if (d.length >= 11 && d.length <= 15 && !d.startsWith("0")) return d;   // another country's number with its code
  return "";
}

export function buildShareMessage(o: { name: string; report: string; ay: string; firm: string }) {
  return [
    `Dear ${o.name},`,
    "",
    `Please find the ${o.report} for AY ${o.ay} at the link below:`,
    "{link}",
    "",
    "The link is valid for 7 days.",
    "",
    "Regards,",
    o.firm,
  ].join("\n");
}

export function waLinks(number: string, message: string) {
  const t = encodeURIComponent(message);
  return {
    desktop: `whatsapp://send?phone=${number}&text=${t}`,
    web: `https://web.whatsapp.com/send?phone=${number}&text=${t}`,
    phone: `https://wa.me/${number}?text=${t}`,
  };
}
