package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import com.example.cube.model.SavedSolve
import com.example.cube.solver.KociembaSolver
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ExampleRobolectricTest {

    @Test
    fun testAppNameStringResource() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertEquals("CubeSolver", appName)
    }

    @Test
    fun testSolvedCubeState() {
        val cube = CubeState.solved()
        assertTrue(cube.isSolved())
        assertTrue(cube.isColorDistributionValid())
        assertEquals("UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB", cube.toKociembaString())
    }

    @Test
    fun testMoveExecutionAndInverse() {
        val cube = CubeState.solved()
        val move = CubeMove(CubeFace.R, 1) // R
        val inv = move.inverse() // R'

        val turned = cube.applyMove(move)
        assertTrue(!turned.isSolved())

        val restored = turned.applyMove(inv)
        assertTrue(restored.isSolved())
    }

    @Test
    fun testFourQuarterTurnsReturnsToOriginal() {
        val cube = CubeState.solved()
        val rMove = CubeMove(CubeFace.R, 1)
        val rotated = cube.applyMove(rMove).applyMove(rMove).applyMove(rMove).applyMove(rMove)
        assertTrue(rotated.isSolved())
    }

    @Test
    fun testSolverOnSolvedCube() {
        val cube = CubeState.solved()
        val result = KociembaSolver.solve(cube)
        assertTrue(result is KociembaSolver.SolveResult.Success)
        val success = result as KociembaSolver.SolveResult.Success
        assertEquals(0, success.moves.size)
    }

    @Test
    fun testSolverOnEasyScramble() {
        val cube = CubeState.solved().applyMove(CubeMove(CubeFace.U, 1))
        val result = KociembaSolver.solve(cube)
        assertTrue(result is KociembaSolver.SolveResult.Success)
        val success = result as KociembaSolver.SolveResult.Success
        assertTrue(success.moves.isNotEmpty())

        val solvedState = cube.applyMoves(success.moves)
        assertTrue(solvedState.isSolved())
    }

    @Test
    fun testSavedSolveModelMapping() {
        val solve = SavedSolve(
            userId = "user_123",
            name = "Test Solve",
            tags = listOf("practice", "favorite"),
            kociembaString = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB",
            solutionMoves = "R U R' U'",
            moveCount = 4L,
            solveTimeMs = 12L
        )

        val map = solve.toMap()
        assertEquals("user_123", map["userId"])
        assertEquals("Test Solve", map["name"])
        assertEquals(listOf("practice", "favorite"), map["tags"])
        assertEquals(4L, map["moveCount"])
    }
}
