package com.example.cube.data

import android.content.Context
import com.example.R
import com.example.cube.model.SavedSolve
import com.example.cube.model.UserProfile
import com.google.firebase.Timestamp
import com.google.firebase.firestore.DocumentSnapshot
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.Query
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await

class CubeHistoryRepository(private val firestore: FirebaseFirestore) {

    constructor(context: Context) : this(
        FirebaseFirestore.getInstance(
            context.applicationContext.getString(R.string.firestore_database_id)
        )
    )

    fun observeSavedSolves(userId: String): Flow<List<SavedSolve>> = callbackFlow {
        if (userId.isBlank()) {
            trySend(emptyList())
            close()
            return@callbackFlow
        }

        val collectionRef = firestore.collection("users")
            .document(userId)
            .collection("saved_solves")
            .orderBy("timestamp", Query.Direction.DESCENDING)

        val listenerRegistration = collectionRef.addSnapshotListener { snapshot, error ->
            if (error != null) {
                close(error)
                return@addSnapshotListener
            }
            if (snapshot != null) {
                val solves = snapshot.documents.mapNotNull { doc ->
                    doc.toObject(SavedSolve::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                }
                trySend(solves)
            }
        }

        awaitClose { listenerRegistration.remove() }
    }

    suspend fun saveSolve(
        userId: String,
        name: String,
        tags: List<String>,
        kociembaString: String,
        solutionMoves: String,
        moveCount: Long,
        solveTimeMs: Long
    ): Result<String> {
        if (userId.isBlank()) {
            return Result.failure(IllegalStateException("User must be authenticated to save solves."))
        }

        return try {
            val docRef = firestore.collection("users")
                .document(userId)
                .collection("saved_solves")
                .document()

            val data = mapOf(
                "userId" to userId,
                "name" to name.ifBlank { "Solve #${System.currentTimeMillis() % 10000}" },
                "tags" to tags,
                "kociembaString" to kociembaString,
                "solutionMoves" to solutionMoves,
                "moveCount" to moveCount,
                "solveTimeMs" to solveTimeMs,
                "timestamp" to FieldValue.serverTimestamp()
            )

            docRef.set(data).await()
            Result.success(docRef.id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateSolve(
        userId: String,
        solveId: String,
        name: String,
        tags: List<String>
    ): Result<Unit> {
        if (userId.isBlank() || solveId.isBlank()) {
            return Result.failure(IllegalArgumentException("Invalid user or solve ID"))
        }

        return try {
            firestore.collection("users")
                .document(userId)
                .collection("saved_solves")
                .document(solveId)
                .update(
                    mapOf(
                        "name" to name,
                        "tags" to tags
                    )
                ).await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteSolve(userId: String, solveId: String): Result<Unit> {
        if (userId.isBlank() || solveId.isBlank()) {
            return Result.failure(IllegalArgumentException("Invalid user or solve ID"))
        }

        return try {
            firestore.collection("users")
                .document(userId)
                .collection("saved_solves")
                .document(solveId)
                .delete()
                .await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun recordUserLogin(
        userId: String,
        displayName: String,
        email: String,
        photoUrl: String
    ): Result<Unit> {
        if (userId.isBlank()) return Result.failure(IllegalStateException("User ID required"))

        return try {
            val userRef = firestore.collection("users").document(userId)
            val snapshot = userRef.get().await()

            if (!snapshot.exists()) {
                val newUser = UserProfile(
                    displayName = displayName,
                    email = email,
                    photoUrl = photoUrl,
                    createdAt = Timestamp.now(),
                    lastLoginAt = Timestamp.now()
                )
                userRef.set(newUser.toMap()).await()
            } else {
                userRef.update(
                    mapOf(
                        "displayName" to displayName,
                        "email" to email,
                        "photoUrl" to photoUrl,
                        "lastLoginAt" to FieldValue.serverTimestamp()
                    )
                ).await()
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
