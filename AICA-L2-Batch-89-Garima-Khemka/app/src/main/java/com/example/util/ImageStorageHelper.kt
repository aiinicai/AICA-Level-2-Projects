package com.example.util

import android.content.Context
import android.net.Uri
import java.io.File
import java.io.FileOutputStream

object ImageStorageHelper {

    fun saveImageToInternalStorage(context: Context, sourceUri: Uri, prefix: String = "prescription"): String {
        return try {
            val directory = File(context.filesDir, "saved_prescriptions").apply {
                if (!exists()) {
                    mkdirs()
                }
            }
            val destinationFile = File(directory, "${prefix}_${System.currentTimeMillis()}.jpg")
            context.contentResolver.openInputStream(sourceUri)?.use { inputStream ->
                FileOutputStream(destinationFile).use { outputStream ->
                    inputStream.copyTo(outputStream)
                }
            }
            Uri.fromFile(destinationFile).toString()
        } catch (_: Exception) {
            sourceUri.toString()
        }
    }
}
