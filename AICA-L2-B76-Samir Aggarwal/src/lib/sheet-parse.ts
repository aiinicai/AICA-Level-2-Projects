/**
 * Minimal spreadsheet reader for the bulk-upload screens.
 *
 * Deliberately hand-rolled rather than pulling in SheetJS: the npm build of
 * `xlsx` sits at 0.18.5 with an unpatched prototype-pollution advisory (the fix
 * only exists on the vendor's own CDN). An .xlsx is a zip of XML, so unzipping
 * with fflate and reading two files is a small, auditable amount of code.
 *
 * Returns rows keyed by a normalised header, so "Client Code", "client code"
 * and "CLIENT_CODE" all arrive as `clientcode`.
 */

import { unzipSync, strFromU8 } from 'fflate'

export type SheetRow = Record<string, string>

export function normaliseHeader(header: string): string {
  return header
    .toLowerCase()
    .replace(/\*/g, '')
    .replace(/[^a-z0-9]/g, '')
}

/** A1 -> 0, B1 -> 1, AA1 -> 26 */
function columnIndex(ref: string): number {
  const letters = ref.replace(/[0-9]/g, '')
  let index = 0
  for (const ch of letters) {
    index = index * 26 + (ch.charCodeAt(0) - 64)
  }
  return index - 1
}

// ------------------------------------------------------------------ CSV

/** Handles quoted fields, embedded commas, doubled quotes and CRLF. */
export function parseCSV(text: string): string[][] {
  const clean = text.replace(/^﻿/, '')
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false

  for (let i = 0; i < clean.length; i += 1) {
    const ch = clean[i]

    if (inQuotes) {
      if (ch === '"') {
        if (clean[i + 1] === '"') {
          field += '"'
          i += 1
        } else {
          inQuotes = false
        }
      } else {
        field += ch
      }
      continue
    }

    if (ch === '"') {
      inQuotes = true
    } else if (ch === ',') {
      row.push(field)
      field = ''
    } else if (ch === '\n') {
      row.push(field)
      rows.push(row)
      row = []
      field = ''
    } else if (ch !== '\r') {
      field += ch
    }
  }

  if (field !== '' || row.length) {
    row.push(field)
    rows.push(row)
  }

  return rows
}

// ----------------------------------------------------------------- XLSX

function decodeXmlEntities(value: string): string {
  return value
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_m, code) => String.fromCharCode(Number(code)))
    .replace(/&amp;/g, '&')
}

/** Concatenated <t> runs, so rich text in a cell still reads as one string. */
function textOf(xml: string): string {
  const parts = [...xml.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map((m) => m[1])
  return decodeXmlEntities(parts.join(''))
}

function readSharedStrings(files: Record<string, Uint8Array>): string[] {
  const entry = files['xl/sharedStrings.xml']
  if (!entry) return []
  const xml = strFromU8(entry)
  return [...xml.matchAll(/<si>([\s\S]*?)<\/si>/g)].map((m) => textOf(m[1]))
}

/** The workbook's FIRST sheet, resolved through the relationship id. */
function firstSheetPath(files: Record<string, Uint8Array>): string | null {
  const workbook = files['xl/workbook.xml']
  const rels = files['xl/_rels/workbook.xml.rels']

  if (workbook && rels) {
    const sheet = strFromU8(workbook).match(/<sheet[^>]*r:id="([^"]+)"/)
    if (sheet) {
      const relXml = strFromU8(rels)
      const escaped = sheet[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const target = relXml.match(new RegExp(`Id="${escaped}"[^>]*Target="([^"]+)"`))
      if (target) {
        const path = target[1].replace(/^\/?xl\//, '').replace(/^\//, '')
        if (files[`xl/${path}`]) return `xl/${path}`
      }
    }
  }

  const candidates = Object.keys(files)
    .filter((name) => /^xl\/worksheets\/sheet\d+\.xml$/.test(name))
    .sort()
  return candidates[0] ?? null
}

export function parseXLSX(buffer: ArrayBuffer): string[][] {
  const files = unzipSync(new Uint8Array(buffer))
  const sheetPath = firstSheetPath(files)
  if (!sheetPath) throw new Error('No worksheet found in this file.')

  const shared = readSharedStrings(files)
  const xml = strFromU8(files[sheetPath])
  const rows: string[][] = []

  for (const rowMatch of xml.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)) {
    const cells: string[] = []
    // Both cell forms must be matched. Excel writes a styled-but-empty cell as
    // self-closing — <c r="F4" s="86"/> — and matching only <c ...>...</c>
    // swallows it into the following cell, leaking the style index as a value.
    for (const cellMatch of rowMatch[1].matchAll(
      /<c([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g,
    )) {
      const attrs = cellMatch[1]
      const inner = cellMatch[2] ?? ''
      const ref = attrs.match(/r="([A-Z]+\d+)"/)?.[1]
      const type = attrs.match(/t="([^"]+)"/)?.[1]

      let value = ''
      if (type === 's') {
        const index = Number(inner.match(/<v>([\s\S]*?)<\/v>/)?.[1] ?? '-1')
        value = shared[index] ?? ''
      } else if (type === 'inlineStr') {
        value = textOf(inner)
      } else {
        value = decodeXmlEntities(inner.match(/<v>([\s\S]*?)<\/v>/)?.[1] ?? '')
      }

      const index = ref ? columnIndex(ref) : cells.length
      while (cells.length < index) cells.push('')
      cells[index] = value
    }
    rows.push(cells)
  }

  // Self-closing <row/> for blank rows produces nothing above; that is fine.
  return rows
}

// ----------------------------------------------------------------- Public

export async function readSheet(file: File): Promise<SheetRow[]> {
  const name = file.name.toLowerCase()
  let grid: string[][]

  if (name.endsWith('.csv') || name.endsWith('.txt')) {
    grid = parseCSV(await file.text())
  } else if (name.endsWith('.xlsx') || name.endsWith('.xlsm')) {
    grid = parseXLSX(await file.arrayBuffer())
  } else {
    throw new Error('Upload an .xlsx or .csv file.')
  }

  // The header is the first row with at least two non-empty cells — tolerates
  // a stray title line above the table.
  const headerIndex = grid.findIndex(
    (row) => row.filter((cell) => cell && cell.trim()).length >= 2,
  )
  if (headerIndex === -1) throw new Error('That file appears to be empty.')

  const headers = grid[headerIndex].map(normaliseHeader)

  return grid
    .slice(headerIndex + 1)
    .map((cells, offset) => {
      const row: SheetRow = { __row: String(headerIndex + offset + 2) }
      headers.forEach((header, i) => {
        if (!header) return
        row[header] = (cells[i] ?? '').trim()
      })
      return row
    })
    .filter((row) =>
      Object.entries(row).some(([key, value]) => key !== '__row' && value !== ''),
    )
}
