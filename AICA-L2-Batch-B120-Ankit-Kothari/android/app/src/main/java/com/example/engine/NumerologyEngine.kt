package com.example.engine

import com.example.model.NumerologyReport

object NumerologyEngine {

    // Chaldean letter values
    private val chaldeanMap = mapOf(
        'A' to 1, 'I' to 1, 'J' to 1, 'Q' to 1, 'Y' to 1,
        'B' to 2, 'K' to 2, 'R' to 2,
        'C' to 3, 'G' to 3, 'L' to 3, 'S' to 3,
        'D' to 4, 'M' to 4, 'T' to 4,
        'E' to 5, 'H' to 5, 'N' to 5, 'X' to 5,
        'U' to 6, 'V' to 6, 'W' to 6,
        'O' to 7, 'Z' to 7,
        'F' to 8, 'P' to 8
    )

    private fun reduceSingleDigit(num: Int): Int {
        var n = num
        while (n > 9 && n != 11 && n != 22 && n != 33) {
            var sum = 0
            var temp = n
            while (temp > 0) {
                sum += temp % 10
                temp /= 10
            }
            n = sum
        }
        return n
    }

    fun calculateReport(birthDate: String, name: String): NumerologyReport {
        // Expected format YYYY-MM-DD
        val parts = birthDate.split("-")
        val year = parts.getOrNull(0)?.toIntOrNull() ?: 1998
        val month = parts.getOrNull(1)?.toIntOrNull() ?: 5
        val day = parts.getOrNull(2)?.toIntOrNull() ?: 15

        // Moolank (Day number)
        val moolank = reduceSingleDigit(day)

        // Bhagyank (Destiny number: all digits summed)
        var totalSum = 0
        "$year$month$day".forEach { char ->
            if (char.isDigit()) totalSum += char.digitToInt()
        }
        val bhagyank = reduceSingleDigit(totalSum)

        // Life Path
        val lifePath = bhagyank

        // Naamank (Name Chaldean sum)
        var nameSum = 0
        name.uppercase().forEach { ch ->
            nameSum += chaldeanMap[ch] ?: 0
        }
        val chaldeanCompound = nameSum
        val naamank = reduceSingleDigit(nameSum)

        // Lo Shu Grid digit frequency
        val digits = "$year$month$day".filter { it.isDigit() }.map { it.digitToInt() }
        val loShuCounts = mutableMapOf<Int, Int>()
        for (i in 1..9) {
            loShuCounts[i] = digits.count { it == i }
        }

        val arrows = mutableListOf<String>()
        // Planes:
        if ((loShuCounts[4] ?: 0) > 0 && (loShuCounts[3] ?: 0) > 0 && (loShuCounts[8] ?: 0) > 0) {
            arrows.add("Arrow of Thought (4-3-8): Strategic mind, high retention, insightful planning")
        }
        if ((loShuCounts[9] ?: 0) > 0 && (loShuCounts[5] ?: 0) > 0 && (loShuCounts[1] ?: 0) > 0) {
            arrows.add("Arrow of Will (9-5-1): Unstoppable determination, resilience through change")
        }
        if ((loShuCounts[2] ?: 0) > 0 && (loShuCounts[7] ?: 0) > 0 && (loShuCounts[6] ?: 0) > 0) {
            arrows.add("Arrow of Action (2-7-6): Practical execution, physical vitality, artistic taste")
        }
        if ((loShuCounts[4] ?: 0) > 0 && (loShuCounts[9] ?: 0) > 0 && (loShuCounts[2] ?: 0) > 0) {
            arrows.add("Mental Plane (4-9-2): Analytical strength, intellectual curiosity")
        }
        if ((loShuCounts[3] ?: 0) > 0 && (loShuCounts[5] ?: 0) > 0 && (loShuCounts[7] ?: 0) > 0) {
            arrows.add("Emotional Plane (3-5-7): High empathy, spiritual depth, warmth")
        }
        if ((loShuCounts[8] ?: 0) > 0 && (loShuCounts[1] ?: 0) > 0 && (loShuCounts[6] ?: 0) > 0) {
            arrows.add("Practical Plane (8-1-6): Earthy competence, financial wisdom")
        }
        if (arrows.isEmpty()) {
            arrows.add("Balanced Chart: Adaptable, receptive to multiple growth avenues")
        }

        val qualities = when (moolank) {
            1 -> listOf("Leadership", "Originality", "Ambition", "Pioneer spirit")
            2 -> listOf("Diplomacy", "Intuition", "Harmony", "Gentle grace")
            3 -> listOf("Creative expression", "Optimism", "Wit", "Inspiration")
            4 -> listOf("Systematic discipline", "Dependability", "Endurance")
            5 -> listOf("Versatility", "Freedom", "Charisma", "Adaptability")
            6 -> listOf("Compassion", "Nurturing", "Beauty", "Family balance")
            7 -> listOf("Depth", "Spiritual discernment", "Investigation", "Quiet wisdom")
            8 -> listOf("Material mastery", "Authority", "Visionary courage")
            9 -> listOf("Universal love", "Artistry", "Generosity", "Broad perspective")
            else -> listOf("Integrity", "Kindness", "Creativity")
        }

        return NumerologyReport(
            lifePath = lifePath,
            moolank = moolank,
            bhagyank = bhagyank,
            naamank = naamank,
            chaldeanCompound = chaldeanCompound,
            loShuCounts = loShuCounts,
            arrowStrengths = arrows,
            coreQualities = qualities
        )
    }
}
