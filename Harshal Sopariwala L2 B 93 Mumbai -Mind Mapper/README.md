# HS Mind Mapper

A single-file, offline mind-mapping tool. Open `HS Mind Mapper - Demo.html` in Chrome or Edge - no install, no server, no account. It opens with a sample map explaining **Rule 11UA and Section 50C** of the Income-tax Act. `HS Mind Mapper.html` is the same app without the sample.

## What it does

| Area | Capability |
|---|---|
| Maps | Create, rename, switch and delete multiple maps (sidebar list, sorted by last edited) |
| Nodes | Double-click canvas for a new idea; **+** branches off a node; **x** deletes a node and its branches |
| Structure | Drag a node onto another to re-parent; promote / demote level; reorder siblings; collapse / expand branches (or all at once) |
| Notes | Attach a short or long note to any node (formulas, examples); show/hide all notes |
| Styling | Teal and orange palette (teal `#00535C`, orange `#F09721`) with auto-lightening sub-branches; custom colour, 4 fonts, 3 sizes, bold/italic |
| View | Zoom in/out, centre on root, collapsible sidebar, branch panel |
| Export | PNG image, PDF, printable notes document, JSON data |

## How it works

- **Storage:** maps are saved as JSON in the browser's `localStorage` (key `atlas_maps_v1`). Nothing is uploaded, so data stays confidential.
- **Data model:** each map holds a list of nodes `{id, text, x, y, parent, root, color, font, size, bold, italic, note, collapsed}`; parent links form the tree.
- **Rendering:** nodes are absolutely positioned DOM elements on a zoomable canvas; connectors are drawn between parent and child.
- **Export:** PNG/PDF use `html2canvas` and `jsPDF` loaded from cdnjs (internet needed the first time only).

## Limitations

- Data lives in one browser on one device - clearing site data erases it. **Export JSON regularly** as a backup.
- No JSON import yet, no sync, no real-time collaboration.

## Use case: course planning

**Scenario:** You are designing the *Business Valuation* module of a course.

1. Create a map named "Valuation Module"; the centre node is the course topic.
2. Add main branches: *Income Approach*, *Market Approach*, *Asset Approach*, *Case Studies*.
3. Under *Income Approach*, branch to DCF, WACC, Terminal Value; attach notes holding formulas and worked examples.
4. Drag topics between branches as the sequence changes; collapse finished branches to focus.
5. Export the **notes document** as a lecture handout (PDF), the **PNG** for slides, and the **JSON** as a backup.

**Other uses:** client engagement scoping, valuation report outlines, exam revision maps, investment-thesis frameworks, meeting brainstorms.

## Sample map: Rule 11UA and Section 50C

The demo opens with a pre-built map (seeded once, on first open) covering why the rules exist, s.50C for the seller, s.56(2)(x) for the buyer, the Rule 11UA valuation method, a worked example and compliance tips. Click any node's note to read the detail. It uses Income-tax Act, 1961 numbering; under the Income-tax Act, 2025 (from 1 April 2026) s.50C is s.78, s.50CA is s.79 and s.56 is s.92. It is illustrative learning content, not tax advice.

## Licence

Proof of concept by Harshal Sopariwala. Free to use, study and adapt with attribution. Provided as is, without warranty.
