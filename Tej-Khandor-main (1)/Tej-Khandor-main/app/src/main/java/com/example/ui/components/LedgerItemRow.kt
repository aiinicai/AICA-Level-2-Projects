package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.SyncAlt
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.core.model.Money
import com.example.core.model.TransactionStatus
import com.example.core.repository.LedgerItem
import com.example.ui.theme.CrimsonContainer
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldContainer
import com.example.ui.theme.EmeraldPrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun LedgerItemRow(
    item: LedgerItem,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val tx = item.transaction
    val isVoided = tx.status == TransactionStatus.VOIDED.name
    val isReversed = tx.status == TransactionStatus.REVERSED.name
    val dateFormat = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.ENGLISH)
    val dateStr = dateFormat.format(Date(tx.transactionDate))

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .clickable { onClick() },
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isVoided) MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
            else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            // Top row: Date + Status Badges
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = dateStr,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (isVoided) {
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MaterialTheme.colorScheme.errorContainer
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.Block, "Voided", modifier = Modifier.size(10.dp), tint = MaterialTheme.colorScheme.error)
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("VOIDED", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                            }
                        }
                    } else if (isReversed) {
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MaterialTheme.colorScheme.secondaryContainer
                        ) {
                            Text("REVERSED", fontSize = 9.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
                        }
                    }

                    // Due date badge if applicable
                    if (tx.dueDate != null && !isVoided) {
                        val now = System.currentTimeMillis()
                        val diffDays = ((tx.dueDate - now) / (24 * 60 * 60 * 1000L)).toInt()
                        val dueFormat = SimpleDateFormat("dd MMM", Locale.ENGLISH)
                        val dueStr = dueFormat.format(Date(tx.dueDate))
                        val isOverdue = tx.dueDate < now

                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = if (isOverdue) CrimsonContainer.copy(alpha = 0.8f) else MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.7f)
                        ) {
                            Text(
                                text = if (isOverdue) "Overdue (Due $dueStr)" else "Due $dueStr",
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isOverdue) CrimsonPrimary else MaterialTheme.colorScheme.onTertiaryContainer,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }

                    // Payment mode chip
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant
                    ) {
                        Text(
                            text = tx.paymentMode,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Middle row: Description/Notes & Amount (Debit/Credit)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    val desc = if (!tx.notes.isNullOrBlank()) tx.notes else tx.type
                    Text(
                        text = desc,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        textDecoration = if (isVoided) TextDecoration.LineThrough else TextDecoration.None
                    )
                    if (!tx.referenceNumber.isNullOrEmpty()) {
                        Text(
                            text = "Ref: ${tx.referenceNumber}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Debit or Credit Display
                Column(horizontalAlignment = Alignment.End) {
                    if (item.debitPaise > 0) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = EmeraldContainer
                        ) {
                            Text(
                                text = "+${Money.formatIndianPaise(item.debitPaise)}",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = EmeraldPrimary,
                                textDecoration = if (isVoided) TextDecoration.LineThrough else TextDecoration.None,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                            )
                        }
                        val debitLabel = when (tx.type) {
                            "PAYMENT_TO_SUPPLIER" -> "Paid to Supplier (+)"
                            "OPENING_BALANCE" -> "Opening Balance (+)"
                            "SALE" -> "Sale on Credit (+)"
                            else -> "You Gave (Lena +)"
                        }
                        Text(
                            text = debitLabel,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = EmeraldPrimary,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    } else if (item.creditPaise > 0) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = CrimsonContainer
                        ) {
                            Text(
                                text = "-${Money.formatIndianPaise(item.creditPaise)}",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = CrimsonPrimary,
                                textDecoration = if (isVoided) TextDecoration.LineThrough else TextDecoration.None,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                            )
                        }
                        val creditLabel = when (tx.type) {
                            "PURCHASE" -> "Credit from Supplier (-)"
                            "OPENING_BALANCE" -> "Opening Balance (-)"
                            else -> "You Got (Jama -)"
                        }
                        Text(
                            text = creditLabel,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = CrimsonPrimary,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Bottom row: Running balance
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                Text(
                    text = "Balance: ${Money.formatIndianPaise(item.runningBalancePaise)}",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
