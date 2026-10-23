
"""Excel multi-sheet export helpers using XlsxWriter."""
from __future__ import annotations

import io
import pandas as pd


def create_working_paper(
    daybook: pd.DataFrame,
    summary_df: pd.DataFrame,
    exceptions_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    variance_df: pd.DataFrame | None,
    parameters: list[dict],
) -> bytes:
    """Create a single Excel file with multiple formatted sheets."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Formats
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#007f75",
            "font_color": "white",
            "border": 1,
        })

        num_fmt = workbook.add_format({
            "num_format": "#,##0.00",
            "border": 1,
        })

        text_fmt = workbook.add_format({"border": 1})

        def write_sheet(df: pd.DataFrame | None, name: str) -> None:
            """Write a DataFrame to Excel and safely adjust column widths."""
            if df is None or df.empty:
                return

            # Excel worksheet names must not exceed 31 characters.
            df.to_excel(writer, sheet_name=name, index=False)
            worksheet = writer.sheets[name]

            # Format headers and adjust column widths.
            for col_num, column in enumerate(df.columns):
                column_name = str(column)

                worksheet.write(0, col_num, column_name, header_fmt)

                # Start with the header width.
                max_len = len(column_name)

                # Convert values to strings before measuring their lengths.
                # Missing values are treated as empty cells for sizing.
                for cell_value in df[column].tolist():
                    if pd.isna(cell_value):
                        cell_len = 0
                    else:
                        cell_len = len(str(cell_value))

                    max_len = max(max_len, cell_len)

                # Add padding and cap the width to avoid oversized columns.
                column_width = min(max_len + 2, 50)

                # Preserve numeric formatting for numeric columns.
                if pd.api.types.is_numeric_dtype(df[column].dtype):
                    cell_format = num_fmt
                else:
                    cell_format = text_fmt

                worksheet.set_column(
                    col_num,
                    col_num,
                    column_width,
                    cell_format,
                )

        # 1. Summary & Parameters
        params_df = pd.DataFrame(parameters)
        write_sheet(params_df, "Audit Summary")

        # 2. Selected Samples
        write_sheet(samples_df, "Selected Samples")

        # 3. Exception Results
        write_sheet(exceptions_df, "Exceptions Found")

        # 4. Variance Analysis
        if variance_df is not None:
            write_sheet(variance_df, "Variance Analysis")

        # 5. Full Cleaned Day Book (limited to 5,000 rows)
        if daybook is not None:
            write_sheet(
                daybook.head(5000),
                "Day Book (Top 5k rows)",
            )

    return output.getvalue()
