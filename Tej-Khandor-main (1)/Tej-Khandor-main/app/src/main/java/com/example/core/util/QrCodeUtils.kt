package com.example.core.util

import android.graphics.Bitmap
import android.graphics.Color as AndroidColor
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel
import java.net.URLEncoder
import java.util.EnumMap

object QrCodeUtils {

    /**
     * Builds standard NPCI UPI Payment URI string:
     * upi://pay?pa=<upiId>&pn=<payeeName>&am=<amountFormatted>&cu=INR&tn=<note>
     */
    fun buildUpiUri(
        upiId: String,
        payeeName: String,
        amountRupees: Double? = null,
        note: String? = null
    ): String {
        val cleanUpi = upiId.trim()
        val cleanName = URLEncoder.encode(payeeName.trim(), "UTF-8")
        val sb = StringBuilder("upi://pay?pa=$cleanUpi&pn=$cleanName&cu=INR")

        if (amountRupees != null && amountRupees > 0) {
            sb.append(String.format(java.util.Locale.US, "&am=%.2f", amountRupees))
        }

        if (!note.isNullOrBlank()) {
            val encodedNote = URLEncoder.encode(note.trim(), "UTF-8")
            sb.append("&tn=$encodedNote")
        }

        return sb.toString()
    }

    /**
     * Generates an Android Bitmap for any QR payload text.
     */
    fun generateQrBitmap(
        content: String,
        sizePx: Int = 512,
        foregroundHex: Int = AndroidColor.BLACK,
        backgroundHex: Int = AndroidColor.WHITE
    ): Bitmap? {
        if (content.isBlank()) return null
        return try {
            val hints = EnumMap<EncodeHintType, Any>(EncodeHintType::class.java).apply {
                put(EncodeHintType.CHARACTER_SET, "UTF-8")
                put(EncodeHintType.ERROR_CORRECTION, ErrorCorrectionLevel.M)
                put(EncodeHintType.MARGIN, 1)
            }

            val bitMatrix = QRCodeWriter().encode(
                content,
                BarcodeFormat.QR_CODE,
                sizePx,
                sizePx,
                hints
            )

            val width = bitMatrix.width
            val height = bitMatrix.height
            val pixels = IntArray(width * height)

            for (y in 0 until height) {
                val offset = y * width
                for (x in 0 until width) {
                    pixels[offset + x] = if (bitMatrix.get(x, y)) foregroundHex else backgroundHex
                }
            }

            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            bitmap.setPixels(pixels, 0, width, 0, 0, width, height)
            bitmap
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * Generates a Compose ImageBitmap for direct display in Image().
     */
    fun generateQrImageBitmap(
        content: String,
        sizePx: Int = 512,
        foregroundHex: Int = AndroidColor.BLACK,
        backgroundHex: Int = AndroidColor.WHITE
    ): ImageBitmap? {
        return generateQrBitmap(content, sizePx, foregroundHex, backgroundHex)?.asImageBitmap()
    }
}
