"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Building2, Globe, Tag, BookOpen, Users, Coins } from "lucide-react"
import Link from "next/link"

const overviewCards = [
  {
    title: "Countries",
    description: "Manage country master data.",
    icon: Globe,
    href: "/master/countries",
    color: "bg-blue-500",
  },
  {
    title: "Entities",
    description: "Manage legal entities and tax registration details.",
    icon: Building2,
    href: "/master/entities",
    color: "bg-emerald-500",
  },

  {
    title: "Tax Types",
    description: "Manage tax types such as VAT, WHT, and income tax.",
    icon: Tag,
    href: "/master/tax-types",
    color: "bg-cyan-500",
  },
  {
    title: "Forms",
    description: "Manage form masters linked to compliance types and countries.",
    icon: BookOpen,
    href: "/master/forms",
    color: "bg-purple-500",
  },
  {
    title: "Employees",
    description: "Manage users, roles, departments, and reporting structures.",
    icon: Users,
    href: "/master/employees",
    color: "bg-rose-500",
  },
  {
    title: "Currencies",
    description: "Manage currency master data independently from countries.",
    icon: Coins,
    href: "/master/currencies",
    color: "bg-amber-500",
  },
]

export default function MasterOverviewPage() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Master Data Management</CardTitle>
          <CardDescription>
            Select a category below to manage reference data used across the TaxFlow platform.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {overviewCards.map((card) => (
              <Link key={card.href} href={card.href}>
                <Card className="card-hover cursor-pointer transition-all hover:shadow-md">
                  <CardHeader className="pb-2">
                    <div className={`h-10 w-10 rounded-lg ${card.color} flex items-center justify-center mb-2`}>
                      <card.icon className="h-5 w-5 text-white" />
                    </div>
                    <CardTitle className="text-base">{card.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-500">
                      {card.description}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
