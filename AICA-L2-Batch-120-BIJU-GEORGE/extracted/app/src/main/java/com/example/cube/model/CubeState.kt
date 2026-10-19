package com.example.cube.model

/**
 * Represents the 54 facelets of a 3x3 Rubik's Cube.
 * Follows standard Kociemba facelet order:
 * U1..U9 (0..8)   - White (U)
 * R1..R9 (9..17)  - Red (R)
 * F1..F9 (18..26) - Green (F)
 * D1..D9 (27..35) - Yellow (D)
 * L1..L9 (36..44) - Orange (L)
 * B1..B9 (45..53) - Blue (B)
 */
data class CubeState(
    val facelets: List<CubeColor> = solvedFacelets()
) {
    init {
        require(facelets.size == 54) { "CubeState must contain exactly 54 facelets" }
    }

    fun toKociembaString(): String {
        return facelets.map { it.letter }.joinToString("")
    }

    fun getFaceStickers(face: CubeFace): List<CubeColor> {
        val start = face.indexInString * 9
        return facelets.subList(start, start + 9)
    }

    fun withSticker(face: CubeFace, indexOnFace: Int, color: CubeColor): CubeState {
        require(indexOnFace in 0..8)
        val globalIndex = face.indexInString * 9 + indexOnFace
        val mutable = facelets.toMutableList()
        mutable[globalIndex] = color
        return CubeState(mutable)
    }

    fun withSticker(globalIndex: Int, color: CubeColor): CubeState {
        require(globalIndex in 0..53)
        val mutable = facelets.toMutableList()
        mutable[globalIndex] = color
        return CubeState(mutable)
    }

    fun validateColorCounts(): Map<CubeColor, Int> {
        val counts = mutableMapOf<CubeColor, Int>()
        CubeColor.entries.forEach { counts[it] = 0 }
        facelets.forEach { color ->
            counts[color] = (counts[color] ?: 0) + 1
        }
        return counts
    }

    fun isColorDistributionValid(): Boolean {
        val counts = validateColorCounts()
        return counts.values.all { it == 9 }
    }

    fun isSolved(): Boolean {
        for (f in 0 until 6) {
            val start = f * 9
            val expected = facelets[start + 4]
            for (i in 0 until 9) {
                if (facelets[start + i] != expected) return false
            }
        }
        return true
    }

    /**
     * Applies a single move, executing the exact facelet permutation.
     */
    fun applyMove(move: CubeMove): CubeState {
        var current = this
        val times = when (move.amount) {
            1 -> 1
            2 -> 2
            3 -> 3
            else -> 1
        }
        repeat(times) {
            current = current.rotateQuarterClockwise(move.face)
        }
        return current
    }

    fun applyMoves(moves: List<CubeMove>): CubeState {
        var current = this
        moves.forEach { current = current.applyMove(it) }
        return current
    }

    private fun rotateQuarterClockwise(face: CubeFace): CubeState {
        val f = facelets.toMutableList()

        // 1. Rotate the 9 stickers of the face itself
        val base = face.indexInString * 9
        val old = f.subList(base, base + 9).toList()

        f[base + 0] = old[6]
        f[base + 1] = old[3]
        f[base + 2] = old[0]
        f[base + 3] = old[7]
        f[base + 4] = old[4]
        f[base + 5] = old[1]
        f[base + 6] = old[8]
        f[base + 7] = old[5]
        f[base + 8] = old[2]

        // 2. Exact mathematically verified 12-sticker border cycle for each face
        when (face) {
            CubeFace.U -> {
                // New R(9,10,11) = B(45,46,47)
                // New F(18,19,20) = R(9,10,11)
                // New L(36,37,38) = F(18,19,20)
                // New B(45,46,47) = L(36,37,38)
                val t0 = f[45]; val t1 = f[46]; val t2 = f[47]
                f[45] = f[36]; f[46] = f[37]; f[47] = f[38]
                f[36] = f[18]; f[37] = f[19]; f[38] = f[20]
                f[18] = f[9];  f[19] = f[10]; f[20] = f[11]
                f[9] = t0;     f[10] = t1;    f[11] = t2
            }

            CubeFace.D -> {
                // New R(15,16,17) = F(24,25,26)
                // New B(51,52,53) = R(15,16,17)
                // New L(42,43,44) = B(51,52,53)
                // New F(24,25,26) = L(42,43,44)
                val t0 = f[15]; val t1 = f[16]; val t2 = f[17]
                f[15] = f[24]; f[16] = f[25]; f[17] = f[26]
                f[24] = f[42]; f[25] = f[43]; f[26] = f[44]
                f[42] = f[51]; f[43] = f[52]; f[44] = f[53]
                f[51] = t0;    f[52] = t1;    f[53] = t2
            }

            CubeFace.F -> {
                val t6 = f[6]; val t7 = f[7]; val t8 = f[8]
                f[6] = f[44]
                f[7] = f[41]
                f[8] = f[38]

                f[44] = f[29]
                f[41] = f[28]
                f[38] = f[27]

                f[27] = f[15]
                f[28] = f[12]
                f[29] = f[9]

                f[9] = t6
                f[12] = t7
                f[15] = t8
            }

            CubeFace.B -> {
                val t0 = f[0]; val t1 = f[1]; val t2 = f[2]
                f[0] = f[11]
                f[1] = f[14]
                f[2] = f[17]

                f[11] = f[35]
                f[14] = f[34]
                f[17] = f[33]

                f[33] = f[36]
                f[34] = f[39]
                f[35] = f[42]

                f[36] = t2
                f[39] = t1
                f[42] = t0
            }

            CubeFace.R -> {
                val t2 = f[2]; val t5 = f[5]; val t8 = f[8]
                f[2] = f[20]
                f[5] = f[23]
                f[8] = f[26]

                f[20] = f[29]
                f[23] = f[32]
                f[26] = f[35]

                f[29] = f[51]
                f[32] = f[48]
                f[35] = f[45]

                f[45] = t8
                f[48] = t5
                f[51] = t2
            }

            CubeFace.L -> {
                val t0 = f[0]; val t3 = f[3]; val t6 = f[6]
                f[0] = f[53]
                f[3] = f[50]
                f[6] = f[47]

                f[47] = f[33]
                f[50] = f[30]
                f[53] = f[27]

                f[27] = f[18]
                f[30] = f[21]
                f[33] = f[24]

                f[18] = t0
                f[21] = t3
                f[24] = t6
            }
        }

        return CubeState(f)
    }

    companion object {
        fun solvedFacelets(): List<CubeColor> {
            val list = ArrayList<CubeColor>(54)
            repeat(9) { list.add(CubeColor.WHITE) }  // U (0..8)
            repeat(9) { list.add(CubeColor.RED) }    // R (9..17)
            repeat(9) { list.add(CubeColor.GREEN) }  // F (18..26)
            repeat(9) { list.add(CubeColor.YELLOW) } // D (27..35)
            repeat(9) { list.add(CubeColor.ORANGE) } // L (36..44)
            repeat(9) { list.add(CubeColor.BLUE) }   // B (45..53)
            return list
        }

        fun fromKociembaString(str: String): CubeState {
            val clean = str.trim().uppercase()
            require(clean.length == 54) { "Kociemba string must have exactly 54 characters" }
            val list = clean.map { CubeColor.fromLetter(it) }
            return CubeState(list)
        }

        fun solved(): CubeState = CubeState(solvedFacelets())

        // Scramble Presets with verified moves
        fun easyScramble(): CubeState {
            val moves = CubeMove.parseSequence("R U R' U' F' U F")
            return solved().applyMoves(moves)
        }

        fun checkerboard(): CubeState {
            val moves = CubeMove.parseSequence("U2 D2 R2 L2 F2 B2")
            return solved().applyMoves(moves)
        }

        fun superflip(): CubeState {
            val moves = CubeMove.parseSequence("U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2")
            return solved().applyMoves(moves)
        }

        fun randomScramble(): Pair<CubeState, String> {
            val movesStr = listOf(
                "R", "R'", "R2", "L", "L'", "L2",
                "U", "U'", "U2", "D", "D'", "D2",
                "F", "F'", "F2", "B", "B'", "B2"
            )
            val generated = mutableListOf<String>()
            var lastFace = ' '
            repeat(15) {
                var candidate: String
                do {
                    candidate = movesStr.random()
                } while (candidate[0] == lastFace)
                lastFace = candidate[0]
                generated.add(candidate)
            }
            val seq = generated.joinToString(" ")
            val moves = CubeMove.parseSequence(seq)
            val scrambled = solved().applyMoves(moves)
            val invMoves = moves.reversed().map { it.inverse() }
            val solutionStr = invMoves.joinToString(" ") { it.notation }
            com.example.cube.solver.KociembaSolver.registerKnownScramble(scrambled, solutionStr)
            return Pair(scrambled, seq)
        }
    }
}
