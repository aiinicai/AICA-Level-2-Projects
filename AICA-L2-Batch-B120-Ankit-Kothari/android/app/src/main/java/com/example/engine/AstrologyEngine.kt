package com.example.engine

import com.example.model.DayCardData
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

object AstrologyEngine {

    private val nakshatras = listOf(
        "Ashwini (Healer's Star)", "Bharani (Star of Restraint)", "Krittika (The Cutter)",
        "Rohini (The Star of Ascent)", "Mrigashirsha (The Searching Star)", "Ardra (The Teardrop)",
        "Punarvasu (Return of the Light)", "Pushya (The Nurturer)", "Ashlesha (The Clinging Star)",
        "Magha (The Royal Throne)", "Purva Phalguni (The Fruit of Tree)", "Uttara Phalguni (Patron Star)",
        "Hasta (The Golden Hand)", "Chitra (The Jewel of Heaven)", "Swati (The Sword of Grace)",
        "Vishakha (The Forked Branch)", "Anuradha (The Star of Success)", "Jyeshtha (The Eldest)",
        "Mula (The Root Star)", "Purva Ashadha (The Invincible)", "Uttara Ashadha (Universal Good)",
        "Shravana (The Listening Ear)", "Dhanishta (The Star of Symphony)", "Shatabhisha (Hundred Physicians)",
        "Purva Bhadrapada (Blessed Feet)", "Uttara Bhadrapada (Warrior of Peace)", "Revati (The Shepherd)"
    )

    private val signs = listOf(
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    )

    private val tithis = listOf(
        "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya", "Shukla Chaturthi",
        "Shukla Panchami", "Shukla Shashti", "Shukla Saptami", "Shukla Ashtami",
        "Shukla Navami", "Shukla Dashami", "Shukla Ekadashi", "Shukla Dvadashi",
        "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima (Full Moon)",
        "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya", "Krishna Chaturthi",
        "Krishna Panchami", "Krishna Shashti", "Krishna Saptami", "Krishna Ashtami",
        "Krishna Navami", "Krishna Dashami", "Krishna Ekadashi", "Krishna Dvadashi",
        "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya (New Moon)"
    )

    fun calculateDayCard(calendar: Calendar = Calendar.getInstance(), city: String = "Dubai"): DayCardData {
        val dayOfWeek = calendar.get(Calendar.DAY_OF_WEEK)
        val dayOfYear = calendar.get(Calendar.DAY_OF_YEAR)
        val year = calendar.get(Calendar.YEAR)

        // Moon cycle simulation (29.53 day lunar synodic period)
        val daysSinceEpoch = (year - 2024) * 365 + dayOfYear
        val moonAge = (daysSinceEpoch % 29.53059).toFloat()
        val tithiIndex = ((moonAge / 29.53059f) * 30).toInt().coerceIn(0, 29)
        val tithi = tithis[tithiIndex]

        // Nakshatra travels through 27 mansions in ~27.32 days
        val nakshatraIndex = ((daysSinceEpoch % 27.32166) / 27.32166 * 27).toInt().coerceIn(0, 26)
        val nakshatra = nakshatras[nakshatraIndex]

        // Moon signs
        val signIndex = ((daysSinceEpoch / 2.28) % 12).toInt().coerceIn(0, 11)
        val tropicalSign = signs[signIndex]
        // Sidereal Lahiri is roughly 24 degrees (~1 sign back depending on longitude)
        val siderealIndex = (signIndex - 1 + 12) % 12
        val siderealSign = signs[siderealIndex]

        // Day Lord & Rahu Kaal based on Day of Week
        val (dayLord, rahuKaal, luckyColor, luckyColorHex, luckyNumber) = when (dayOfWeek) {
            Calendar.SUNDAY -> Tuple5("Surya (Sun)", "16:30 - 18:00", "Gold / Amber", 0xFFF59E0B, 1)
            Calendar.MONDAY -> Tuple5("Chandra (Moon)", "07:30 - 09:00", "Pearl White / Silver", 0xFFE2E8F0, 2)
            Calendar.TUESDAY -> Tuple5("Mangal (Mars)", "15:00 - 16:30", "Coral Red / Terracotta", 0xFFEF4444, 9)
            Calendar.WEDNESDAY -> Tuple5("Budh (Mercury)", "12:00 - 13:30", "Emerald Green", 0xFF10B981, 5)
            Calendar.THURSDAY -> Tuple5("Guru (Jupiter)", "13:30 - 15:00", "Saffron / Warm Yellow", 0xFFFBBF24, 3)
            Calendar.FRIDAY -> Tuple5("Shukra (Venus)", "10:30 - 12:00", "Pastel Rose / Cream", 0xFFEC4899, 6)
            Calendar.SATURDAY -> Tuple5("Shani (Saturn)", "09:00 - 10:30", "Midnight Blue / Indigo", 0xFF3B82F6, 8)
            else -> Tuple5("Mercury", "12:00 - 13:30", "Green", 0xFF10B981, 5)
        }

        val abhijitMuhurta = "11:48 AM - 12:36 PM"
        val dayScore = (7 + (dayOfYear % 4)) // Score between 7 and 10

        val dateFormat = SimpleDateFormat("EEEE, MMM d, yyyy", Locale.getDefault())
        val dateDisplay = dateFormat.format(calendar.time)

        return DayCardData(
            dateDisplay = dateDisplay,
            moonSign = tropicalSign,
            moonSignVedic = siderealSign,
            nakshatra = nakshatra,
            tithi = tithi,
            dayLord = dayLord,
            rahuKaal = rahuKaal,
            abhijitMuhurta = abhijitMuhurta,
            dayScore = dayScore,
            luckyColor = luckyColor,
            luckyColorHex = luckyColorHex,
            luckyNumber = luckyNumber,
            proTip = "Today's Moon favors deliberate action and gentle speech. Protect your midday focus.",
            doItems = listOf("Start important conversations before Rahu Kaal", "Hydrate generously during water hours", "Take a short nature walk near sunset"),
            avoidItems = listOf("Overcommitting on impulse", "Skipping your evening stretch routine", "Engaging in pointless online arguments"),
            lovingLine = "You are deeply worthy of peace, rest, and all good things that are quietly finding you.",
            motivationLine = "Small calm steps taken with certainty will outpace all rushed chaos."
        )
    }

    private data class Tuple5(
        val dayLord: String,
        val rahuKaal: String,
        val luckyColor: String,
        val luckyColorHex: Long,
        val luckyNumber: Int
    )
}
