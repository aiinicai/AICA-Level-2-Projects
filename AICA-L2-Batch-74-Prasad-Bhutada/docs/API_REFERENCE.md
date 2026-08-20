# REST API Reference

Base URL: `http://<server>:4000/api`

All responses follow `{ success: boolean, data?: any, message?: string }`. Routes marked 🔒 require an `Authorization: Bearer <token>` header, obtained from `POST /settings/unlock`.

## Templates
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/templates?search=&categoryId=&status=` | – | List templates (default status=Active) |
| GET | `/templates/:id` | – | Get one template + placeholders |
| GET | `/templates/:id/preview` | – | Word-like HTML preview |
| GET | `/templates/:id/download` | – | Download the master .docx |
| POST | `/templates/import` | 🔒 | Multipart: `files[]`, `categoryId`, `keywords`, `description` |
| POST | `/templates/:id/replace` | 🔒 | Multipart: `file` |
| PATCH | `/templates/:id/rename` | 🔒 | `{ name }` |
| GET | `/templates/:id/dependencies` | 🔒 | Dependency check before delete |
| DELETE | `/templates/:id` | 🔒 | Soft delete (Recycle Bin) |
| POST | `/templates/:id/restore` | 🔒 | Restore from Recycle Bin |
| GET | `/templates/recycle-bin/list` | 🔒 | List deleted templates |

## Placeholder Mapping
| Method | Path | Description |
|---|---|---|
| GET | `/placeholder-mappings` | All known placeholders + current mapping + templates using each |
| GET | `/placeholder-mappings/available-fields` | System + custom Client Master fields |
| PUT | `/placeholder-mappings/:placeholderId` | `{ clientFieldKey }` |
| DELETE | `/placeholder-mappings/:placeholderId` | Remove mapping |

## Categories
| Method | Path | Description |
|---|---|---|
| GET | `/categories` | List |
| POST | `/categories` | `{ name }` |
| DELETE | `/categories/:id` | Delete (blocked if in use or system default) |

## Clients
| Method | Path | Description |
|---|---|---|
| GET | `/clients?search=` | List/search |
| GET | `/clients/:id` | Get one |
| POST | `/clients` | Create |
| PUT | `/clients/:id` | Update |
| DELETE | `/clients/:id` | Delete |
| GET | `/clients/fields` | List custom field definitions |
| POST | `/clients/fields` | `{ fieldKey, label, fieldType, isRequired }` |
| GET | `/clients/export` | Download Excel export |
| POST | `/clients/import` | Multipart `file` (.xlsx) bulk import |

## Generation
| Method | Path | Description |
|---|---|---|
| POST | `/generation/merge-placeholders` | `{ templateIds }` → merged/deduped placeholders with usage |
| POST | `/generation/autofill` | `{ clientId, templateIds }` → mapped values from Client Master |
| POST | `/generation/validate` | `{ templateIds, values }` → validation errors, if any |
| POST | `/generation/generate` | Multipart: `clientId?, clientName, templateIds (JSON), values (JSON), outputFormats (JSON), <imagePlaceholderName> files` |
| GET | `/generation/download?dir=&file=` | Download one generated file |
| GET | `/generation/download?dir=&all=true&zipName=` | Download all files in a batch as ZIP |

## History
| Method | Path | Description |
|---|---|---|
| GET | `/history?clientId=&templateId=&dateFrom=&dateTo=` | Filtered list |
| GET | `/history/export?...same filters` | Excel export |

## Settings
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/settings/unlock` | – | `{ password }` → `{ token }` (this IS the login step) |
| GET | `/settings` | 🔒 | All settings (password hash never returned) |
| PUT | `/settings` | 🔒 | Partial update, `{ key: value, ... }` |
| POST | `/settings/change-password` | 🔒 | `{ newPassword }` |

## Backup
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/backup/run` | 🔒 | Run an immediate backup |
| POST | `/backup/restore` | 🔒 | Multipart `file` (.zip) restore |

## Health
| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{ success: true, status: 'ok' }` — for uptime checks |
