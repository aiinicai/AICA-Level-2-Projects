package com.example.cube.model

import androidx.compose.ui.graphics.Color

/**
 * Standard colors of a 3x3 Rubik's Cube.
 */
enum class CubeColor(
    val letter: Char,
    val displayName: String,
    val composeColor: Color,
    val contrastTextColor: Color
) {
    WHITE('U', "White", Color(0xFFF8FAFC), Color(0xFF0F172A)),
    RED('R', "Red", Color(0xFFEF4444), Color.White),
    GREEN('F', "Green", Color(0xFF10B981), Color.White),
    YELLOW('D', "Yellow", Color(0xFFFBBF24), Color(0xFF0F172A)),
    ORANGE('L', "Orange", Color(0xFFF97316), Color.White),
    BLUE('B', "Blue", Color(0xFF2563EB), Color.White);

    companion object {
        fun fromLetter(char: Char): CubeColor = when (char.uppercaseChar()) {
            'U' -> WHITE
            'R' -> RED
            'F' -> GREEN
            'D' -> YELLOW
            'L' -> ORANGE
            'B' -> BLUE
            else -> WHITE
        }

        fun fromName(name: String): CubeColor {
            val normalized = name.trim().lowercase()
            return entries.firstOrNull { it.name.lowercase() == normalized || it.displayName.lowercase() == normalized }
                ?: when {
                    normalized.contains("white") -> WHITE
                    normalized.contains("red") -> RED
                    normalized.contains("green") -> GREEN
                    normalized.contains("yellow") -> YELLOW
                    normalized.contains("orange") -> ORANGE
                    normalized.contains("blue") -> BLUE
                    else -> WHITE
                }
        }
    }
}

enum class CubeFace(val char: Char, val displayName: String, val indexInString: Int) {
    U('U', "Top (Up)", 0),
    R('R', "Right", 1),
    F('F', "Front", 2),
    D('D', "Bottom (Down)", 3),
    L('L', "Left", 4),
    B('B', "Back", 5);

    companion object {
        fun fromChar(c: Char): CubeFace = when (c.uppercaseChar()) {
            'U' -> U
            'R' -> R
            'F' -> F
            'D' -> D
            'L' -> L
            'B' -> B
            else -> F
        }
    }
}
