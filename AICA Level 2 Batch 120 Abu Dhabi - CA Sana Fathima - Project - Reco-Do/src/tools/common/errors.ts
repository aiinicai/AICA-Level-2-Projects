// Errors thrown by every tool engine. The UI shows `message` to the user as is.

export type ToolErrorCode =
  /** The PDF needs a password to open. */
  | 'password-protected'
  /** The PDF opens without a password but is protected against editing (owner password / permissions). */
  | 'edit-protected'
  /** The file is not a PDF, or it is damaged. */
  | 'invalid-pdf'
  /** A non-PDF input (sheet, table) is unusable. */
  | 'invalid-file'
  /** An option value is wrong, e.g. a page range that does not exist. */
  | 'invalid-option'
  /** The tool ran but found nothing to output. */
  | 'empty-result'
  /** OCR was needed but could not be started or failed on a page. */
  | 'ocr-failed'
  /** The user cancelled (AbortSignal). */
  | 'cancelled'
  /** Anything else; message stays plain English. */
  | 'unexpected'

export class ToolError extends Error {
  readonly code: ToolErrorCode
  /** Technical detail for logs; never shown to the user. */
  readonly detail?: string

  constructor(code: ToolErrorCode, message: string, detail?: string) {
    super(message)
    this.name = 'ToolError'
    this.code = code
    this.detail = detail
  }
}

export const PASSWORD_MESSAGE = 'This PDF is password-protected. Remove the password first, then try again.'
export const EDIT_PROTECTED_MESSAGE =
  'This PDF is protected against editing, so its pages cannot be merged or split. Open it in a PDF reader, print it to a new PDF (or remove the protection), then try again.'
export const INVALID_PDF_MESSAGE = 'This file is not a valid PDF, or it is damaged. Try opening it in a PDF reader and saving a fresh copy.'
export const CANCELLED_MESSAGE = 'Cancelled.'

export function isToolError(e: unknown): e is ToolError {
  return e instanceof ToolError
}

export function passwordError(): ToolError {
  return new ToolError('password-protected', PASSWORD_MESSAGE)
}

/** Throws a `cancelled` ToolError when the signal has been aborted. */
export function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new ToolError('cancelled', CANCELLED_MESSAGE)
}

function errorText(e: unknown): string {
  if (e instanceof Error) return `${e.name}: ${e.message}`
  return String(e)
}

/**
 * Converts any error raised while opening a PDF (pdf.js or pdf-lib) into a ToolError
 * with a plain-English message. ToolErrors pass through unchanged.
 */
export function toPdfOpenError(e: unknown): ToolError {
  if (e instanceof ToolError) return e
  const name = e instanceof Error ? e.name : ''
  const text = errorText(e)
  if (name === 'PasswordException' || name === 'EncryptedPDFError' || /encrypt|password/i.test(text)) return passwordError()
  return new ToolError('invalid-pdf', INVALID_PDF_MESSAGE, text)
}

/** Wraps an unknown failure in a ToolError, keeping ToolErrors as they are. */
export function toToolError(e: unknown, message = 'Something went wrong while processing the file. Please try again.'): ToolError {
  if (e instanceof ToolError) return e
  return new ToolError('unexpected', message, errorText(e))
}
