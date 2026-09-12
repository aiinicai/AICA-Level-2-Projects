"use client"

import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableHeader, TableBody, TableHead, TableRow, TableCell,
} from "@/components/ui/table"
import { Tag } from "lucide-react"
import { TAX_TYPE_OPTIONS } from "@/lib/tax-types"

const DESCRIPTIONS: Record<string, string> = {
  VAT: "Consumption tax added to goods and services at each stage of the supply chain.",
  GST: "Broad-based consumption tax levied on most goods and services.",
  SALES_TAX: "Tax imposed on the sale of goods and services at the point of sale.",
  WHT: "Tax deducted at source from payments such as interest, dividends, and royalties.",
  CORPORATE_TAX: "Tax levied on the profits of companies and business income.",
  STATUTORY: "Statutory levies such as social security, provident fund, and other contributions.",
}

const TAX_TYPES = TAX_TYPE_OPTIONS.map((t) => ({
  code: t.value,
  label: t.label,
  description: DESCRIPTIONS[t.value] || "",
}))

export default function TaxTypesPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Tax Types</CardTitle>
            <CardDescription>Tax types used across compliance schedules and form masters.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Code</TableHead>
                  <TableHead>Tax Type</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {TAX_TYPES.map((t) => (
                  <TableRow key={t.code}>
                    <TableCell><Badge variant="outline">{t.code}</Badge></TableCell>
                    <TableCell className="font-medium">{t.label}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{t.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
            <Tag className="h-4 w-4 mt-0.5 shrink-0" />
            <p>
              A tax type is selected when creating a compliance schedule and is shown on every
              schedule for quick identification. Forms can be tagged to a tax type so they are
              suggested when building a schedule.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
