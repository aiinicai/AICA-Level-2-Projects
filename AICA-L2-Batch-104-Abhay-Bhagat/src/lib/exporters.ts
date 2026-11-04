import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import type { Client, ReconItem } from "./types";
import { STATUS_LABEL } from "./types";
import type { ReconResult } from "./recon";
import { inr } from "./recon";

export function exportExcel(client: Client, res: ReconResult, saved: ReconItem[], firmName: string) {
  const wb = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(
    wb,
    XLSX.utils.json_to_sheet([
      { Field: "Firm", Value: firmName },
      { Field: "Client", Value: client.name },
      { Field: "GSTIN", Value: client.gstin },
      { Field: "Financial Year", Value: client.fy },
      { Field: "State", Value: client.state },
      { Field: "Registration Type", Value: client.reg_type },
      { Field: "Prepared on", Value: new Date().toLocaleString("en-IN") },
      { Field: "Note", Value: "Reconciliation working only. This tool does not file GST returns." },
    ]),
    "Cover",
  );

  XLSX.utils.book_append_sheet(
    wb,
    XLSX.utils.json_to_sheet(
      res.summaries.map((r) => ({
        Section: r.section,
        Particulars: r.label,
        "As per Books": r.books,
        "As per GST Return": r.gst,
        Difference: r.diff,
        Note: r.note ?? "",
      })),
    ),
    "Summary",
  );

  const byKey = new Map(saved.map((s) => [`${s.section}|${s.key_label}`, s]));
  XLSX.utils.book_append_sheet(
    wb,
    XLSX.utils.json_to_sheet(
      res.items.map((i) => {
        const s = byKey.get(`${i.section}|${i.key_label}`);
        return {
          Section: i.section,
          Document: i.key_label,
          Party: i.party,
          Status: STATUS_LABEL[i.status],
          "Books Taxable": i.books_taxable,
          "Books Tax": i.books_tax,
          "Return Taxable": i.gst_taxable,
          "Return Tax": i.gst_tax,
          "Taxable Difference": +(i.books_taxable - i.gst_taxable).toFixed(2),
          "Tax Difference": +(i.books_tax - i.gst_tax).toFixed(2),
          Remarks: s?.remarks ?? "",
          "Proposed Adjustment": s?.adjustment ?? 0,
          "Proposed Treatment": s?.proposed_treatment ?? "",
          Resolved: s?.resolved ? "Yes" : "No",
        };
      }),
    ),
    "Transaction Level",
  );

  XLSX.utils.book_append_sheet(
    wb,
    XLSX.utils.json_to_sheet([
      { Particulars: "Total turnover (books)", Amount: res.totals.turnover },
      { Particulars: "Tax liability (books)", Amount: res.totals.liability },
      { Particulars: "ITC claimed", Amount: res.totals.itc },
      { Particulars: "Total variance", Amount: res.totals.variance },
      { Particulars: "Unreconciled transactions", Amount: res.totals.unreconciled },
      { Particulars: "Potential additional tax liability", Amount: res.totals.additionalTax },
      { Particulars: "Potential unclaimed ITC", Amount: res.totals.unclaimedItc },
    ]),
    "Dashboard",
  );

  XLSX.writeFile(wb, `GST_Reconciliation_${client.name.replace(/\W+/g, "_")}_${client.fy}.xlsx`);
}

export function exportPdf(client: Client, res: ReconResult, saved: ReconItem[], firmName: string) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const navy: [number, number, number] = [18, 38, 74];

  doc.setFillColor(...navy);
  doc.rect(0, 0, 595, 70, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.text(firmName, 40, 32);
  doc.setFontSize(11);
  doc.text("GST Annual Return Reconciliation Summary", 40, 52);

  doc.setTextColor(30, 30, 30);
  doc.setFontSize(10);
  autoTable(doc, {
    startY: 90,
    theme: "plain",
    body: [
      ["Client", client.name, "GSTIN", client.gstin],
      ["Financial Year", client.fy, "State", client.state],
      ["Registration Type", client.reg_type, "Prepared on", new Date().toLocaleDateString("en-IN")],
    ],
    styles: { fontSize: 9 },
  });

  autoTable(doc, {
    head: [["Key Figures", "Amount (INR)"]],
    body: [
      ["Total turnover as per books", inr(res.totals.turnover)],
      ["Tax liability as per books", inr(res.totals.liability)],
      ["ITC claimed", inr(res.totals.itc)],
      ["Total variance", inr(res.totals.variance)],
      ["Unreconciled transactions", String(res.totals.unreconciled)],
      ["Potential additional tax liability", inr(res.totals.additionalTax)],
      ["Potential unclaimed ITC", inr(res.totals.unclaimedItc)],
    ],
    headStyles: { fillColor: navy },
    styles: { fontSize: 9 },
  });

  autoTable(doc, {
    head: [["Section", "Particulars", "Books", "GST Return", "Difference"]],
    body: res.summaries.map((r) => [r.section, r.label, inr(r.books), inr(r.gst), inr(r.diff)]),
    headStyles: { fillColor: navy },
    styles: { fontSize: 8 },
    columnStyles: { 2: { halign: "right" }, 3: { halign: "right" }, 4: { halign: "right" } },
  });

  const open = saved.filter((s) => !s.resolved && s.remarks);
  if (open.length) {
    autoTable(doc, {
      head: [["Document", "Status", "Remarks", "Proposed treatment", "Adjustment"]],
      body: open.map((s) => [s.key_label, STATUS_LABEL[s.status], s.remarks, s.proposed_treatment, inr(s.adjustment)]),
      headStyles: { fillColor: navy },
      styles: { fontSize: 8 },
    });
  }

  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(120);
    doc.text(
      "Reconciliation working prepared for internal review. This software does not file GST returns.",
      40,
      820,
    );
    doc.text(`Page ${i} of ${pages}`, 520, 820);
  }

  doc.save(`GST_Reconciliation_${client.name.replace(/\W+/g, "_")}_${client.fy}.pdf`);
}
