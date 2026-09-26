package com.example.data.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.data.dao.MedicineDao
import com.example.data.model.AppSettingsEntity
import com.example.data.model.Chemist
import com.example.data.model.EmergencyContact
import com.example.data.model.IntakeLog
import com.example.data.model.MedicalReport
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import com.example.data.model.RoutineVitalLog

@Database(
    entities = [
        PatientProfile::class,
        Prescription::class,
        Medicine::class,
        IntakeLog::class,
        MedicalReport::class,
        RoutineVitalLog::class,
        Chemist::class,
        EmergencyContact::class,
        AppSettingsEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun medicineDao(): MedicineDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                try {
                    db.execSQL("ALTER TABLE medicines ADD COLUMN hasTapering INTEGER NOT NULL DEFAULT 0")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperStartDate TEXT")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperDosage TEXT")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperTimesPerDay INTEGER")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperScheduledTimes TEXT")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperInstructions TEXT")
                    db.execSQL("ALTER TABLE medicines ADD COLUMN taperEndDate TEXT")
                } catch (_: Exception) {}
                try {
                    db.execSQL("ALTER TABLE intake_logs ADD COLUMN dosage TEXT NOT NULL DEFAULT ''")
                    db.execSQL("ALTER TABLE intake_logs ADD COLUMN isTapered INTEGER NOT NULL DEFAULT 0")
                } catch (_: Exception) {}
            }
        }

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "my_medicine_reminder.db"
                )
                    .addMigrations(MIGRATION_2_3)
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
