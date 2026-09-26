package com.example.util

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object DateUtils {
    const val FORMAT_DD_MM_YYYY = "dd-MM-yyyy"
    const val FORMAT_YYYY_MM_DD = "yyyy-MM-dd"

    /**
     * Returns today's date in DD-MM-YYYY format.
     */
    fun getToday(): String {
        return SimpleDateFormat(FORMAT_DD_MM_YYYY, Locale.getDefault()).format(Date())
    }

    /**
     * Returns tomorrow's date in DD-MM-YYYY format.
     */
    fun getTomorrow(): String {
        val cal = java.util.Calendar.getInstance()
        cal.add(java.util.Calendar.DAY_OF_YEAR, 1)
        return SimpleDateFormat(FORMAT_DD_MM_YYYY, Locale.getDefault()).format(cal.time)
    }

    /**
     * Parses a date string into a Calendar at 00:00:00.
     */
    fun parseToCalendar(dateStr: String?): java.util.Calendar? {
        val date = parseDate(dateStr) ?: return null
        return java.util.Calendar.getInstance().apply {
            time = date
            set(java.util.Calendar.HOUR_OF_DAY, 0)
            set(java.util.Calendar.MINUTE, 0)
            set(java.util.Calendar.SECOND, 0)
            set(java.util.Calendar.MILLISECOND, 0)
        }
    }

    /**
     * Checks if targetDate is on or between startDate and endDate.
     * If endDate is null or blank, checks if targetDate is on or after startDate.
     */
    fun isDateInRange(targetDateStr: String, startDateStr: String?, endDateStr: String?): Boolean {
        val targetCal = parseToCalendar(targetDateStr) ?: return true
        val startCal = parseToCalendar(startDateStr)
        val endCal = parseToCalendar(endDateStr)

        if (startCal != null && targetCal.before(startCal)) {
            return false
        }
        if (endCal != null && targetCal.after(endCal)) {
            return false
        }
        return true
    }

    /**
     * Checks if dateA is on or after dateB (ignoring time).
     */
    fun isOnOrAfter(dateA: String?, dateB: String?): Boolean {
        if (dateB.isNullOrBlank()) return true
        val calA = parseToCalendar(dateA) ?: return false
        val calB = parseToCalendar(dateB) ?: return true
        return !calA.before(calB)
    }

    /**
     * Checks if dateA is strictly before dateB (ignoring time).
     */
    fun isBefore(dateA: String?, dateB: String?): Boolean {
        val calA = parseToCalendar(dateA) ?: return false
        val calB = parseToCalendar(dateB) ?: return false
        return calA.before(calB)
    }

    /**
     * Converts any input date string (whether yyyy-MM-dd, dd-MM-yyyy, dd/MM/yyyy, yyyy/MM/dd)
     * into standard DD-MM-YYYY format for UI presentation.
     */
    fun formatDisplayDate(dateStr: String?): String {
        if (dateStr.isNullOrBlank()) return ""
        val trimmed = dateStr.trim()
        val patterns = listOf(
            "dd-MM-yyyy",
            "yyyy-MM-dd",
            "dd/MM/yyyy",
            "yyyy/MM/dd",
            "d-M-yyyy",
            "d/M/yyyy",
            "dd.MM.yyyy"
        )
        for (pattern in patterns) {
            try {
                val sdf = SimpleDateFormat(pattern, Locale.getDefault()).apply { isLenient = false }
                val parsed = sdf.parse(trimmed)
                if (parsed != null) {
                    return SimpleDateFormat(FORMAT_DD_MM_YYYY, Locale.getDefault()).format(parsed)
                }
            } catch (_: Exception) {}
        }
        return trimmed
    }

    /**
     * Parses a date string in various common formats into a java.util.Date object.
     */
    fun parseDate(dateStr: String?): Date? {
        if (dateStr.isNullOrBlank()) return null
        val trimmed = dateStr.trim()
        val patterns = listOf(
            "dd-MM-yyyy",
            "yyyy-MM-dd",
            "dd/MM/yyyy",
            "yyyy/MM/dd",
            "d-M-yyyy",
            "d/M/yyyy",
            "dd.MM.yyyy"
        )
        for (pattern in patterns) {
            try {
                val sdf = SimpleDateFormat(pattern, Locale.getDefault()).apply { isLenient = false }
                val parsed = sdf.parse(trimmed)
                if (parsed != null) return parsed
            } catch (_: Exception) {}
        }
        return null
    }

    /**
     * Converts between dd-MM-yyyy and yyyy-MM-dd for backward compatible queries:
     * If dd-MM-yyyy (e.g. "21-09-2026") -> returns "2026-09-21"
     * If yyyy-MM-dd (e.g. "2026-09-21") -> returns "21-09-2026"
     */
    fun getAlternateDateFormat(dateStr: String): String {
        val trimmed = dateStr.trim()
        return try {
            if (trimmed.contains("-")) {
                val parts = trimmed.split("-")
                if (parts.size == 3) {
                    if (parts[0].length == 4) {
                        // yyyy-MM-dd -> dd-MM-yyyy
                        "${parts[2]}-${parts[1]}-${parts[0]}"
                    } else if (parts[2].length == 4) {
                        // dd-MM-yyyy -> yyyy-MM-dd
                        "${parts[2]}-${parts[1]}-${parts[0]}"
                    } else trimmed
                } else trimmed
            } else trimmed
        } catch (_: Exception) {
            trimmed
        }
    }
}
