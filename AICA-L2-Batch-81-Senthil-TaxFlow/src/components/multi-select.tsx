"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Check, ChevronDown, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface Option {
  value: string
  label: string
  country?: string
}

interface MultiSelectProps {
  options: Option[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  label?: string
  disabled?: boolean
  searchable?: boolean
  showCountryFilter?: boolean
}

export default function MultiSelect({ options, selected, onChange, placeholder = "Select...", label, disabled = false, searchable = false, showCountryFilter = false }: MultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [countryFilter, setCountryFilter] = useState("")
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  function toggle(value: string) {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const countries = useMemo(
    () => Array.from(new Set(options.map((o) => o.country).filter(Boolean) as string[])).sort(),
    [options]
  )

  const filteredOptions = useMemo(() => {
    let list = options
    if (countryFilter) list = list.filter((o) => o.country === countryFilter)
    if (query) {
      const q = query.toLowerCase()
      list = list.filter((o) => o.label.toLowerCase().includes(q) || (o.country || "").toLowerCase().includes(q))
    }
    return list
  }, [options, query, countryFilter])

  const selectedLabels = selected
    .map((v) => options.find((o) => o.value === v)?.label)
    .filter(Boolean)

  return (
    <div ref={ref} className="space-y-2">
      {label && <Label>{label}</Label>}
      <div className="relative">
        <Button
          type="button"
          variant="outline"
          className="w-full justify-between text-left font-normal"
          disabled={disabled}
          onClick={() => setOpen(!open)}
        >
          <span className="truncate">
            {selectedLabels.length > 0 ? selectedLabels.join(", ") : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 ml-2 shrink-0 opacity-50" />
        </Button>
        {open && !disabled && (
          <div className="absolute z-50 w-full mt-1 rounded-md border bg-popover text-popover-foreground shadow-md">
            <div className="p-1">
              {(searchable || showCountryFilter) && (
                <div className="border-b pb-1.5 mb-1 space-y-1.5">
                  {searchable && (
                    <Input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search..."
                      className="h-8 text-sm"
                    />
                  )}
                  {showCountryFilter && countries.length > 1 && (
                    <select
                      value={countryFilter}
                      onChange={(e) => setCountryFilter(e.target.value)}
                      className="w-full h-8 text-sm rounded-md border bg-background px-2"
                    >
                      <option value="">All countries</option>
                      {countries.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
              {filteredOptions.length === 0 && (
                <div className="px-2 py-4 text-sm text-center text-muted-foreground">No options</div>
              )}
              {filteredOptions.map((option) => {
                const isSelected = selected.includes(option.value)
                return (
                  <div
                    key={option.value}
                    className="w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-sm cursor-pointer hover:bg-accent hover:text-accent-foreground"
                    onClick={() => toggle(option.value)}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-[var(--color-primary)] shadow-sm",
                        isSelected && "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]"
                      )}
                    >
                      {isSelected && <Check className="h-4 w-4" />}
                    </span>
                    {option.label}
                  </div>
                )
              })}
            </div>
            {selected.length > 0 && (
              <div className="border-t p-1">
                <button
                  type="button"
                  className="w-full flex items-center justify-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground rounded-sm"
                  onClick={() => onChange([])}
                >
                  <X className="h-3 w-3" />
                  Clear all
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
