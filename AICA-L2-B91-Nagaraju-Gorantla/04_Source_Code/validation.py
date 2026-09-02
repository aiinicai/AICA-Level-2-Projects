import re
from dataclasses import dataclass
from typing import List


# ============================================================
# VALIDATION RESULT
# ============================================================

@dataclass
class ValidationIssue:
    severity: str
    field: str
    message: str


@dataclass
class ValidationResult:
    approved: bool
    issues: List[ValidationIssue]


# ============================================================
# SETTINGS
# ============================================================

MIN_AI_CONFIDENCE = 85
MIN_CHARGE_CONFIDENCE = 85


# ============================================================
# FORMAT CHECKS
# ============================================================

def valid_file_reference(value):

    if not value:
        return False

    pattern = r"^[A-Z]{2,6}-\d{3,6}-(?:\d{2}|\d{4})$"

    return bool(
        re.match(
            pattern,
            value.strip().upper()
        )
    )


def valid_container_number(value):

    if not value:
        return False

    pattern = r"^[A-Z]{4}\d{7}$"

    return bool(
        re.match(
            pattern,
            value.strip().upper()
        )
    )


# ============================================================
# AI RESULT VALIDATION
# ============================================================

def validate_ai_result(result):

    issues = []

    # --------------------------------------------------------
    # FILE REFERENCE
    # --------------------------------------------------------

    if not result.file_reference:

        issues.append(
            ValidationIssue(
                "HIGH",
                "File Reference",
                "File reference is missing."
            )
        )

    elif not valid_file_reference(
        result.file_reference
    ):

        issues.append(
            ValidationIssue(
                "HIGH",
                "File Reference",
                "File reference format is invalid."
            )
        )

    # --------------------------------------------------------
    # CONTAINER
    # --------------------------------------------------------

    if not result.containers:

        issues.append(
            ValidationIssue(
                "HIGH",
                "Container",
                "Container number is missing."
            )
        )

    else:

        for container in result.containers:

            if not valid_container_number(
                container
            ):

                issues.append(
                    ValidationIssue(
                        "HIGH",
                        "Container",
                        f"Invalid container format: {container}"
                    )
                )

    # --------------------------------------------------------
    # CHARGES
    # --------------------------------------------------------

    if not result.charges:

        issues.append(
            ValidationIssue(
                "HIGH",
                "Charges",
                "No positive additional charges were identified."
            )
        )

    seen_charges = set()

    for charge in result.charges:

        description = (
            charge.description
            or ""
        ).strip().upper()

        amount = charge.amount_usd

        # Zero / negative
        if amount <= 0:

            issues.append(
                ValidationIssue(
                    "HIGH",
                    description or "Charge",
                    "Charge amount must be greater than zero."
                )
            )

        # Low confidence
        if charge.confidence < MIN_CHARGE_CONFIDENCE:

            issues.append(
                ValidationIssue(
                    "MEDIUM",
                    description or "Charge",
                    (
                        "Charge confidence is below "
                        f"{MIN_CHARGE_CONFIDENCE}%."
                    )
                )
            )

        # Duplicate detection
        duplicate_key = (
            description,
            round(amount, 2)
        )

        if duplicate_key in seen_charges:

            issues.append(
                ValidationIssue(
                    "HIGH",
                    description or "Charge",
                    (
                        "Possible duplicate charge detected: "
                        f"USD {amount:,.2f}"
                    )
                )
            )

        seen_charges.add(
            duplicate_key
        )

    # --------------------------------------------------------
    # OVERALL AI CONFIDENCE
    # --------------------------------------------------------

    if result.overall_confidence < MIN_AI_CONFIDENCE:

        issues.append(
            ValidationIssue(
                "MEDIUM",
                "AI Confidence",
                (
                    "Overall AI confidence is below "
                    f"{MIN_AI_CONFIDENCE}%."
                )
            )
        )

    # --------------------------------------------------------
    # AI'S OWN REVIEW FLAG
    # --------------------------------------------------------

    if result.needs_review:

        reason = (
            result.review_reason
            or "AI identified uncertainty."
        )

        issues.append(
            ValidationIssue(
                "MEDIUM",
                "AI Review",
                reason
            )
        )

    # --------------------------------------------------------
    # FINAL DECISION
    # --------------------------------------------------------

    blocking_issues = [
        issue
        for issue in issues
        if issue.severity in (
            "HIGH",
            "MEDIUM"
        )
    ]

    approved = (
        len(blocking_issues) == 0
    )

    return ValidationResult(
        approved=approved,
        issues=issues
    )


# ============================================================
# DISPLAY HELPERS
# ============================================================

def validation_status(validation_result):

    if validation_result.approved:
        return "APPROVED"

    return "NEEDS REVIEW"


def validation_summary(validation_result):

    if validation_result.approved:

        return (
            "All validation controls passed. "
            "No human review required."
        )

    messages = []

    for issue in validation_result.issues:

        messages.append(
            f"[{issue.severity}] "
            f"{issue.field}: "
            f"{issue.message}"
        )

    return "\n".join(
        messages
    )