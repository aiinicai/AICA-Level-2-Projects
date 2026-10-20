package com.example.engine

import kotlin.random.Random

object FortuneEngine {
    private val fortunes = listOf(
        "A warm heart will unlock a doorway that intellect has been knocking on for weeks.",
        "Your body is asking for kindness today, not perfection. Listen gently.",
        "The stars suggest an unexpected alignment in your favor before sundown.",
        "A sip of stillness will bring you more clarity than a storm of rushing.",
        "You are not behind in life; you are blooming in the season designed specifically for you.",
        "An old project or forgotten creative idea is ready to sparkle again.",
        "Your glow comes from the peace you protect, not the opinions you entertain.",
        "Small steps taken with faith move mountains faster than leaps taken in doubt.",
        "Someone you inspired recently is quietly rooting for your success.",
        "Trust the rhythm of your breath when the noise of the day gets too loud.",
        "The universe loves curiosity. Ask a bold question today.",
        "You have survived every single difficult day so far. Your score is 100%.",
        "A gentle word you speak today will ripple farther than you will ever know.",
        "Drink a tall glass of water; your energy is waiting to be refreshed.",
        "Honor your boundaries with love. They are the garden fence of your peace.",
        "An unexpected compliment will brighten your afternoon. Receive it gracefully.",
        "Release the need to predict tomorrow; today has enough magic waiting for you.",
        "Look into the mirror today and say: 'Thank you for carrying me so far.'",
        "The obstacle in your path is simply pointing you toward a sweeter shortcut.",
        "Your presence is a comfort to people even when you feel you haven't done enough."
    )

    fun getDailyFortune(dateString: String, name: String): Pair<String, Boolean> {
        // Seeded random for consistent fortune per day
        val seed = (dateString.hashCode() + name.lowercase().hashCode()).toLong()
        val random = Random(seed)
        val isGolden = random.nextInt(12) == 0 // ~1 in 12 chance of Golden Cookie
        val index = (random.nextInt(fortunes.size)).coerceIn(0, fortunes.size - 1)
        val text = fortunes[index]
        return Pair(text, isGolden)
    }
}
