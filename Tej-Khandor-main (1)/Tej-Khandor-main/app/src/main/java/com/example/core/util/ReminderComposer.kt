package com.example.core.util

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.example.core.model.BusinessEntity
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

enum class ReminderLanguage(val title: String) {
    ENGLISH("English"),
    HINDI("Hindi (हिंदी)"),
    HINGLISH("Hinglish")
}

object ReminderComposer {
    fun buildReminderText(
        language: ReminderLanguage,
        business: BusinessEntity,
        party: PartyEntity,
        outstandingPaise: Long,
        dueDate: Long? = null
    ): String {
        val amountStr = Money.formatIndianPaise(outstandingPaise)
        val dateFormat = SimpleDateFormat("dd/MM/yyyy", Locale.ENGLISH)
        val dueDateStr = if (dueDate != null) dateFormat.format(Date(dueDate)) else "as soon as possible"
        val upiInfo = if (!business.upiId.isNullOrEmpty()) "\nUPI Payment ID: ${business.upiId}" else ""
        val phoneInfo = if (!business.phone.isNullOrEmpty()) "\nContact: ${business.phone}" else ""

        return when (language) {
            ReminderLanguage.ENGLISH -> {
                "Dear ${party.name},\n" +
                "This is a gentle payment reminder from ${business.name}. Your pending balance is $amountStr (due by $dueDateStr). " +
                "Kindly settle the amount at your earliest convenience.$upiInfo$phoneInfo\n" +
                "Thank you for your business!"
            }
            ReminderLanguage.HINDI -> {
                "नमस्ते ${party.name},\n" +
                "${business.name} से आपका बकाया भुगतान $amountStr है। कृपया यथाशीघ्र भुगतान करने का कष्ट करें।$upiInfo$phoneInfo\n" +
                "धन्यवाद!"
            }
            ReminderLanguage.HINGLISH -> {
                "Namaste ${party.name} ji,\n" +
                "${business.name} se aapka pending hisab-kitab $amountStr baki hai. Please ise jaldi se clear kar dijiye.$upiInfo$phoneInfo\n" +
                "Dhanyawad!"
            }
        }
    }

    fun shareViaWhatsApp(context: Context, phone: String?, message: String) {
        try {
            val cleanPhone = (phone ?: "").replace("+", "").replace(" ", "").replace("-", "")
            val fullPhone = if (cleanPhone.length == 10) "91$cleanPhone" else cleanPhone
            val uri = Uri.parse("https://api.whatsapp.com/send?phone=$fullPhone&text=${Uri.encode(message)}")
            val intent = Intent(Intent.ACTION_VIEW, uri)
            context.startActivity(intent)
        } catch (e: Exception) {
            // Fallback to general share sheet
            shareViaShareSheet(context, message, "Payment Reminder")
        }
    }

    fun shareViaSms(context: Context, phone: String?, message: String) {
        try {
            val uri = Uri.parse("smsto:${phone ?: ""}")
            val intent = Intent(Intent.ACTION_SENDTO, uri).apply {
                putExtra("sms_body", message)
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            shareViaShareSheet(context, message, "Payment Reminder")
        }
    }

    fun shareViaShareSheet(context: Context, text: String, title: String = "Share") {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
            putExtra(Intent.EXTRA_SUBJECT, title)
        }
        context.startActivity(Intent.createChooser(intent, title))
    }
}
