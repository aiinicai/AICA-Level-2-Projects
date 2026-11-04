package com.example.cube.model

/**
 * Represents a standard Rubik's cube turn (Singmaster notation)
 * with detailed physical grip, direction, and finger-trick guidance.
 */
data class CubeMove(
    val face: CubeFace,
    val amount: Int // 1 = 90° CW, 2 = 180°, 3 = 90° CCW (i.e. ')
) {
    val notation: String = when (amount) {
        1 -> "${face.char}"
        2 -> "${face.char}2"
        3 -> "${face.char}'"
        else -> "${face.char}"
    }

    val directionName: String = when (amount) {
        1 -> "90° Clockwise"
        2 -> "180° Double Turn"
        3 -> "90° Counter-Clockwise"
        else -> "Turn"
    }

    val isClockwise: Boolean = amount == 1
    val isDoubleTurn: Boolean = amount == 2
    val isCounterClockwise: Boolean = amount == 3

    val layerLabel: String = when (face) {
        CubeFace.U -> "Top (Up) Layer"
        CubeFace.R -> "Right Layer"
        CubeFace.F -> "Front Face"
        CubeFace.D -> "Bottom (Down) Layer"
        CubeFace.L -> "Left Layer"
        CubeFace.B -> "Back Layer"
    }

    val description: String = when (face) {
        CubeFace.U -> when (amount) {
            1 -> "Turn TOP face 90° Clockwise"
            2 -> "Turn TOP face 180° (Half turn)"
            3 -> "Turn TOP face 90° Counter-Clockwise"
            else -> ""
        }
        CubeFace.R -> when (amount) {
            1 -> "Turn RIGHT face 90° Clockwise (Away from you)"
            2 -> "Turn RIGHT face 180° (Half turn)"
            3 -> "Turn RIGHT face 90° Counter-Clockwise (Toward you)"
            else -> ""
        }
        CubeFace.F -> when (amount) {
            1 -> "Turn FRONT face 90° Clockwise"
            2 -> "Turn FRONT face 180° (Half turn)"
            3 -> "Turn FRONT face 90° Counter-Clockwise"
            else -> ""
        }
        CubeFace.D -> when (amount) {
            1 -> "Turn BOTTOM face 90° Clockwise"
            2 -> "Turn BOTTOM face 180° (Half turn)"
            3 -> "Turn BOTTOM face 90° Counter-Clockwise"
            else -> ""
        }
        CubeFace.L -> when (amount) {
            1 -> "Turn LEFT face 90° Clockwise (Toward you)"
            2 -> "Turn LEFT face 180° (Half turn)"
            3 -> "Turn LEFT face 90° Counter-Clockwise (Away from you)"
            else -> ""
        }
        CubeFace.B -> when (amount) {
            1 -> "Turn BACK face 90° Clockwise"
            2 -> "Turn BACK face 180° (Half turn)"
            3 -> "Turn BACK face 90° Counter-Clockwise"
            else -> ""
        }
    }

    val fingerTrickTip: String = when (face) {
        CubeFace.U -> when (amount) {
            1 -> "Flick top-right corner with your right index finger pulling leftwards."
            2 -> "Double-flick top face: right index finger then right middle finger."
            3 -> "Flick top-left corner with your left index finger pulling rightwards."
            else -> ""
        }
        CubeFace.R -> when (amount) {
            1 -> "Push the right face upwards and away from you using your right hand."
            2 -> "Roll the right face 180° using two quick upwards wrist turns."
            3 -> "Pull the right face downwards toward you using your right thumb & wrist."
            else -> ""
        }
        CubeFace.F -> when (amount) {
            1 -> "Push front face clockwise using right index finger pushing downwards."
            2 -> "Turn front face 180° using right thumb and index finger."
            3 -> "Push front face counter-clockwise using right thumb pushing upwards."
            else -> ""
        }
        CubeFace.D -> when (amount) {
            1 -> "Use your right ring finger on the bottom layer to flick towards the right."
            2 -> "Double flick bottom layer 180° using right ring then pinky finger."
            3 -> "Use your left ring finger on the bottom layer to flick towards the left."
            else -> ""
        }
        CubeFace.L -> when (amount) {
            1 -> "Pull the left face downwards toward you using your left hand."
            2 -> "Roll the left face 180° using two quick downwards wrist turns."
            3 -> "Push the left face upwards and away from you using your left hand."
            else -> ""
        }
        CubeFace.B -> when (amount) {
            1 -> "Flick the back face clockwise with your right index finger extending behind."
            2 -> "Turn the back face 180° using two consecutive flicks."
            3 -> "Flick the back face counter-clockwise with your left index finger extending behind."
            else -> ""
        }
    }

    val angleDegrees: Float = when (amount) {
        1 -> 90f
        2 -> 180f
        3 -> -90f
        else -> 0f
    }

    fun inverse(): CubeMove = CubeMove(
        face = face,
        amount = when (amount) {
            1 -> 3
            2 -> 2
            3 -> 1
            else -> 1
        }
    )

    companion object {
        fun fromNotation(notation: String): CubeMove? {
            val clean = notation.trim()
            if (clean.isEmpty()) return null
            val faceChar = clean[0].uppercaseChar()
            val face = when (faceChar) {
                'U' -> CubeFace.U
                'R' -> CubeFace.R
                'F' -> CubeFace.F
                'D' -> CubeFace.D
                'L' -> CubeFace.L
                'B' -> CubeFace.B
                else -> return null
            }
            val amount = when {
                clean.length == 1 -> 1
                clean.endsWith("2") -> 2
                clean.endsWith("'") || clean.endsWith("i") -> 3
                else -> 1
            }
            return CubeMove(face, amount)
        }

        fun parseSequence(seq: String): List<CubeMove> {
            return seq.split(" ", "\n", "\t")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .mapNotNull { fromNotation(it) }
        }

        val ALL_STANDARD_MOVES = listOf(
            fromNotation("R")!!, fromNotation("R'")!!, fromNotation("R2")!!,
            fromNotation("U")!!, fromNotation("U'")!!, fromNotation("U2")!!,
            fromNotation("F")!!, fromNotation("F'")!!, fromNotation("F2")!!,
            fromNotation("L")!!, fromNotation("L'")!!, fromNotation("L2")!!,
            fromNotation("D")!!, fromNotation("D'")!!, fromNotation("D2")!!,
            fromNotation("B")!!, fromNotation("B'")!!, fromNotation("B2")!!
        )
    }
}
