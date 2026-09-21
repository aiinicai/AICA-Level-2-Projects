# Capstone Overview

## Problem

Container tracking is fragmented across carrier websites. Operational users
manually repeat searches, interpret different layouts, and consolidate current
information into spreadsheets. This creates avoidable effort and inconsistent
exception visibility.

## Proposed solution

ContainerPulse accepts a two-column Excel list and uses a carrier registry to
route each row to the appropriate browser-automation connector. It standardizes
the available result into one dashboard and downloadable Excel output.

## Innovation

- Multi-carrier normalization without a paid carrier API.
- Modular dedicated connectors for proven carriers.
- A registry-based Setup Connector prototype that attempts to discover common
  public tracking controls and result fields.
- Responsible automation that stops at CAPTCHA, login, or access restrictions.
- An office-laptop-friendly design using existing Chrome/Edge.

## Use of AI coding tools

AI coding tools supported requirement refinement, modular architecture,
connector debugging, selector analysis, test generation, UI iteration, and
documentation. Development remained evidence-driven: live rendered pages,
saved diagnostic artifacts, regression tests, and user validation were used to
confirm behaviour. AI assistance accelerated development but did not replace
security controls or authorize access to restricted carrier data.

## Why no paid carrier API was required

MSC and Maersk provide public tracking pages that accept container numbers.
Playwright automates these browser interactions and extracts rendered fields
where the sites permit access. No carrier API key is used. This approach is
appropriate for a capstone proof of concept, but public-page availability and
carrier terms remain important operational constraints.

## Practical business benefit

ContainerPulse can reduce repetitive tracking work, provide one current-status
view, highlight failures requiring attention, and create a consistent Excel
output for operational review. The design is especially relevant to logistics,
procurement, imports, finance, and plant operations teams.

## Future scalability

The connector registry allows additional carriers to be introduced without
changing the Excel format or dashboard result schema. Future versions could add
dedicated connectors, secure access, compliant scheduling, enterprise storage,
notifications, and deployment infrastructure. These are intentionally outside
the present capstone scope.
