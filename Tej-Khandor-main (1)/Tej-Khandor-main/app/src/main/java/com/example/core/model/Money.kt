package com.example.core.model

import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

/**
 * Utility object for precision monetary representations in Paise (1 INR = 100 Paise).
 * Never uses floating-point numbers for financial calculations.
 */
object Money {
    fun rupeesToPaise(rupees: String): Long {
        val clean = rupees.trim().replace(",", "").replace("₹", "")
        if (clean.isEmpty()) return 0L
        val parts = clean.split(".")
        val whole = parts[0].toLongOrNull() ?: 0L
        val fraction = if (parts.size > 1) {
            val fracStr = parts[1].take(2).padEnd(2, '0')
            fracStr.toLongOrNull() ?: 0L
        } else {
            0L
        }
        return if (whole >= 0) whole * 100L + fraction else whole * 100L - fraction
    }

    fun paiseToRupees(paise: Long): String {
        val whole = paise / 100
        val fraction = kotlin.math.abs(paise % 100)
        return if (fraction == 0L) {
            whole.toString()
        } else {
            String.format(Locale.ENGLISH, "%d.%02d", whole, fraction)
        }
    }

    /**
     * Formats paise to Indian numbering format e.g. ₹1,25,000.00 or ₹1,25,000
     */
    fun formatIndianPaise(paise: Long, showPaise: Boolean = true, includeSymbol: Boolean = true): String {
        val isNegative = paise < 0
        val absPaise = kotlin.math.abs(paise)
        val whole = absPaise / 100
        val fraction = absPaise % 100

        val wholeStr = whole.toString()
        val formattedWhole = formatIndianNumber(wholeStr)

        val result = StringBuilder()
        if (isNegative) result.append("-")
        if (includeSymbol) result.append("₹")
        result.append(formattedWhole)
        if (showPaise && fraction > 0) {
            result.append(String.format(Locale.ENGLISH, ".%02d", fraction))
        } else if (showPaise) {
            result.append(".00")
        }
        return result.toString()
    }

    private fun formatIndianNumber(numberStr: String): String {
        if (numberStr.length <= 3) return numberStr
        val lastThree = numberStr.substring(numberStr.length - 3)
        val remaining = numberStr.substring(0, numberStr.length - 3)
        val sb = StringBuilder()
        var count = 0
        for (i in remaining.length - 1 downTo 0) {
            sb.insert(0, remaining[i])
            count++
            if (count == 2 && i != 0) {
                sb.insert(0, ",")
                count = 0
            }
        }
        return sb.toString() + "," + lastThree
    }
}
