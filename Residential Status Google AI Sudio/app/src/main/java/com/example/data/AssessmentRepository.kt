package com.example.data

import kotlinx.coroutines.flow.Flow

class AssessmentRepository(private val dao: AssessmentDao) {
    val allAssessments: Flow<List<AssessmentEntity>> = dao.getAllAssessments()

    fun getAssessmentsByRegime(regime: String): Flow<List<AssessmentEntity>> {
        return dao.getAssessmentsByRegime(regime)
    }

    suspend fun getAssessmentById(id: Long): AssessmentEntity? {
        return dao.getAssessmentById(id)
    }

    suspend fun saveAssessment(record: AssessmentEntity): Long {
        return dao.insertAssessment(record)
    }

    suspend fun deleteAssessment(id: Long) {
        dao.deleteAssessmentById(id)
    }

    suspend fun clearHistory() {
        dao.clearAll()
    }
}
