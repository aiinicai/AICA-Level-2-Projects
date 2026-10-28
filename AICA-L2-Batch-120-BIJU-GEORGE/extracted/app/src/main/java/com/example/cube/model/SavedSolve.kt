package com.example.cube.model

import com.google.firebase.Timestamp
import com.google.firebase.firestore.DocumentId
import com.google.firebase.firestore.IgnoreExtraProperties
import com.google.firebase.firestore.ServerTimestamp

@IgnoreExtraProperties
data class SavedSolve(
    @DocumentId val id: String = "",
    val userId: String = "",
    val name: String = "",
    val tags: List<String> = emptyList(),
    val kociembaString: String = "",
    val solutionMoves: String = "",
    val moveCount: Long = 0L,
    val solveTimeMs: Long = 0L,
    @ServerTimestamp val timestamp: Timestamp? = null
) {
    fun toMap(): Map<String, Any> {
        val map = mutableMapOf<String, Any>()
        map["userId"] = userId
        map["name"] = name
        map["tags"] = tags
        map["kociembaString"] = kociembaString
        map["solutionMoves"] = solutionMoves
        map["moveCount"] = moveCount
        map["solveTimeMs"] = solveTimeMs
        map["timestamp"] = timestamp ?: Timestamp.now()
        return map
    }
}
