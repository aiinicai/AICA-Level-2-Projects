package com.example.core.util

import android.content.Context
import com.example.core.model.BusinessEntity
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import com.example.core.repository.LedgerItem
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object CsvExporter {
    fun exportPartyLedgerCsv(
        context: Context,
        party: PartyEntity,
        ledgerItems: List<LedgerItem>
    ): File? {
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Ledger_${party.name.replace(" ", "_")}_${System.currentTimeMillis()}.csv")
            val writer = FileWriter(file)

            writer.append("Date,Transaction ID,Type,Reference No,Payment Mode,Notes,Debit (Paise),Credit (Paise),Running Balance (INR)\n")
            for (item in ledgerItems) {
                val dateStr = dateFormat.format(Date(item.transaction.transactionDate))
                val type = item.transaction.type
                val ref = (item.transaction.referenceNumber ?: "").replace(",", " ")
                val mode = item.transaction.paymentMode
                val notes = (item.transaction.notes ?: "").replace(",", " ")
                val debit = item.debitPaise
                val credit = item.creditPaise
                val balanceInr = Money.paiseToRupees(item.runningBalancePaise)

                writer.append("$dateStr,${item.transaction.id},$type,$ref,$mode,$notes,$debit,$credit,$balanceInr\n")
            }
            writer.flush()
            writer.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun exportDaybookCsv(
        context: Context,
        business: BusinessEntity,
        transactions: List<TransactionEntity>,
        partiesMap: Map<String, PartyEntity>
    ): File? {
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Daybook_${business.name.replace(" ", "_")}_${System.currentTimeMillis()}.csv")
            val writer = FileWriter(file)

            writer.append("Date,Transaction ID,Party Name,Type,Amount (INR),Payment Mode,Status,Reference No,Notes\n")
            for (tx in transactions) {
                val dateStr = dateFormat.format(Date(tx.transactionDate))
                val partyName = partiesMap[tx.partyId]?.name ?: "N/A"
                val amountInr = Money.paiseToRupees(tx.amountPaise)
                val ref = (tx.referenceNumber ?: "").replace(",", " ")
                val notes = (tx.notes ?: "").replace(",", " ")

                writer.append("$dateStr,${tx.id},\"$partyName\",${tx.type},$amountInr,${tx.paymentMode},${tx.status},$ref,\"$notes\"\n")
            }
            writer.flush()
            writer.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun exportAllTransactionsCsv(
        context: Context,
        transactions: List<TransactionEntity>,
        partiesMap: Map<String, String>
    ): File? {
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)
        return try {
            val docsDir = File(context.cacheDir, "docs").apply { mkdirs() }
            val file = File(docsDir, "Transactions_${System.currentTimeMillis()}.csv")
            val writer = FileWriter(file)

            writer.append("Date,Transaction ID,Party Name,Type,Amount (INR),Payment Mode,Status,Reference No,Notes\n")
            for (tx in transactions) {
                val dateStr = dateFormat.format(Date(tx.transactionDate))
                val partyName = partiesMap[tx.partyId] ?: "N/A"
                val amountInr = Money.paiseToRupees(tx.amountPaise)
                val ref = (tx.referenceNumber ?: "").replace(",", " ")
                val notes = (tx.notes ?: "").replace(",", " ")

                writer.append("$dateStr,${tx.id},\"$partyName\",${tx.type},$amountInr,${tx.paymentMode},${tx.status},$ref,\"$notes\"\n")
            }
            writer.flush()
            writer.close()
            file
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}
