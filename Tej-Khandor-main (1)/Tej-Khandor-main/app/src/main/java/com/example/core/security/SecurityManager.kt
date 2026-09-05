package com.example.core.security

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import com.example.core.database.AppDatabase
import com.example.core.model.AccountEntity
import com.example.core.model.AuditLogEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.CategoryEntity
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

data class BackupMetadata(
    val backupId: String,
    val businessName: String,
    val businessId: String,
    val partyCount: Int,
    val transactionCount: Int,
    val accountCount: Int,
    val createdAt: Long,
    val appVersion: String = "1.0"
)

class SecurityManager(private val context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("ledgerpro_security", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_PIN_HASH = "pin_hash"
        private const val KEY_PIN_SALT = "pin_salt"
        private const val KEY_LOCK_ENABLED = "lock_enabled"
        private const val KEY_AUTO_LOCK_MINS = "auto_lock_mins"
        private const val KEY_LAST_ACTIVE = "last_active_time"
        private const val ITERATIONS = 10000
        private const val KEY_LENGTH = 256
    }

    fun isLockEnabled(): Boolean = prefs.getBoolean(KEY_LOCK_ENABLED, false)

    fun hasPinSet(): Boolean = prefs.contains(KEY_PIN_HASH)

    fun setPin(pin: String) {
        val salt = ByteArray(16)
        SecureRandom().nextBytes(salt)
        val hash = hashPin(pin, salt)
        prefs.edit()
            .putString(KEY_PIN_HASH, Base64.encodeToString(hash, Base64.NO_WRAP))
            .putString(KEY_PIN_SALT, Base64.encodeToString(salt, Base64.NO_WRAP))
            .putBoolean(KEY_LOCK_ENABLED, true)
            .apply()
    }

    fun verifyPin(pin: String): Boolean {
        val storedHash = prefs.getString(KEY_PIN_HASH, null) ?: return false
        val storedSaltStr = prefs.getString(KEY_PIN_SALT, null) ?: return false
        val salt = Base64.decode(storedSaltStr, Base64.NO_WRAP)
        val computedHash = hashPin(pin, salt)
        return Base64.encodeToString(computedHash, Base64.NO_WRAP) == storedHash
    }

    fun disableLock() {
        prefs.edit()
            .remove(KEY_PIN_HASH)
            .remove(KEY_PIN_SALT)
            .putBoolean(KEY_LOCK_ENABLED, false)
            .apply()
    }

    fun recordUserActivity() {
        prefs.edit().putLong(KEY_LAST_ACTIVE, System.currentTimeMillis()).apply()
    }

    private fun hashPin(pin: String, salt: ByteArray): ByteArray {
        val spec = PBEKeySpec(pin.toCharArray(), salt, ITERATIONS, KEY_LENGTH)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        return factory.generateSecret(spec).encoded
    }

    // Encrypted Backup Generator
    suspend fun createEncryptedBackup(
        database: AppDatabase,
        businessId: String,
        password: String
    ): File = withContext(Dispatchers.IO) {
        val business = database.businessDao().getBusinessById(businessId) ?: throw IllegalStateException("Business not found")
        val parties = database.partyDao().getAllPartiesIncludingArchived(businessId).first()
        val txs = database.transactionDao().getTransactionsByBusiness(businessId).first()
        val accounts = database.accountDao().getAccountsByBusiness(businessId).first()
        val categories = database.categoryDao().getCategoriesByBusiness(businessId).first()
        val auditLogs = database.auditLogDao().getAuditLogs(businessId).first()

        val rootJson = JSONObject()
        rootJson.put("version", 1)
        rootJson.put("createdAt", System.currentTimeMillis())

        // Business
        val bJson = JSONObject().apply {
            put("id", business.id)
            put("name", business.name)
            put("ownerName", business.ownerName ?: "")
            put("businessType", business.businessType)
            put("phone", business.phone ?: "")
            put("gstin", business.gstin ?: "")
            put("pan", business.pan ?: "")
            put("currencyCode", business.currencyCode)
            put("upiId", business.upiId ?: "")
            put("address", business.address ?: "")
            put("createdAt", business.createdAt)
            put("updatedAt", business.updatedAt)
        }
        rootJson.put("business", bJson)

        // Parties
        val partiesArray = JSONArray()
        for (p in parties) {
            val pObj = JSONObject().apply {
                put("id", p.id)
                put("businessId", p.businessId)
                put("name", p.name)
                put("phone", p.phone ?: "")
                put("email", p.email ?: "")
                put("address", p.address ?: "")
                put("gstin", p.gstin ?: "")
                put("pan", p.pan ?: "")
                put("openingBalancePaise", p.openingBalancePaise)
                put("creditLimitPaise", p.creditLimitPaise ?: -1L)
                put("paymentTermsDays", p.paymentTermsDays ?: -1)
                put("notes", p.notes ?: "")
                put("tags", p.tags ?: "")
                put("roles", p.roles)
                put("isArchived", p.isArchived)
                put("createdAt", p.createdAt)
                put("updatedAt", p.updatedAt)
            }
            partiesArray.put(pObj)
        }
        rootJson.put("parties", partiesArray)

        // Transactions
        val txArray = JSONArray()
        for (t in txs) {
            val tObj = JSONObject().apply {
                put("id", t.id)
                put("businessId", t.businessId)
                put("partyId", t.partyId ?: "")
                put("accountId", t.accountId ?: "")
                put("destinationAccountId", t.destinationAccountId ?: "")
                put("type", t.type)
                put("amountPaise", t.amountPaise)
                put("transactionDate", t.transactionDate)
                put("dueDate", t.dueDate ?: -1L)
                put("referenceNumber", t.referenceNumber ?: "")
                put("paymentMode", t.paymentMode)
                put("categoryId", t.categoryId ?: "")
                put("notes", t.notes ?: "")
                put("status", t.status)
                put("reversalTransactionId", t.reversalTransactionId ?: "")
                put("voidReason", t.voidReason ?: "")
                put("createdAt", t.createdAt)
                put("updatedAt", t.updatedAt)
            }
            txArray.put(tObj)
        }
        rootJson.put("transactions", txArray)

        // Accounts
        val accArray = JSONArray()
        for (a in accounts) {
            val aObj = JSONObject().apply {
                put("id", a.id)
                put("businessId", a.businessId)
                put("name", a.name)
                put("type", a.type)
                put("accountNumber", a.accountNumber ?: "")
                put("ifscCode", a.ifscCode ?: "")
                put("upiId", a.upiId ?: "")
                put("openingBalancePaise", a.openingBalancePaise)
                put("isArchived", a.isArchived)
                put("createdAt", a.createdAt)
                put("updatedAt", a.updatedAt)
            }
            accArray.put(aObj)
        }
        rootJson.put("accounts", accArray)

        // Encrypt with AES-GCM
        val plaintext = rootJson.toString().toByteArray(StandardCharsets.UTF_8)
        val salt = ByteArray(16)
        SecureRandom().nextBytes(salt)
        val iv = ByteArray(12)
        SecureRandom().nextBytes(iv)

        val keySpec = PBEKeySpec(password.toCharArray(), salt, 10000, 256)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val secretKey = SecretKeySpec(factory.generateSecret(keySpec).encoded, "AES")

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, GCMParameterSpec(128, iv))
        val ciphertext = cipher.doFinal(plaintext)

        // Checksum of plaintext for verification
        val digest = MessageDigest.getInstance("SHA-256")
        val checksum = digest.digest(plaintext)

        val backupDir = File(context.cacheDir, "backups").apply { mkdirs() }
        val backupFile = File(backupDir, "${business.name.replace(" ", "_")}_backup_${System.currentTimeMillis()}.lpbackup")
        val fos = FileOutputStream(backupFile)
        // Write header: MAGIC(4) + Salt(16) + IV(12) + SHA256(32) + Ciphertext
        fos.write("LPBK".toByteArray(StandardCharsets.UTF_8))
        fos.write(salt)
        fos.write(iv)
        fos.write(checksum)
        fos.write(ciphertext)
        fos.flush()
        fos.close()

        backupFile
    }

    // Inspect Backup Header & Verify Password
    suspend fun inspectBackup(file: File, password: String): BackupMetadata = withContext(Dispatchers.IO) {
        val rootJson = decryptBackupJson(file, password)
        val bObj = rootJson.getJSONObject("business")
        val partiesArr = rootJson.getJSONArray("parties")
        val txArr = rootJson.getJSONArray("transactions")
        val accArr = rootJson.getJSONArray("accounts")

        BackupMetadata(
            backupId = file.name,
            businessName = bObj.getString("name"),
            businessId = bObj.getString("id"),
            partyCount = partiesArr.length(),
            transactionCount = txArr.length(),
            accountCount = accArr.length(),
            createdAt = rootJson.optLong("createdAt", file.lastModified())
        )
    }

    // Restore Backup into Database
    suspend fun restoreBackup(
        database: AppDatabase,
        file: File,
        password: String
    ): Unit = withContext(Dispatchers.IO) {
        val rootJson = decryptBackupJson(file, password)
        val bObj = rootJson.getJSONObject("business")
        val business = BusinessEntity(
            id = bObj.getString("id"),
            name = bObj.getString("name"),
            ownerName = bObj.optString("ownerName").takeIf { it.isNotEmpty() },
            businessType = bObj.optString("businessType", "Retail"),
            phone = bObj.optString("phone").takeIf { it.isNotEmpty() },
            gstin = bObj.optString("gstin").takeIf { it.isNotEmpty() },
            pan = bObj.optString("pan").takeIf { it.isNotEmpty() },
            currencyCode = bObj.optString("currencyCode", "INR"),
            upiId = bObj.optString("upiId").takeIf { it.isNotEmpty() },
            address = bObj.optString("address").takeIf { it.isNotEmpty() },
            createdAt = bObj.optLong("createdAt", System.currentTimeMillis()),
            updatedAt = System.currentTimeMillis(),
            isDefault = true
        )
        database.businessDao().clearDefault()
        database.businessDao().insertBusiness(business)

        // Restore Parties
        val partiesArr = rootJson.getJSONArray("parties")
        for (i in 0 until partiesArr.length()) {
            val p = partiesArr.getJSONObject(i)
            database.partyDao().insertParty(
                PartyEntity(
                    id = p.getString("id"),
                    businessId = p.getString("businessId"),
                    name = p.getString("name"),
                    phone = p.optString("phone").takeIf { it.isNotEmpty() },
                    email = p.optString("email").takeIf { it.isNotEmpty() },
                    address = p.optString("address").takeIf { it.isNotEmpty() },
                    gstin = p.optString("gstin").takeIf { it.isNotEmpty() },
                    pan = p.optString("pan").takeIf { it.isNotEmpty() },
                    openingBalancePaise = p.optLong("openingBalancePaise", 0L),
                    creditLimitPaise = p.optLong("creditLimitPaise").takeIf { it > 0 },
                    paymentTermsDays = p.optInt("paymentTermsDays").takeIf { it > 0 },
                    notes = p.optString("notes").takeIf { it.isNotEmpty() },
                    tags = p.optString("tags").takeIf { it.isNotEmpty() },
                    roles = p.optString("roles", "CUSTOMER"),
                    isArchived = p.optBoolean("isArchived", false),
                    createdAt = p.optLong("createdAt", System.currentTimeMillis()),
                    updatedAt = p.optLong("updatedAt", System.currentTimeMillis())
                )
            )
        }

        // Restore Accounts
        val accArr = rootJson.getJSONArray("accounts")
        for (i in 0 until accArr.length()) {
            val a = accArr.getJSONObject(i)
            database.accountDao().insertAccount(
                AccountEntity(
                    id = a.getString("id"),
                    businessId = a.getString("businessId"),
                    name = a.getString("name"),
                    type = a.optString("type", "CASH"),
                    accountNumber = a.optString("accountNumber").takeIf { it.isNotEmpty() },
                    ifscCode = a.optString("ifscCode").takeIf { it.isNotEmpty() },
                    upiId = a.optString("upiId").takeIf { it.isNotEmpty() },
                    openingBalancePaise = a.optLong("openingBalancePaise", 0L),
                    isArchived = a.optBoolean("isArchived", false),
                    createdAt = a.optLong("createdAt", System.currentTimeMillis()),
                    updatedAt = a.optLong("updatedAt", System.currentTimeMillis())
                )
            )
        }

        // Restore Transactions
        val txArr = rootJson.getJSONArray("transactions")
        for (i in 0 until txArr.length()) {
            val t = txArr.getJSONObject(i)
            database.transactionDao().insertTransaction(
                TransactionEntity(
                    id = t.getString("id"),
                    businessId = t.getString("businessId"),
                    partyId = t.optString("partyId").takeIf { it.isNotEmpty() },
                    accountId = t.optString("accountId").takeIf { it.isNotEmpty() },
                    destinationAccountId = t.optString("destinationAccountId").takeIf { it.isNotEmpty() },
                    type = t.getString("type"),
                    amountPaise = t.getLong("amountPaise"),
                    transactionDate = t.optLong("transactionDate", System.currentTimeMillis()),
                    dueDate = t.optLong("dueDate").takeIf { it > 0 },
                    referenceNumber = t.optString("referenceNumber").takeIf { it.isNotEmpty() },
                    paymentMode = t.optString("paymentMode", "CASH"),
                    categoryId = t.optString("categoryId").takeIf { it.isNotEmpty() },
                    notes = t.optString("notes").takeIf { it.isNotEmpty() },
                    status = t.optString("status", "POSTED"),
                    reversalTransactionId = t.optString("reversalTransactionId").takeIf { it.isNotEmpty() },
                    voidReason = t.optString("voidReason").takeIf { it.isNotEmpty() },
                    createdAt = t.optLong("createdAt", System.currentTimeMillis()),
                    updatedAt = t.optLong("updatedAt", System.currentTimeMillis())
                )
            )
        }

        database.auditLogDao().insertAuditLog(
            AuditLogEntity(
                businessId = business.id,
                action = "RESTORE_BACKUP",
                entityType = "Backup",
                entityId = file.name,
                details = "Restored ${partiesArr.length()} parties and ${txArr.length()} transactions from backup."
            )
        )
    }

    private fun decryptBackupJson(file: File, password: String): JSONObject {
        val fis = FileInputStream(file)
        val header = ByteArray(4)
        fis.read(header)
        val magic = String(header, StandardCharsets.UTF_8)
        if (magic != "LPBK") {
            throw IllegalArgumentException("Invalid backup format or corrupted file")
        }

        val salt = ByteArray(16)
        fis.read(salt)
        val iv = ByteArray(12)
        fis.read(iv)
        val expectedChecksum = ByteArray(32)
        fis.read(expectedChecksum)

        val ciphertext = fis.readBytes()
        fis.close()

        val keySpec = PBEKeySpec(password.toCharArray(), salt, 10000, 256)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val secretKey = SecretKeySpec(factory.generateSecret(keySpec).encoded, "AES")

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, secretKey, GCMParameterSpec(128, iv))
        val plaintext = cipher.doFinal(ciphertext)

        // Verify SHA-256 Checksum
        val digest = MessageDigest.getInstance("SHA-256")
        val computedChecksum = digest.digest(plaintext)
        if (!MessageDigest.isEqual(expectedChecksum, computedChecksum)) {
            throw IllegalStateException("Backup integrity checksum mismatch! File may be altered.")
        }

        return JSONObject(String(plaintext, StandardCharsets.UTF_8))
    }
}
