package com.example.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "assessments")
data class AssessmentEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val clientName: String,
    val pan: String,
    val period: String, // e.g., "AY 2026-27" or "FY 2025-26"
    val regime: String, // "INCOME_TAX" or "FEMA"
    val statusCode: String, // "ROR", "RNOR", "NR", "PRI", "PROI"
    val statusTitle: String,
    val statutoryProvision: String,
    val timestamp: Long = System.currentTimeMillis(),
    val summary: String,
    val rationaleBullets: String, // newline separated or json
    val keyFactorsSummary: String, // key-value pairs formatted
    val notes: String = ""
)
