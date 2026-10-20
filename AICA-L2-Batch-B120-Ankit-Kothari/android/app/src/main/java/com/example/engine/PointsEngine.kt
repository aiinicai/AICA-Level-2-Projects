package com.example.engine

import com.example.model.Badge

object PointsEngine {

    val allBadges = listOf(
        Badge("first_sip", "First Sip", "Logged your first glass of water", "water_drop"),
        Badge("hydration_hero", "Hydration Hero", "Hit water goal consistently", "local_drink"),
        Badge("ten_k_club", "10K Club", "Walked 10,000+ steps in a day", "directions_walk"),
        Badge("neck_saver", "Neck Saver", "Completed neck relief routines", "accessibility"),
        Badge("eagle_eyes", "Eagle Eyes", "Practiced 20-20-20 eye breaks", "visibility"),
        Badge("glow_getter", "Glow Getter", "Completed first Glow check-in", "auto_awesome"),
        Badge("glow_journal", "Glow Journal", "Maintained 5 glow check-in entries", "photo_library"),
        Badge("fortune_finder", "Fortune Finder", "Cracked a daily fortune cookie", "cookie"),
        Badge("golden_touch", "Golden Touch", "Found a rare Golden Fortune cookie", "star"),
        Badge("know_thyself", "Know Thyself", "Completed Big Five personality quiz", "psychology"),
        Badge("star_child", "Star Child", "Explored deep birth chart & day card", "nightlight"),
        Badge("week_warrior", "Week Warrior", "Kept a 7-day healthy habits streak", "local_fire_department"),
        Badge("month_master", "Month Master", "Maintained a 30-day streak", "military_tech"),
        Badge("early_bird", "Early Bird", "Logged morning routine before 8 AM", "wb_sunny"),
        Badge("body_aware", "Body Aware", "Logged BMI and body health metrics", "monitor_weight"),
        Badge("desk_zen", "Desk Zen", "Completed desk stretches during work", "self_improvement")
    )

    fun calculateLevel(totalPoints: Int): Pair<String, Float> {
        return when {
            totalPoints < 300 -> Pair("Spark", totalPoints / 300f)
            totalPoints < 900 -> Pair("Glow", (totalPoints - 300) / 600f)
            totalPoints < 2000 -> Pair("Shine", (totalPoints - 900) / 1100f)
            totalPoints < 4000 -> Pair("Radiant", (totalPoints - 2000) / 2000f)
            totalPoints < 7500 -> Pair("Luminary", (totalPoints - 4000) / 3500f)
            else -> Pair("Supernova", 1f)
        }
    }
}
