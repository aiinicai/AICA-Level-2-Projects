package com.example.cube.model

import com.google.firebase.Timestamp
import com.google.firebase.firestore.DocumentId
import com.google.firebase.firestore.IgnoreExtraProperties
import com.google.firebase.firestore.ServerTimestamp

@IgnoreExtraProperties
data class UserProfile(
    @DocumentId val id: String = "",
    val displayName: String = "",
    val email: String = "",
    val photoUrl: String = "",
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val lastLoginAt: Timestamp? = null
) {
    fun toMap(): Map<String, Any> {
        val map = mutableMapOf<String, Any>()
        map["displayName"] = displayName
        map["email"] = email
        map["photoUrl"] = photoUrl
        map["createdAt"] = createdAt ?: Timestamp.now()
        map["lastLoginAt"] = Timestamp.now()
        return map
    }
}
