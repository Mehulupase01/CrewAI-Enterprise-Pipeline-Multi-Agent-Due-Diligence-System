from __future__ import annotations

import io

from openpyxl import Workbook


def build_financial_workbook_bytes(*, bridge_variant: str = "audit") -> bytes:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Financial Summary"

    summary.append(["Particulars", "FY22", "FY23", "FY24", "FY25"])
    summary.append(["Revenue from Operations", 100.0, 120.0, 150.0, 170.0])
    summary.append(["Gross Profit", 50.0, 61.0, 78.0, 88.0])
    summary.append(["EBITDA", 12.0, 16.0, 20.0, 22.3])
    summary.append(["Profit After Tax", 4.0, 6.0, 8.0, 9.0])
    summary.append(["Operating Cash Flow", 8.0, 12.0, 13.0, -3.0])
    summary.append(["Net Debt", 40.0, 38.0, 35.0, 32.0])
    summary.append(["Interest Expense", 4.0, 4.0, 5.0, 4.5])
    summary.append(["Working Capital", 18.0, 20.0, 24.0, 28.0])
    summary.append(["Total Assets", 70.0, 82.0, 95.0, 105.0])
    summary.append(["Shareholder Equity", 22.0, 28.0, 34.0, 38.0])
    summary.append(["Top 3 Customer Concentration", "48%", "52%", "58%", "72%"])
    summary.append(["Q4 Revenue Share", "23%", "24%", "27%", "45%"])
    summary.append(["One-time legal cost", None, None, None, -2.5])

    bridge = workbook.create_sheet("Quarterly Bridge")
    bridge.append(["Bridge Variant", bridge_variant])
    bridge.append(["Particulars", "Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25"])
    bridge.append(["Revenue", 38.0, 41.0, 33.5, 57.5])
    bridge.append(["EBITDA", 4.5, 5.2, 4.1, 8.5])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
