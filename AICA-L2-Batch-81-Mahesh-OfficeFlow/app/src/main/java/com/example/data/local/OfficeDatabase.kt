package com.example.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.data.model.OfficeActivityNotification
import com.example.data.model.PortalIntegration
import com.example.data.model.TaxNotification

// Tasks, Projects, and Team Members now live in Firestore (see OfficeRepository) so every
// device shares the same live data. Tax notices, portal integrations, and the activity log
// have no cross-device consistency requirement yet and stay on this local Room database.
@Database(
    entities = [
        TaxNotification::class,
        OfficeActivityNotification::class,
        PortalIntegration::class
    ],
    version = 6,
    exportSchema = false
)
abstract class OfficeDatabase : RoomDatabase() {
    abstract fun officeDao(): OfficeDao

    companion object {
        @Volatile
        private var INSTANCE: OfficeDatabase? = null

        fun getDatabase(context: Context): OfficeDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    OfficeDatabase::class.java,
                    "office_flow_database.db"
                ).fallbackToDestructiveMigration().build()
                INSTANCE = instance
                instance
            }
        }
    }
}
