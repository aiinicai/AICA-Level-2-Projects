import re


GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
)


def is_missing(value):
    """Check whether an extracted value is missing."""

    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    return False


def validate_gstin(gstin):
    """Basic structural validation of an Indian GSTIN."""

    if is_missing(gstin):
        return None

    cleaned = str(gstin).strip().upper()

    return bool(
        GSTIN_PATTERN.fullmatch(cleaned)
    )


def validate_invoice(record, existing_records=None):
    """
    Review an extracted invoice and return validation results.

    This performs warning-level checks only.
    It does not alter the extracted invoice.
    """

    notes = []

    # ----------------------------------------------
    # IMPORTANT FIELDS
    # ----------------------------------------------

    if is_missing(record.get("Vendor Name")):
        notes.append("Vendor name missing")

    if is_missing(record.get("Invoice Number")):
        notes.append("Invoice number missing")

    if is_missing(record.get("Invoice Date")):
        notes.append("Invoice date missing")

    if is_missing(record.get("Total Amount")):
        notes.append("Total amount missing")

    # ----------------------------------------------
    # GSTIN FORMAT
    # ----------------------------------------------

    gstin = record.get("GSTIN")

    gstin_result = validate_gstin(gstin)

    if gstin_result is False:
        notes.append("GSTIN format requires review")

    # ----------------------------------------------
    # AMOUNT RECONCILIATION
    # ----------------------------------------------

    taxable = record.get("Taxable Amount")
    cgst = record.get("CGST")
    sgst = record.get("SGST")
    igst = record.get("IGST")
    total = record.get("Total Amount")

    if taxable is not None and total is not None:

        try:
            calculated_total = float(taxable)

            for tax in [cgst, sgst, igst]:
                if tax is not None:
                    calculated_total += float(tax)

            difference = abs(
                calculated_total - float(total)
            )

            if difference > 1:
                notes.append(
                    "Taxable amount + GST does not match "
                    "invoice total; check discounts, charges, "
                    "rounding or extraction"
                )

        except (TypeError, ValueError):
            notes.append(
                "One or more amount fields require review"
            )

    # ----------------------------------------------
    # DUPLICATE CHECK
    # ----------------------------------------------

    if existing_records:

        vendor = str(
            record.get("Vendor Name") or ""
        ).strip().lower()

        invoice_number = str(
            record.get("Invoice Number") or ""
        ).strip().lower()

        if vendor and invoice_number:

            for old_record in existing_records:

                old_vendor = str(
                    old_record.get("Vendor Name") or ""
                ).strip().lower()

                old_invoice_number = str(
                    old_record.get("Invoice Number") or ""
                ).strip().lower()

                if (
                    vendor == old_vendor
                    and invoice_number == old_invoice_number
                ):
                    notes.append(
                        "Possible duplicate invoice"
                    )
                    break

    # ----------------------------------------------
    # FINAL STATUS
    # ----------------------------------------------

    if notes:
        status = "Review Required"
    else:
        status = "OK"

    return {
        "Validation Status": status,
        "Validation Notes": "; ".join(notes)
    }