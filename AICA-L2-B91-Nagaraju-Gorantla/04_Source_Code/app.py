import tkinter as tk
from tkinter import ttk, messagebox
import threading

from rule_extractor import extract_email
from ai_extractor import extract_email_with_ai
from validation import (
    validate_ai_result,
    validation_status,
    validation_summary,
)
from test_cases import TEST_CASES

SAMPLE_EMAIL = """Subject: Additional Charges - SIM-0706-26 - ASLU7042918

Dear Sir,

Please find the additional charges for the container:

1. Ferry Charges - USD 316
2. Demurrage Charges - USD 1790

Regards,
Demo User
"""


class CapstoneApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "AI-Powered Invoice Extras Extraction"
        )

        self.root.geometry(
            "1000x740"
        )

        self.root.resizable(
            True,
            True
        )

        # ----------------------------------------------------
        # CURRENT STATE
        # ----------------------------------------------------

        self.current_ai_result = None
        self.current_validation = None
        self.human_decision = None

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = tk.Label(
            root,
            text="AI-Powered Invoice Extras Extraction",
            font=("Segoe UI", 20, "bold")
        )

        title.pack(
            pady=(18, 4)
        )

        subtitle = tk.Label(
            root,
            text=(
                "AICA Level 2 Capstone Project "
                "- Hybrid Rule + AI + Human Validation"
            ),
            font=("Segoe UI", 11)
        )

        subtitle.pack(
            pady=(0, 15)
        )

        # ----------------------------------------------------
        # MAIN FRAME
        # ----------------------------------------------------

        main_frame = tk.Frame(
            root
        )

        main_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5
        )

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------
        # ----------------------------------------------------
        # CAPSTONE TEST CASE SELECTOR
        # ----------------------------------------------------

        test_frame = tk.Frame(
            main_frame
        )

        test_frame.pack(
            fill="x",
            pady=(5, 12)
        )

        test_label = tk.Label(
            test_frame,
            text="Capstone Test Case:",
            font=("Segoe UI", 10, "bold")
        )

        test_label.pack(
            side="left",
            padx=(0, 8)
        )

        self.test_case_var = tk.StringVar()

        self.test_case_combo = ttk.Combobox(
            test_frame,
            textvariable=self.test_case_var,
            state="readonly",
            width=42
        )

        self.test_case_combo["values"] = [
            f"{test['id']} - {test['name']}"
            for test in TEST_CASES
        ]

        self.test_case_combo.pack(
            side="left",
            padx=5
        )

        self.test_case_combo.current(0)

        self.load_test_button = tk.Button(
            test_frame,
            text="Load Test",
            width=12,
            command=self.load_test_case
        )

        self.load_test_button.pack(
            side="left",
            padx=8
        )

        self.expected_label = tk.Label(
            test_frame,
            text="",
            font=("Segoe UI", 9)
        )

        self.expected_label.pack(
            side="left",
            padx=10
        )
        email_label = tk.Label(
            main_frame,
            text="Email / Unstructured Input",
            font=("Segoe UI", 11, "bold")
        )

        email_label.pack(
            anchor="w"
        )

        self.email_box = tk.Text(
            main_frame,
            height=12,
            font=("Consolas", 10),
            wrap="word"
        )

        self.email_box.pack(
            fill="x",
            pady=(5, 12)
        )

        self.email_box.insert(
            "1.0",
            SAMPLE_EMAIL
        )

        # ----------------------------------------------------
        # EXTRACTION BUTTONS
        # ----------------------------------------------------

        button_frame = tk.Frame(
            main_frame
        )

        button_frame.pack(
            pady=5
        )

        self.rule_button = tk.Button(
            button_frame,
            text="Rule Extraction",
            width=18,
            command=self.rule_extract
        )

        self.rule_button.grid(
            row=0,
            column=0,
            padx=6
        )

        self.ai_button = tk.Button(
            button_frame,
            text="AI Extraction",
            width=18,
            command=self.start_ai_extract
        )

        self.ai_button.grid(
            row=0,
            column=1,
            padx=6
        )

        self.review_button = tk.Button(
            button_frame,
            text="Needs Review",
            width=18,
            command=self.show_review_details
        )

        self.review_button.grid(
            row=0,
            column=2,
            padx=6
        )

        self.clear_button = tk.Button(
            button_frame,
            text="Clear",
            width=18,
            command=self.clear_all
        )

        self.clear_button.grid(
            row=0,
            column=3,
            padx=6
        )

        # ----------------------------------------------------
        # RESULT TABLE
        # ----------------------------------------------------

        result_label = tk.Label(
            main_frame,
            text="Structured Extraction Result",
            font=("Segoe UI", 11, "bold")
        )

        result_label.pack(
            anchor="w",
            pady=(15, 5)
        )

        columns = (
            "field",
            "value",
            "confidence",
            "status"
        )

        self.tree = ttk.Treeview(
            main_frame,
            columns=columns,
            show="headings",
            height=12
        )

        self.tree.heading(
            "field",
            text="Field"
        )

        self.tree.heading(
            "value",
            text="Extracted Value"
        )

        self.tree.heading(
            "confidence",
            text="Confidence"
        )

        self.tree.heading(
            "status",
            text="Status"
        )

        self.tree.column(
            "field",
            width=190
        )

        self.tree.column(
            "value",
            width=390
        )

        self.tree.column(
            "confidence",
            width=120
        )

        self.tree.column(
            "status",
            width=180
        )

        self.tree.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # HUMAN REVIEW BUTTONS
        # ----------------------------------------------------

        decision_frame = tk.Frame(
            main_frame
        )

        decision_frame.pack(
            pady=12
        )

        self.approve_button = tk.Button(
            decision_frame,
            text="APPROVE",
            width=16,
            state="disabled",
            command=self.approve_result
        )

        self.approve_button.grid(
            row=0,
            column=0,
            padx=10
        )

        self.reject_button = tk.Button(
            decision_frame,
            text="REJECT",
            width=16,
            state="disabled",
            command=self.reject_result
        )

        self.reject_button.grid(
            row=0,
            column=1,
            padx=10
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status_label = tk.Label(
            main_frame,
            text="Status: Ready",
            font=("Segoe UI", 10, "bold")
        )

        self.status_label.pack(
            pady=(5, 3)
        )

        self.control_label = tk.Label(
            main_frame,
            text=(
                "Control: AI recommendations are subject "
                "to validation and human review."
            ),
            font=("Segoe UI", 9)
        )

        self.control_label.pack(
            pady=(0, 8)
        )

    # ========================================================
    # LOAD CAPSTONE TEST CASE
    # ========================================================

    def load_test_case(self):

        selected_index = self.test_case_combo.current()

        if selected_index < 0:
            return

        test = TEST_CASES[
            selected_index
        ]

        self.email_box.delete(
            "1.0",
            "end"
        )

        self.email_box.insert(
            "1.0",
            test["email"].strip()
        )

        expected = test[
            "expected"
        ]

        expected_review = (
            "YES"
            if expected["review"]
            else "NO"
        )

        self.expected_label.config(
            text=(
                f"Expected: USD "
                f"{expected['total']:,.2f} | "
                f"Review: {expected_review}"
            )
        )

        self.clear_tree()
        self.reset_decision()

        self.status_label.config(
            text=(
                f"Status: {test['id']} loaded - "
                f"{test['name']}"
            )
        )
    # ========================================================
    # UTILITIES
    # ========================================================

    def clear_tree(self):

        for item in self.tree.get_children():
            self.tree.delete(item)


    def reset_decision(self):

        self.current_ai_result = None
        self.current_validation = None
        self.human_decision = None

        self.approve_button.config(
            state="disabled"
        )

        self.reject_button.config(
            state="disabled"
        )


    def clear_all(self):

        self.clear_tree()
        self.reset_decision()

        self.status_label.config(
            text="Status: Ready"
        )


    # ========================================================
    # RULE EXTRACTION
    # ========================================================

    def rule_extract(self):

        self.clear_tree()
        self.reset_decision()

        email_text = self.email_box.get(
            "1.0",
            "end"
        ).strip()

        if not email_text:

            messagebox.showwarning(
                "No Input",
                "Please enter or paste an email first."
            )

            return

        try:

            result = extract_email(
                email_text
            )

        except Exception as error:

            messagebox.showerror(
                "Rule Extraction Error",
                str(error)
            )

            self.status_label.config(
                text="Status: Rule extraction failed"
            )

            return

        # ----------------------------------------------------
        # FILE REF
        # ----------------------------------------------------

        file_ref = result.get(
            "file_reference"
        )

        self.tree.insert(
            "",
            "end",
            values=(
                "File Reference",
                file_ref or "Not Found",
                "100%" if file_ref else "0%",
                "Validated" if file_ref else "Needs Review"
            )
        )

        # ----------------------------------------------------
        # CONTAINERS
        # ----------------------------------------------------

        containers = result.get(
            "containers",
            []
        )

        if containers:

            for container in containers:

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        "Container",
                        container,
                        "100%",
                        "Validated"
                    )
                )

        else:

            self.tree.insert(
                "",
                "end",
                values=(
                    "Container",
                    "Not Found",
                    "0%",
                    "Needs Review"
                )
            )

        # ----------------------------------------------------
        # CHARGES
        # ----------------------------------------------------

        charges = result.get(
            "charges",
            []
        )

        if charges:

            for charge in charges:

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        charge["description"],
                        f"USD {charge['amount']:,.2f}",
                        "98%",
                        "Rule Extracted"
                    )
                )

        else:

            self.tree.insert(
                "",
                "end",
                values=(
                    "Extra Charges",
                    "None Found",
                    "0%",
                    "Needs Review"
                )
            )

        # ----------------------------------------------------
        # TOTAL
        # ----------------------------------------------------

        total = result.get(
            "total",
            0
        )

        self.tree.insert(
            "",
            "end",
            values=(
                "Total Extras",
                f"USD {total:,.2f}",
                "100%",
                "Calculated"
            )
        )

        if (
            file_ref
            and containers
            and charges
        ):

            self.status_label.config(
                text="Status: Rule extraction successful"
            )

        else:

            self.status_label.config(
                text=(
                    "Status: Rule extraction completed "
                    "- review required"
                )
            )


    # ========================================================
    # START AI
    # ========================================================

    def start_ai_extract(self):

        email_text = self.email_box.get(
            "1.0",
            "end"
        ).strip()

        if not email_text:

            messagebox.showwarning(
                "No Input",
                "Please enter or paste an email first."
            )

            return

        self.clear_tree()
        self.reset_decision()

        self.ai_button.config(
            state="disabled",
            text="AI Working..."
        )

        self.status_label.config(
            text="Status: AI extraction in progress..."
        )

        thread = threading.Thread(
            target=self.run_ai_extract,
            args=(email_text,),
            daemon=True
        )

        thread.start()


    # ========================================================
    # AI EXTRACTION
    # ========================================================

    def run_ai_extract(
        self,
        email_text
    ):

        try:

            result = extract_email_with_ai(
                email_text
            )

            validation = validate_ai_result(
                result
            )

            self.root.after(
                0,
                lambda: self.show_ai_result(
                    result,
                    validation
                )
            )

        except Exception as error:

            # Capture the exception text immediately.
            # Python clears exception variables after the except block,
            # so passing str(error) directly inside a delayed Tkinter
            # lambda can cause a NameError.
            error_text = str(error)

            self.root.after(
                0,
                lambda error_text=error_text: self.show_ai_error(
                    error_text
                )
            )


    # ========================================================
    # DISPLAY AI RESULT
    # ========================================================

    def show_ai_result(
        self,
        result,
        validation
    ):

        self.ai_button.config(
            state="normal",
            text="AI Extraction"
        )

        self.clear_tree()

        self.current_ai_result = result
        self.current_validation = validation
        self.human_decision = None

        # ----------------------------------------------------
        # FILE REF
        # ----------------------------------------------------

        self.tree.insert(
            "",
            "end",
            values=(
                "File Reference",
                result.file_reference or "Not Found",
                f"{result.overall_confidence}%",
                (
                    "AI Confirmed"
                    if result.file_reference
                    else "Needs Review"
                )
            )
        )

        # ----------------------------------------------------
        # CONTAINERS
        # ----------------------------------------------------

        if result.containers:

            for container in result.containers:

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        "Container",
                        container,
                        f"{result.overall_confidence}%",
                        "AI Confirmed"
                    )
                )

        else:

            self.tree.insert(
                "",
                "end",
                values=(
                    "Container",
                    "Not Found",
                    f"{result.overall_confidence}%",
                    "Needs Review"
                )
            )

        # ----------------------------------------------------
        # CHARGES
        # ----------------------------------------------------

        total = 0

        if result.charges:

            for charge in result.charges:

                total += charge.amount_usd

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        charge.description.upper(),
                        f"USD {charge.amount_usd:,.2f}",
                        f"{charge.confidence}%",
                        "AI Extracted"
                    )
                )

        else:

            self.tree.insert(
                "",
                "end",
                values=(
                    "Extra Charges",
                    "None Found",
                    f"{result.overall_confidence}%",
                    "Needs Review"
                )
            )

        # ----------------------------------------------------
        # TOTAL
        # ----------------------------------------------------

        self.tree.insert(
            "",
            "end",
            values=(
                "Total Extras",
                f"USD {total:,.2f}",
                "100%",
                "Calculated"
            )
        )

        # ----------------------------------------------------
        # VALIDATION STATUS
        # ----------------------------------------------------

        status = validation_status(
            validation
        )

        self.tree.insert(
            "",
            "end",
            values=(
                "Validation Status",
                status,
                "-",
                "Control Result"
            )
        )

        # ----------------------------------------------------
        # VALIDATION ISSUES
        # ----------------------------------------------------

        for issue in validation.issues:

            self.tree.insert(
                "",
                "end",
                values=(
                    f"{issue.severity} Review",
                    issue.message,
                    "-",
                    "Needs Review"
                )
            )

        # ----------------------------------------------------
        # FINAL SYSTEM STATUS
        # ----------------------------------------------------

        if validation.approved:

            self.status_label.config(
                text=(
                    "Status: Validation passed - "
                    "ready for human approval"
                )
            )

        else:

            self.status_label.config(
                text=(
                    "Status: NEEDS REVIEW - "
                    "human decision required"
                )
            )

        # Human reviewer can approve or reject either way.
        self.approve_button.config(
            state="normal"
        )

        self.reject_button.config(
            state="normal"
        )


    # ========================================================
    # AI ERROR
    # ========================================================

    def show_ai_error(
        self,
        error_text
    ):

        self.ai_button.config(
            state="normal",
            text="AI Extraction"
        )

        self.status_label.config(
            text="Status: AI extraction failed"
        )

        # Give clean, presentation-friendly messages for common
        # Gemini service conditions instead of exposing raw API errors.
        error_upper = (error_text or "").upper()

        if (
            "429" in error_upper
            or "RESOURCE_EXHAUSTED" in error_upper
            or "QUOTA" in error_upper
            or "RATE LIMIT" in error_upper
        ):
            title = "Gemini Daily Quota Reached"
            friendly_message = (
                "Gemini AI request quota has been reached for the current account/project.\n\n"
                "Please retry after the quota resets or when more quota is available.\n\n"
                "Rule Extraction remains available because it runs locally."
            )

        elif (
            "503" in error_upper
            or "UNAVAILABLE" in error_upper
            or "HIGH DEMAND" in error_upper
        ):
            title = "Gemini Temporarily Busy"
            friendly_message = (
                "Gemini AI is temporarily busy or unavailable due to high demand.\n\n"
                "Please wait a short while and click AI Extraction again.\n\n"
                "Rule Extraction remains available because it runs locally."
            )

        else:
            title = "AI Extraction Error"
            friendly_message = (
                error_text[:1500]
                if error_text
                else "Unknown AI extraction error."
            )

        messagebox.showerror(
            title,
            friendly_message
        )


    # ========================================================
    # REVIEW DETAILS
    # ========================================================

    def show_review_details(self):

        if not self.current_validation:

            messagebox.showinfo(
                "Needs Review",
                "Run AI Extraction first."
            )

            return

        summary = validation_summary(
            self.current_validation
        )

        messagebox.showinfo(
            "Validation Review",
            summary
        )


    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    def approve_result(self):

        if not self.current_ai_result:

            messagebox.showwarning(
                "No AI Result",
                "Run AI Extraction first."
            )

            return

        # If validation has issues, require explicit confirmation.
        if (
            self.current_validation
            and not self.current_validation.approved
        ):

            confirm = messagebox.askyesno(
                "Approve Exception",
                (
                    "Validation has identified issues.\n\n"
                    "Do you still want to approve this result "
                    "after human review?"
                )
            )

            if not confirm:
                return

        self.human_decision = "APPROVED"

        self.tree.insert(
            "",
            "end",
            values=(
                "Human Decision",
                "APPROVED",
                "-",
                "Final Decision"
            )
        )

        self.status_label.config(
            text="Status: APPROVED by human reviewer"
        )

        self.approve_button.config(
            state="disabled"
        )

        self.reject_button.config(
            state="disabled"
        )

        messagebox.showinfo(
            "Approved",
            "The extracted result has been approved by the human reviewer."
        )


    # ========================================================
    # HUMAN REJECTION
    # ========================================================

    def reject_result(self):

        if not self.current_ai_result:

            messagebox.showwarning(
                "No AI Result",
                "Run AI Extraction first."
            )

            return

        confirm = messagebox.askyesno(
            "Reject Result",
            "Reject this AI extraction result?"
        )

        if not confirm:
            return

        self.human_decision = "REJECTED"

        self.tree.insert(
            "",
            "end",
            values=(
                "Human Decision",
                "REJECTED",
                "-",
                "Final Decision"
            )
        )

        self.status_label.config(
            text="Status: REJECTED by human reviewer"
        )

        self.approve_button.config(
            state="disabled"
        )

        self.reject_button.config(
            state="disabled"
        )

        messagebox.showinfo(
            "Rejected",
            (
                "The AI result was rejected.\n\n"
                "The record should be corrected or reviewed manually."
            )
        )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = CapstoneApp(
        root
    )

    root.mainloop()