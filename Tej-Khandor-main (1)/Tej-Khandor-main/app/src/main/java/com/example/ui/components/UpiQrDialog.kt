package com.example.ui.components

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.core.model.BusinessEntity
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.util.QrCodeUtils
import com.example.ui.theme.EmeraldPrimary

@Composable
fun UpiQrDialog(
    business: BusinessEntity,
    party: PartyEntity? = null,
    initialAmountRupees: Double? = null,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var upiId by remember {
        mutableStateOf(business.upiId?.takeIf { it.isNotEmpty() } ?: "merchant@upi")
    }
    var isEditingUpi by remember { mutableStateOf(business.upiId.isNullOrBlank()) }
    var amountStr by remember {
        mutableStateOf(
            if (initialAmountRupees != null && initialAmountRupees > 0) {
                String.format(java.util.Locale.US, "%.0f", initialAmountRupees)
            } else ""
        )
    }
    var note by remember {
        mutableStateOf(if (party != null) "Payment from ${party.name}" else "Payment to ${business.name}")
    }

    val amountDouble = amountStr.toDoubleOrNull()
    val upiPayload = remember(upiId, business.name, amountDouble, note) {
        QrCodeUtils.buildUpiUri(
            upiId = upiId,
            payeeName = business.ownerName ?: business.name,
            amountRupees = amountDouble,
            note = note
        )
    }

    val qrBitmap = remember(upiPayload) {
        QrCodeUtils.generateQrImageBitmap(upiPayload, sizePx = 600)
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .background(EmeraldPrimary.copy(alpha = 0.15f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.QrCode, contentDescription = null, tint = EmeraldPrimary, modifier = Modifier.size(20.dp))
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text("UPI Payment QR", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        Text(business.name, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // QR Code Container
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                    modifier = Modifier.padding(vertical = 4.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        if (qrBitmap != null) {
                            Image(
                                bitmap = qrBitmap,
                                contentDescription = "UPI QR Code",
                                modifier = Modifier
                                    .size(210.dp)
                                    .clip(RoundedCornerShape(8.dp)),
                                contentScale = ContentScale.Fit
                            )
                        } else {
                            Box(
                                modifier = Modifier
                                    .size(210.dp)
                                    .background(Color.LightGray.copy(alpha = 0.3f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("Please enter a valid UPI ID", color = Color.Gray, fontSize = 12.sp)
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Amount / Scan & Pay label
                        if (amountDouble != null && amountDouble > 0) {
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = EmeraldPrimary.copy(alpha = 0.12f)
                            ) {
                                Text(
                                    text = "Pay ₹${String.format(java.util.Locale.US, "%,.2f", amountDouble)}",
                                    fontWeight = FontWeight.ExtraBold,
                                    fontSize = 18.sp,
                                    color = EmeraldPrimary,
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp)
                                )
                            }
                        } else {
                            Text(
                                text = "Scan & Pay Any Amount",
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp,
                                color = Color.DarkGray
                            )
                        }

                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Accepts GPay, PhonePe, Paytm, BHIM & all UPI apps",
                            fontSize = 10.sp,
                            color = Color.Gray,
                            textAlign = TextAlign.Center
                        )
                    }
                }

                // UPI ID Configuration
                if (isEditingUpi) {
                    OutlinedTextField(
                        value = upiId,
                        onValueChange = { upiId = it },
                        label = { Text("Your Shop UPI ID *") },
                        placeholder = { Text("merchant@upi / 9876543210@paytm") },
                        trailingIcon = {
                            IconButton(onClick = { isEditingUpi = false }) {
                                Icon(Icons.Default.Check, contentDescription = "Save")
                            }
                        },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                } else {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text("UPI ID", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(upiId, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                            }
                            Row {
                                IconButton(
                                    onClick = {
                                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        clipboard.setPrimaryClip(ClipData.newPlainText("UPI ID", upiId))
                                        Toast.makeText(context, "UPI ID copied", Toast.LENGTH_SHORT).show()
                                    },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(Icons.Default.ContentCopy, contentDescription = "Copy", modifier = Modifier.size(16.dp))
                                }
                                IconButton(
                                    onClick = { isEditingUpi = true },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(Icons.Default.Edit, contentDescription = "Edit", modifier = Modifier.size(16.dp))
                                }
                            }
                        }
                    }
                }

                // Custom Amount Input
                OutlinedTextField(
                    value = amountStr,
                    onValueChange = { amountStr = it },
                    label = { Text("Request Specific Amount (₹) [Optional]") },
                    placeholder = { Text("Leave blank for any amount") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Quick Amount Chips
                if (initialAmountRupees != null && initialAmountRupees > 0) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        FilterChip(
                            selected = amountStr == String.format(java.util.Locale.US, "%.0f", initialAmountRupees),
                            onClick = { amountStr = String.format(java.util.Locale.US, "%.0f", initialAmountRupees) },
                            label = { Text("Full: ₹${initialAmountRupees.toInt()}", fontSize = 11.sp) }
                        )
                        FilterChip(
                            selected = amountStr.isEmpty(),
                            onClick = { amountStr = "" },
                            label = { Text("Any Amount", fontSize = 11.sp) }
                        )
                    }
                }
            }
        },
        confirmButton = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("UPI Link", upiPayload))
                        Toast.makeText(context, "UPI Payment link copied", Toast.LENGTH_SHORT).show()
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Copy Link", fontSize = 12.sp)
                }

                Button(
                    onClick = {
                        val shareText = buildString {
                            append("Dear Customer,\n")
                            if (amountDouble != null && amountDouble > 0) {
                                append("Please pay ₹${String.format(java.util.Locale.US, "%.2f", amountDouble)} to ${business.name}.\n\n")
                            } else {
                                append("Please pay to ${business.name}.\n\n")
                            }
                            append("UPI ID: $upiId\n")
                            append("Payment Link: $upiPayload\n\n")
                            append("Pay using Google Pay, PhonePe, Paytm or any UPI App.")
                        }
                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_SUBJECT, "UPI Payment to ${business.name}")
                            putExtra(Intent.EXTRA_TEXT, shareText)
                        }
                        context.startActivity(Intent.createChooser(shareIntent, "Share Payment QR & Link"))
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Share", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }
        },
        dismissButton = {}
    )
}
