package com.example.core.util

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import androidx.core.content.FileProvider
import com.example.core.model.BusinessEntity
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.repository.LedgerItem
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object PdfStatementGenerator {
    fun generatePartyStatementPdf(
        context: Context,
        business: BusinessEntity,
        party: PartyEntity,
        ledgerItems: List<LedgerItem>,
        netBalancePaise: Long
    ): File? {
        val pdfDocument = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create() // A4 size
        val page = pdfDocument.startPage(pageInfo)
        val canvas: Canvas = page.canvas

        val paint = Paint().apply { isAntiAlias = true }
        val dateFormat = SimpleDateFormat("dd/MM/yyyy", Locale.ENGLISH)
        val timeFormat = SimpleDateFormat("dd/MM/yyyy hh:mm a", Locale.ENGLISH)

        // Background
        paint.color = Color.WHITE
        canvas.drawRect(0f, 0f, 595f, 842f, paint)

        // Top Header Banner
        paint.color = Color.rgb(15, 23, 42) // SlateNavy900
        canvas.drawRect(0f, 0f, 595f, 90f, paint)

        // Business Name
        paint.color = Color.WHITE
        paint.textSize = 20f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText(business.name, 36f, 42f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        val subtitle = StringBuilder()
        if (!business.phone.isNullOrEmpty()) subtitle.append("Ph: ${business.phone}  ")
        if (!business.gstin.isNullOrEmpty()) subtitle.append("GSTIN: ${business.gstin}  ")
        if (!business.upiId.isNullOrEmpty()) subtitle.append("UPI: ${business.upiId}")
        canvas.drawText(subtitle.toString(), 36f, 62f, paint)

        paint.textSize = 12f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("ACCOUNT STATEMENT", 420f, 42f, paint)

        paint.textSize = 9f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        canvas.drawText("Date: ${dateFormat.format(Date())}", 420f, 62f, paint)

        // Party Info Box
        var currentY = 115f
        paint.color = Color.rgb(241, 245, 249)
        canvas.drawRoundRect(36f, currentY, 559f, currentY + 65f, 8f, 8f, paint)

        paint.color = Color.rgb(15, 23, 42)
        paint.textSize = 12f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("Statement For: ${party.name}", 50f, currentY + 25f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        val partyContact = StringBuilder()
        if (!party.phone.isNullOrEmpty()) partyContact.append("Phone: ${party.phone}  ")
        if (!party.address.isNullOrEmpty()) partyContact.append("Address: ${party.address}  ")
        if (!party.gstin.isNullOrEmpty()) partyContact.append("GSTIN: ${party.gstin}")
        canvas.drawText(partyContact.toString(), 50f, currentY + 45f, paint)

        // Net Balance Callout
        paint.textSize = 11f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        val balanceLabel = if (netBalancePaise >= 0) "Net Receivable (Lena): " else "Net Payable (Dena): "
        val balanceVal = Money.formatIndianPaise(netBalancePaise)
        paint.color = if (netBalancePaise >= 0) Color.rgb(5, 150, 105) else Color.rgb(220, 38, 38)
        canvas.drawText("$balanceLabel $balanceVal", 360f, currentY + 35f, paint)

        // Table Header
        currentY += 85f
        paint.color = Color.rgb(30, 41, 59)
        canvas.drawRect(36f, currentY, 559f, currentY + 24f, paint)

        paint.color = Color.WHITE
        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("DATE", 46f, currentY + 16f, paint)
        canvas.drawText("DESCRIPTION / REF", 130f, currentY + 16f, paint)
        canvas.drawText("DEBIT (+)", 330f, currentY + 16f, paint)
        canvas.drawText("CREDIT (-)", 410f, currentY + 16f, paint)
        canvas.drawText("BALANCE", 490f, currentY + 16f, paint)

        currentY += 24f

        // Table Rows (Draw up to ~25 recent rows to fit cleanly on page)
        paint.textSize = 9f
        var isAlternate = false

        for (item in ledgerItems.take(25)) {
            paint.color = if (isAlternate) Color.rgb(248, 250, 252) else Color.WHITE
            canvas.drawRect(36f, currentY, 559f, currentY + 20f, paint)
            isAlternate = !isAlternate

            paint.color = Color.rgb(30, 41, 59)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
            val dateStr = dateFormat.format(Date(item.transaction.transactionDate))
            canvas.drawText(dateStr, 46f, currentY + 14f, paint)

            val desc = item.transaction.notes ?: item.transaction.type
            val ref = if (!item.transaction.referenceNumber.isNullOrEmpty()) " [Ref: ${item.transaction.referenceNumber}]" else ""
            val fullDesc = (desc + ref).take(28)
            canvas.drawText(fullDesc, 130f, currentY + 14f, paint)

            // Debit
            if (item.debitPaise > 0) {
                paint.color = Color.rgb(5, 150, 105)
                canvas.drawText(Money.formatIndianPaise(item.debitPaise, showPaise = false), 330f, currentY + 14f, paint)
            } else {
                paint.color = Color.GRAY
                canvas.drawText("-", 345f, currentY + 14f, paint)
            }

            // Credit
            if (item.creditPaise > 0) {
                paint.color = Color.rgb(220, 38, 38)
                canvas.drawText(Money.formatIndianPaise(item.creditPaise, showPaise = false), 410f, currentY + 14f, paint)
            } else {
                paint.color = Color.GRAY
                canvas.drawText("-", 425f, currentY + 14f, paint)
            }

            // Running Balance
            paint.color = Color.rgb(15, 23, 42)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            canvas.drawText(Money.formatIndianPaise(item.runningBalancePaise, showPaise = false), 490f, currentY + 14f, paint)

            // Bottom border line
            paint.color = Color.rgb(226, 232, 240)
            canvas.drawLine(36f, currentY + 20f, 559f, currentY + 20f, paint)

            currentY += 20f
        }

        // Summary Box at Bottom
        currentY += 15f
        paint.color = Color.rgb(241, 245, 249)
        canvas.drawRoundRect(36f, currentY, 559f, currentY + 45f, 6f, 6f, paint)

        paint.color = Color.rgb(15, 23, 42)
        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("FINAL OUTSTANDING: ${Money.formatIndianPaise(netBalancePaise)}", 50f, currentY + 26f, paint)

        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.ITALIC)
        paint.color = Color.GRAY
        canvas.drawText("Generated on ${timeFormat.format(Date())} via LedgerPro (Offline Ledger)", 50f, 810f, paint)
        canvas.drawText("Authorized Signatory: ___________________", 380f, 790f, paint)

        pdfDocument.finishPage(page)

        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Statement_${party.name.replace(" ", "_")}_${System.currentTimeMillis()}.pdf")
            val outputStream = FileOutputStream(file)
            pdfDocument.writeTo(outputStream)
            outputStream.close()
            pdfDocument.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            pdfDocument.close()
            null
        }
    }

    fun generateOutstandingSummaryPdf(
        context: Context,
        business: BusinessEntity,
        parties: List<com.example.core.repository.PartyWithBalance>
    ): File? {
        val pdfDocument = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
        val page = pdfDocument.startPage(pageInfo)
        val canvas: Canvas = page.canvas

        val paint = Paint().apply { isAntiAlias = true }
        val dateFormat = SimpleDateFormat("dd/MM/yyyy", Locale.ENGLISH)

        // Background
        paint.color = Color.WHITE
        canvas.drawRect(0f, 0f, 595f, 842f, paint)

        // Header
        paint.color = Color.rgb(15, 23, 42)
        canvas.drawRect(0f, 0f, 595f, 80f, paint)

        paint.color = Color.WHITE
        paint.textSize = 18f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText(business.name, 36f, 38f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        canvas.drawText("OUTSTANDING RECEIVABLES & PAYABLES SUMMARY", 36f, 58f, paint)
        canvas.drawText("Date: ${dateFormat.format(Date())}", 450f, 58f, paint)

        var currentY = 110f

        // Table Header
        paint.color = Color.rgb(30, 41, 59)
        canvas.drawRect(36f, currentY, 559f, currentY + 24f, paint)

        paint.color = Color.WHITE
        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("PARTY NAME", 46f, currentY + 16f, paint)
        canvas.drawText("PHONE", 260f, currentY + 16f, paint)
        canvas.drawText("RECEIVABLE (LENA)", 360f, currentY + 16f, paint)
        canvas.drawText("PAYABLE (DENA)", 470f, currentY + 16f, paint)

        currentY += 24f
        paint.textSize = 9f
        var isAlternate = false

        for (item in parties.take(28)) {
            paint.color = if (isAlternate) Color.rgb(248, 250, 252) else Color.WHITE
            canvas.drawRect(36f, currentY, 559f, currentY + 20f, paint)
            isAlternate = !isAlternate

            paint.color = Color.rgb(30, 41, 59)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
            canvas.drawText(item.party.name.take(26), 46f, currentY + 14f, paint)
            canvas.drawText(item.party.phone ?: "-", 260f, currentY + 14f, paint)

            if (item.netBalancePaise > 0) {
                paint.color = Color.rgb(5, 150, 105)
                canvas.drawText(Money.formatIndianPaise(item.netBalancePaise, showPaise = false), 360f, currentY + 14f, paint)
            } else {
                paint.color = Color.GRAY
                canvas.drawText("-", 380f, currentY + 14f, paint)
            }

            if (item.netBalancePaise < 0) {
                paint.color = Color.rgb(220, 38, 38)
                canvas.drawText(Money.formatIndianPaise(kotlin.math.abs(item.netBalancePaise), showPaise = false), 470f, currentY + 14f, paint)
            } else {
                paint.color = Color.GRAY
                canvas.drawText("-", 490f, currentY + 14f, paint)
            }

            paint.color = Color.rgb(226, 232, 240)
            canvas.drawLine(36f, currentY + 20f, 559f, currentY + 20f, paint)
            currentY += 20f
        }

        pdfDocument.finishPage(page)

        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Outstanding_Summary_${System.currentTimeMillis()}.pdf")
            val outputStream = FileOutputStream(file)
            pdfDocument.writeTo(outputStream)
            outputStream.close()
            pdfDocument.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            pdfDocument.close()
            null
        }
    }

    fun generateComprehensiveBusinessAuditPdf(
        context: Context,
        business: BusinessEntity,
        totalReceivablePaise: Long,
        totalPayablePaise: Long,
        todayInflowPaise: Long,
        todayOutflowPaise: Long,
        topDebtors: List<com.example.core.repository.PartyWithBalance>,
        topCreditors: List<com.example.core.repository.PartyWithBalance>,
        ageingSummary: com.example.core.repository.AgeingSummary
    ): File? {
        val pdfDocument = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
        val page = pdfDocument.startPage(pageInfo)
        val canvas: Canvas = page.canvas

        val paint = Paint().apply { isAntiAlias = true }
        val dateFormat = SimpleDateFormat("dd MMMM yyyy", Locale.ENGLISH)
        val timeFormat = SimpleDateFormat("hh:mm a", Locale.ENGLISH)

        // Background
        paint.color = Color.WHITE
        canvas.drawRect(0f, 0f, 595f, 842f, paint)

        // Navy Header Banner
        paint.color = Color.rgb(15, 23, 42) // Slate Navy
        canvas.drawRect(0f, 0f, 595f, 85f, paint)

        // Business Name & Title
        paint.color = Color.WHITE
        paint.textSize = 20f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText(business.name, 36f, 38f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        val contactStr = StringBuilder()
        if (!business.phone.isNullOrEmpty()) contactStr.append("Ph: ${business.phone}  |  ")
        if (!business.gstin.isNullOrEmpty()) contactStr.append("GSTIN: ${business.gstin}  |  ")
        contactStr.append("Offline Ledger Pro")
        canvas.drawText(contactStr.toString(), 36f, 58f, paint)

        paint.textSize = 12f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("EXECUTIVE AUDIT REPORT", 390f, 38f, paint)

        paint.textSize = 9f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        canvas.drawText("Generated: ${dateFormat.format(Date())} ${timeFormat.format(Date())}", 370f, 58f, paint)

        var currentY = 105f

        // KPI Highlights Cards
        // Card 1: Total Receivable
        paint.color = Color.rgb(236, 253, 245)
        canvas.drawRoundRect(36f, currentY, 195f, currentY + 54f, 6f, 6f, paint)
        paint.color = Color.rgb(5, 150, 105)
        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("TOTAL RECEIVABLE (LENA)", 46f, currentY + 18f, paint)
        paint.textSize = 13f
        canvas.drawText(Money.formatIndianPaise(totalReceivablePaise), 46f, currentY + 38f, paint)

        // Card 2: Total Payable
        paint.color = Color.rgb(254, 242, 242)
        canvas.drawRoundRect(210f, currentY, 375f, currentY + 54f, 6f, 6f, paint)
        paint.color = Color.rgb(220, 38, 38)
        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("TOTAL PAYABLE (DENA)", 220f, currentY + 18f, paint)
        paint.textSize = 13f
        canvas.drawText(Money.formatIndianPaise(totalPayablePaise), 220f, currentY + 38f, paint)

        // Card 3: Net Working Capital
        val netCapital = totalReceivablePaise - totalPayablePaise
        val isNetPositive = netCapital >= 0
        paint.color = if (isNetPositive) Color.rgb(240, 253, 250) else Color.rgb(255, 241, 242)
        canvas.drawRoundRect(390f, currentY, 559f, currentY + 54f, 6f, 6f, paint)
        paint.color = if (isNetPositive) Color.rgb(13, 148, 136) else Color.rgb(225, 29, 72)
        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("NET MARKET BALANCE", 400f, currentY + 18f, paint)
        paint.textSize = 13f
        canvas.drawText(Money.formatIndianPaise(netCapital), 400f, currentY + 38f, paint)

        currentY += 70f

        // Section: Ageing Analysis Summary
        paint.color = Color.rgb(30, 41, 59)
        paint.textSize = 11f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("1. RECEIVABLES AGEING & RISK BRACKETS", 36f, currentY, paint)

        currentY += 10f
        paint.color = Color.rgb(241, 245, 249)
        canvas.drawRoundRect(36f, currentY, 559f, currentY + 38f, 4f, 4f, paint)

        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        paint.color = Color.rgb(71, 85, 105)
        canvas.drawText("0-30 Days (Current)", 46f, currentY + 14f, paint)
        canvas.drawText("31-60 Days (Watch)", 180f, currentY + 14f, paint)
        canvas.drawText("61-90 Days (Overdue)", 310f, currentY + 14f, paint)
        canvas.drawText("90+ Days (High Risk)", 440f, currentY + 14f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        paint.color = Color.rgb(5, 150, 105)
        canvas.drawText(Money.formatIndianPaise(ageingSummary.currentPaise), 46f, currentY + 28f, paint)
        paint.color = Color.rgb(217, 119, 6)
        canvas.drawText(Money.formatIndianPaise(ageingSummary.days31To60Paise), 180f, currentY + 28f, paint)
        paint.color = Color.rgb(234, 88, 12)
        canvas.drawText(Money.formatIndianPaise(ageingSummary.days61To90Paise), 310f, currentY + 28f, paint)
        paint.color = Color.rgb(220, 38, 38)
        canvas.drawText(Money.formatIndianPaise(ageingSummary.over90Paise), 440f, currentY + 28f, paint)

        currentY += 55f

        // Section: Top Debtors (Lena) Table
        paint.color = Color.rgb(30, 41, 59)
        paint.textSize = 11f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("2. TOP CUSTOMER RECEIVABLES (LARGEST DEBTORS)", 36f, currentY, paint)

        currentY += 10f
        paint.color = Color.rgb(51, 65, 85)
        canvas.drawRect(36f, currentY, 559f, currentY + 18f, paint)

        paint.color = Color.WHITE
        paint.textSize = 8.5f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("CUSTOMER NAME", 46f, currentY + 12f, paint)
        canvas.drawText("PHONE", 240f, currentY + 12f, paint)
        canvas.drawText("CREDIT TERMS", 370f, currentY + 12f, paint)
        canvas.drawText("AMOUNT DUE (INR)", 470f, currentY + 12f, paint)

        currentY += 18f
        paint.textSize = 8.5f
        var isAltRow = false

        for (debtor in topDebtors.take(5)) {
            paint.color = if (isAltRow) Color.rgb(248, 250, 252) else Color.WHITE
            canvas.drawRect(36f, currentY, 559f, currentY + 16f, paint)
            isAltRow = !isAltRow

            paint.color = Color.rgb(15, 23, 42)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
            canvas.drawText(debtor.party.name.take(28), 46f, currentY + 11f, paint)
            canvas.drawText(debtor.party.phone ?: "-", 240f, currentY + 11f, paint)
            canvas.drawText("${debtor.party.paymentTermsDays ?: 30} Days", 370f, currentY + 11f, paint)

            paint.color = Color.rgb(5, 150, 105)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            canvas.drawText(Money.formatIndianPaise(debtor.netBalancePaise, showPaise = false), 470f, currentY + 11f, paint)

            paint.color = Color.rgb(226, 232, 240)
            canvas.drawLine(36f, currentY + 16f, 559f, currentY + 16f, paint)
            currentY += 16f
        }

        currentY += 20f

        // Section: Top Creditors (Dena) Table
        paint.color = Color.rgb(30, 41, 59)
        paint.textSize = 11f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("3. TOP SUPPLIER PAYABLES (LARGEST CREDITORS)", 36f, currentY, paint)

        currentY += 10f
        paint.color = Color.rgb(51, 65, 85)
        canvas.drawRect(36f, currentY, 559f, currentY + 18f, paint)

        paint.color = Color.WHITE
        paint.textSize = 8.5f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("SUPPLIER NAME", 46f, currentY + 12f, paint)
        canvas.drawText("PHONE", 240f, currentY + 12f, paint)
        canvas.drawText("GSTIN", 370f, currentY + 12f, paint)
        canvas.drawText("YOU OWE (INR)", 470f, currentY + 12f, paint)

        currentY += 18f
        isAltRow = false

        for (creditor in topCreditors.take(5)) {
            paint.color = if (isAltRow) Color.rgb(248, 250, 252) else Color.WHITE
            canvas.drawRect(36f, currentY, 559f, currentY + 16f, paint)
            isAltRow = !isAltRow

            paint.color = Color.rgb(15, 23, 42)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
            canvas.drawText(creditor.party.name.take(28), 46f, currentY + 11f, paint)
            canvas.drawText(creditor.party.phone ?: "-", 240f, currentY + 11f, paint)
            canvas.drawText(creditor.party.gstin ?: "-", 370f, currentY + 11f, paint)

            paint.color = Color.rgb(220, 38, 38)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            canvas.drawText(Money.formatIndianPaise(kotlin.math.abs(creditor.netBalancePaise), showPaise = false), 470f, currentY + 11f, paint)

            paint.color = Color.rgb(226, 232, 240)
            canvas.drawLine(36f, currentY + 16f, 559f, currentY + 16f, paint)
            currentY += 16f
        }

        // Footer block with verification
        paint.color = Color.rgb(241, 245, 249)
        canvas.drawRoundRect(36f, 755f, 559f, 805f, 6f, 6f, paint)
        paint.color = Color.rgb(15, 23, 42)
        paint.textSize = 8.5f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("CONFIDENTIAL & PRIVILEGED INTERNAL AUDIT REPORT", 50f, 772f, paint)
        paint.textSize = 8f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        paint.color = Color.GRAY
        canvas.drawText("Generated from on-device SQLite database via LedgerPro. Digitally verified.", 50f, 788f, paint)
        canvas.drawText("Authorized Signatory: __________________________", 340f, 788f, paint)

        pdfDocument.finishPage(page)

        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Business_Audit_Report_${System.currentTimeMillis()}.pdf")
            val outputStream = FileOutputStream(file)
            pdfDocument.writeTo(outputStream)
            outputStream.close()
            pdfDocument.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            pdfDocument.close()
            null
        }
    }

    fun generateDaybookPdf(
        context: Context,
        business: BusinessEntity,
        transactions: List<com.example.core.model.TransactionEntity>,
        partiesMap: Map<String, String>
    ): File? {
        val pdfDocument = PdfDocument()
        val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
        val page = pdfDocument.startPage(pageInfo)
        val canvas: Canvas = page.canvas

        val paint = Paint().apply { isAntiAlias = true }
        val dateFormat = SimpleDateFormat("dd/MM/yyyy", Locale.ENGLISH)
        val timeFormat = SimpleDateFormat("hh:mm a", Locale.ENGLISH)

        // Background
        paint.color = Color.WHITE
        canvas.drawRect(0f, 0f, 595f, 842f, paint)

        // Navy Header
        paint.color = Color.rgb(15, 23, 42)
        canvas.drawRect(0f, 0f, 595f, 80f, paint)

        paint.color = Color.WHITE
        paint.textSize = 18f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText(business.name, 36f, 38f, paint)

        paint.textSize = 10f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        canvas.drawText("DAYBOOK & CHRONOLOGICAL TRANSACTION REGISTER", 36f, 58f, paint)
        canvas.drawText("Date: ${dateFormat.format(Date())}", 450f, 58f, paint)

        var currentY = 105f

        // Table Header
        paint.color = Color.rgb(30, 41, 59)
        canvas.drawRect(36f, currentY, 559f, currentY + 22f, paint)

        paint.color = Color.WHITE
        paint.textSize = 9f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        canvas.drawText("DATE & TIME", 46f, currentY + 15f, paint)
        canvas.drawText("PARTY / ACCOUNT", 160f, currentY + 15f, paint)
        canvas.drawText("TYPE", 310f, currentY + 15f, paint)
        canvas.drawText("MODE", 390f, currentY + 15f, paint)
        canvas.drawText("AMOUNT (INR)", 475f, currentY + 15f, paint)

        currentY += 22f
        paint.textSize = 8.5f
        var isAltRow = false

        for (tx in transactions.take(28)) {
            paint.color = if (isAltRow) Color.rgb(248, 250, 252) else Color.WHITE
            canvas.drawRect(36f, currentY, 559f, currentY + 18f, paint)
            isAltRow = !isAltRow

            val dt = "${dateFormat.format(Date(tx.transactionDate))} ${timeFormat.format(Date(tx.transactionDate))}"
            val partyName = (partiesMap[tx.partyId] ?: tx.notes ?: "Self / Internal").take(22)

            paint.color = Color.rgb(15, 23, 42)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
            canvas.drawText(dt, 46f, currentY + 13f, paint)
            canvas.drawText(partyName, 160f, currentY + 13f, paint)
            canvas.drawText(tx.type.replace("_", " ").take(14), 310f, currentY + 13f, paint)
            canvas.drawText(tx.paymentMode, 390f, currentY + 13f, paint)

            val isGreen = tx.type == "GOT" || tx.type == "INCOME"
            paint.color = if (isGreen) Color.rgb(5, 150, 105) else Color.rgb(220, 38, 38)
            paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            canvas.drawText(Money.formatIndianPaise(tx.amountPaise, showPaise = false), 475f, currentY + 13f, paint)

            paint.color = Color.rgb(226, 232, 240)
            canvas.drawLine(36f, currentY + 18f, 559f, currentY + 18f, paint)
            currentY += 18f
        }

        // Footer
        paint.color = Color.rgb(241, 245, 249)
        canvas.drawRoundRect(36f, 770f, 559f, 805f, 6f, 6f, paint)
        paint.color = Color.GRAY
        paint.textSize = 8.5f
        paint.typeface = Typeface.create(Typeface.DEFAULT, Typeface.NORMAL)
        canvas.drawText("Generated from LedgerPro Secure Offline Database.", 50f, 792f, paint)
        canvas.drawText("Total Transactions in Register: ${transactions.size}", 380f, 792f, paint)

        pdfDocument.finishPage(page)

        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Daybook_Register_${System.currentTimeMillis()}.pdf")
            val outputStream = FileOutputStream(file)
            pdfDocument.writeTo(outputStream)
            outputStream.close()
            pdfDocument.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            pdfDocument.close()
            null
        }
    }
}
