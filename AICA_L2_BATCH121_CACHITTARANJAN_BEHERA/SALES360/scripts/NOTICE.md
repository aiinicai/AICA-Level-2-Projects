# Third-party software inventory

Version 0.1.0; 27 October 2026. Review distributed licenses before a company release. Lockfiles specify transitive dependencies; this inventory does not replace their notices.

| Software | Selected version | License family / distribution note |
|---|---|---|
| .NET / ASP.NET Core | 10; local SDK 10.0.403 | MIT components; official SDK/runtime notices apply |
| PostgreSQL | 17.6 local portable test server | PostgreSQL License; not included in app archive |
| Npgsql | 10.0.0 | PostgreSQL License |
| ClosedXML | 0.105.0 | MIT; OpenXML/ExcelNumberFormat dependencies in lockfile |
| React / React DOM | 19.2.0 | MIT |
| TypeScript | 5.9.3 | Apache-2.0; build tool |
| Vite | 7.1.12 | MIT; build tool |
| lucide-react | 0.468.0 | ISC |
| ReportLab | 4.4.9 in configured Python | BSD-style; runtime prerequisite |
| pypdf | 6.10.0 | BSD-3-Clause; QA tool |
| pypdfium2 | 5.14.0 | Apache-2.0/BSD with PDFium third-party notices; QA tool |
| arabic-reshaper | 3.0.0 | Preserve included package dist-info/license notices |
| python-bidi | 0.6.7 | Preserve included package dist-info/license notices |
| Windows Arial fonts | Host OS | Proprietary licensed OS fonts; embedded by renderer as permitted by font flags; font files not copied into app archive |

App source ownership/license is left for the company to choose. No proprietary ERP SDK, ASP license, Microsoft consent or signing certificate is included. Dependency vulnerability and license policy scanning must run before production release; no clean security scan has been claimed.
