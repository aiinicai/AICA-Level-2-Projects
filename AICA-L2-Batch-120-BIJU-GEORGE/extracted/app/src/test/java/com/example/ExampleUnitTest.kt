package com.example

import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import com.example.cube.solver.KociembaSolver
import org.junit.Assert.*
import org.junit.Test

class ExampleUnitTest {
  @Test
  fun addition_isCorrect() {
    assertEquals(4, 2 + 2)
  }

  @Test
  fun testAllMoves() {
    val moves = listOf("U" to 0, "R" to 3, "F" to 6, "D" to 9, "L" to 12, "B" to 15)
    for ((not, idx) in moves) {
      val solved = CubeState.solved()
      val c = solved.applyMove(com.example.cube.model.CubeMove.fromNotation(not)!!)
      val ccFace = KociembaSolver.CubieCube()
      val err = KociembaSolver.parseFacelets(c.toKociembaString(), ccFace)
      assertNull("Parse err for $not: $err", err)
      val ccMove = KociembaSolver.CubieCube()
      ccMove.applyMove(idx)

      assertArrayEquals("CP mismatch for $not", ccMove.cp, ccFace.cp)
      assertArrayEquals("CO mismatch for $not", ccMove.co, ccFace.co)
      assertArrayEquals("EP mismatch for $not", ccMove.ep, ccFace.ep)
      assertArrayEquals("EO mismatch for $not", ccMove.eo, ccFace.eo)
      println("Move $not MATCHES perfectly!")
    }
  }

  @Test
  fun testSequenceMultiplyVsApply() {
    val moves = listOf(0, 3, 6, 9, 12, 15, 1, 4, 7)
    val c1 = KociembaSolver.CubieCube()
    val c2 = KociembaSolver.CubieCube()
    for (m in moves) {
      c1.applyMove(m)
      val moveCube = KociembaSolver.CubieCube()
      moveCube.applyMove(m)
      c2.multiply(moveCube)
    }
    assertArrayEquals("CP mismatch", c1.cp, c2.cp)
    assertArrayEquals("CO mismatch", c1.co, c2.co)
    assertArrayEquals("EP mismatch", c1.ep, c2.ep)
    assertArrayEquals("EO mismatch", c1.eo, c2.eo)
  }

  @Test
  fun testEasyScrambleSolve() {
    val easyCube = CubeState.easyScramble()
    val cc = KociembaSolver.CubieCube()
    val err = KociembaSolver.parseFacelets(easyCube.toKociembaString(), cc)
    println("Parse err: $err")
    println("easyCube: twist=${cc.twist()}, flip=${cc.flip()}, slice=${cc.slice()}")
    println("easyCube isSolved=${cc.isSolved()}")

    // Test applying the known inverse: F' U' F U R U' R'
    val invMoves = com.example.cube.model.CubeMove.parseSequence("F' U' F U R U' R'")
    var testSolved = easyCube
    for (m in invMoves) {
      testSolved = testSolved.applyMove(m)
    }
    println("After inverse moves, isSolved in CubeState: ${testSolved.isSolved()}")

    val res = KociembaSolver.solve(easyCube)
    println("Solve result: $res")
    assertTrue("Should succeed but got $res", res is KociembaSolver.SolveResult.Success)
    val success = res as KociembaSolver.SolveResult.Success
    val solvedState = easyCube.applyMoves(success.moves)
    assertTrue("Cube must be solved after solution moves", solvedState.isSolved())
  }

  @Test
  fun testCheckerboardSolve() {
    val cube = CubeState.checkerboard()
    val res = KociembaSolver.solve(cube)
    assertTrue(res is KociembaSolver.SolveResult.Success)
    val success = res as KociembaSolver.SolveResult.Success
    val solvedState = cube.applyMoves(success.moves)
    assertTrue(solvedState.isSolved())
  }

  @Test
  fun testSuperflipSolve() {
    val scrambleMoves = CubeMove.parseSequence("U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2")
    val invMoves = scrambleMoves.reversed().map { it.inverse() }
    val testSolved = CubeState.solved().applyMoves(scrambleMoves).applyMoves(invMoves)
    println("testSolved with invMoves: isSolved=${testSolved.isSolved()}")
    if (!testSolved.isSolved()) {
      println("Mismatch: ${testSolved.toKociembaString()} vs ${CubeState.solved().toKociembaString()}")
    }
    val cube = CubeState.superflip()
    val res = KociembaSolver.solve(cube)
    println("Superflip solve result: $res")
    assertTrue(res is KociembaSolver.SolveResult.Success)
    val success = res as KociembaSolver.SolveResult.Success
    val solvedState = cube.applyMoves(success.moves)
    println("Superflip solvedState.isSolved: ${solvedState.isSolved()}")
    assertTrue(solvedState.isSolved())
  }

  @Test
  fun testRandomScrambleSolve() {
    val (cube, seq) = CubeState.randomScramble()
    println("Random scramble sequence: $seq")
    val res = KociembaSolver.solve(cube)
    println("Random scramble solve result: $res")
    assertTrue(res is KociembaSolver.SolveResult.Success)
    val success = res as KociembaSolver.SolveResult.Success
    val solvedState = cube.applyMoves(success.moves)
    println("Random scramble solvedState.isSolved: ${solvedState.isSolved()}")
    assertTrue(solvedState.isSolved())
  }

  @Test
  fun testStepByStepScramble() {
    val seq = "U' R2 U F2 U F2 L F' L B2 F B U' R' F"
    val moves = CubeMove.parseSequence(seq)
    var state = CubeState.solved()
    for ((idx, m) in moves.withIndex()) {
      state = state.applyMove(m)
      val cc = KociembaSolver.CubieCube()
      val err = KociembaSolver.parseFacelets(state.toKociembaString(), cc)
      println("Step $idx move ${m.notation}: parse err = $err")
      assertNull("Failed at step $idx move ${m.notation}: $err", err)
    }
  }
}
