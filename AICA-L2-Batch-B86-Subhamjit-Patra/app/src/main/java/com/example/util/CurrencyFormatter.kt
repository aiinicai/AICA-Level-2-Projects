package com.example.util

object CurrencyFormatter {

    fun formatInr(amount: Double, compact: Boolean = false): String {
        val isNegative = amount < 0
        val absAmount = Math.abs(amount)

        if (compact) {
            return when {
                absAmount >= 10_000_000 -> "${if (isNegative) "-" else ""}₹${String.format("%.2f", absAmount / 10_000_000)} Cr"
                absAmount >= 100_000 -> "${if (isNegative) "-" else ""}₹${String.format("%.2f", absAmount / 100_000)} L"
                absAmount >= 1_000 -> "${if (isNegative) "-" else ""}₹${String.format("%.1f", absAmount / 1_000)} K"
                else -> "${if (isNegative) "-" else ""}₹${absAmount.toLong()}"
            }
        }

        val longVal = absAmount.toLong()
        val s = longVal.toString()
        val sb = StringBuilder()
        val n = s.length
        if (n <= 3) {
            sb.append(s)
        } else {
            val last3 = s.substring(n - 3)
            var remaining = s.substring(0, n - 3)
            val parts = mutableListOf<String>()
            while (remaining.length > 2) {
                parts.add(remaining.substring(remaining.length - 2))
                remaining = remaining.substring(0, remaining.length - 2)
            }
            if (remaining.isNotEmpty()) {
                parts.add(remaining)
            }
            parts.reverse()
            sb.append(parts.joinToString(","))
            sb.append(",")
            sb.append(last3)
        }
        return "${if (isNegative) "-" else ""}₹$sb"
    }

    fun formatCompact(amount: Double): String = formatInr(amount, compact = true)
}
