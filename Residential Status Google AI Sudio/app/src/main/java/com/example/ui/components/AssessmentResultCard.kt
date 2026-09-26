package com.example.ui.components

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BookmarkAdd
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.FemaResult
import com.example.model.IncomeTaxResult
import com.example.ui.theme.GoldAccent
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted

@Composable
fun IncomeTaxResultCard(
    result: IncomeTaxResult,
    onSaveToHistory: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var showFullRationale by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .testTag("it_result_card"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "DETERMINATION RESULT",
                    style = MaterialTheme.typography.labelSmall.copy(
                        letterSpacing = 1.2.sp,
                        fontWeight = FontWeight.Bold
                    ),
                    color = SlateMuted
                )
                Text(
                    text = "INCOME TAX ACT",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Status Badge
            IncomeTaxStatusBadge(
                status = result.status,
                isLarge = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Statutory Provision Banner
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = PrimaryNavy,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = result.statutoryProvision,
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace
                        ),
                        color = PrimaryNavy
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Executive Summary
            Text(
                text = result.executiveSummary,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                color = MaterialTheme.colorScheme.onSurface
            )

            Spacer(modifier = Modifier.height(14.dp))
            HorizontalDivider(color = SlateBorder)
            Spacer(modifier = Modifier.height(14.dp))

            // Key Factors Box
            Text(
                text = "Key Determination Factors",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                color = PrimaryNavy
            )
            Spacer(modifier = Modifier.height(8.dp))

            result.keyFactors.forEach { (key, value) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 3.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = key,
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )
                    Text(
                        text = value,
                        style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Rationale Dropdown
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .border(1.dp, SlateBorder, RoundedCornerShape(8.dp)),
                color = MaterialTheme.colorScheme.surface,
                onClick = { showFullRationale = !showFullRationale }
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (showFullRationale) "Hide Statutory Rationale" else "View Detailed Statutory Rationale",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                    Icon(
                        imageVector = if (showFullRationale) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = null,
                        tint = PrimaryNavy
                    )
                }
            }

            AnimatedVisibility(visible = showFullRationale) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    result.rationale.forEach { bullet ->
                        Row(verticalAlignment = Alignment.Top) {
                            Text(text = "•", color = PrimaryNavy, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = bullet,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }

            // Tax Implications
            if (result.taxImplications.isNotEmpty()) {
                Spacer(modifier = Modifier.height(14.dp))
                Text(
                    text = "Tax Implications under the Act",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Spacer(modifier = Modifier.height(6.dp))
                result.taxImplications.forEach { imp ->
                    Row(
                        modifier = Modifier.padding(vertical = 2.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            imageVector = Icons.Default.CheckCircle,
                            contentDescription = null,
                            tint = GoldAccent,
                            modifier = Modifier
                                .size(14.dp)
                                .padding(top = 2.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = imp,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            // Caveats
            if (result.caveats.isNotEmpty()) {
                Spacer(modifier = Modifier.height(10.dp))
                result.caveats.forEach { caveat ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 3.dp),
                        color = Color(0xFFFFF8E1),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(8.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Icon(
                                imageVector = Icons.Default.WarningAmber,
                                contentDescription = null,
                                tint = Color(0xFFB78103),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = caveat,
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = Color(0xFF7A5400)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onSaveToHistory,
                    modifier = Modifier
                        .weight(1f)
                        .testTag("it_save_btn"),
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryNavy),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.BookmarkAdd,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Save")
                }

                OutlinedButton(
                    onClick = {
                        val reportText = buildFormalReport(result)
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        val clip = ClipData.newPlainText("Residential Status Assessment", reportText)
                        clipboard.setPrimaryClip(clip)
                        Toast.makeText(context, "Assessment copied to clipboard!", Toast.LENGTH_SHORT).show()
                    },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("it_copy_btn"),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Copy")
                }

                OutlinedButton(
                    onClick = {
                        val reportText = buildFormalReport(result)
                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, reportText)
                            type = "text/plain"
                        }
                        val shareIntent = Intent.createChooser(sendIntent, "Share Assessment Report")
                        context.startActivity(shareIntent)
                    },
                    modifier = Modifier.testTag("it_share_btn"),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Share,
                        contentDescription = "Share",
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun FemaResultCard(
    result: FemaResult,
    onSaveToHistory: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var showFullRationale by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .testTag("fema_result_card"),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "DETERMINATION RESULT",
                    style = MaterialTheme.typography.labelSmall.copy(
                        letterSpacing = 1.2.sp,
                        fontWeight = FontWeight.Bold
                    ),
                    color = SlateMuted
                )
                Text(
                    text = "FEMA, 1999 (SEC 2(v))",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Status Badge
            FemaStatusBadge(
                status = result.status,
                isLarge = true,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Statutory Provision Banner
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.surfaceVariant,
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = PrimaryNavy,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = result.statutoryProvision,
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace
                        ),
                        color = PrimaryNavy
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Executive Summary
            Text(
                text = result.executiveSummary,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                color = MaterialTheme.colorScheme.onSurface
            )

            Spacer(modifier = Modifier.height(14.dp))
            HorizontalDivider(color = SlateBorder)
            Spacer(modifier = Modifier.height(14.dp))

            // Key Factors Box
            Text(
                text = "Key Determination Factors",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                color = PrimaryNavy
            )
            Spacer(modifier = Modifier.height(8.dp))

            result.keyFactors.forEach { (key, value) ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 3.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = key,
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )
                    Text(
                        text = value,
                        style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Rationale Dropdown
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .border(1.dp, SlateBorder, RoundedCornerShape(8.dp)),
                color = MaterialTheme.colorScheme.surface,
                onClick = { showFullRationale = !showFullRationale }
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (showFullRationale) "Hide Statutory Rationale" else "View Detailed Statutory Rationale",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                    Icon(
                        imageVector = if (showFullRationale) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = null,
                        tint = PrimaryNavy
                    )
                }
            }

            AnimatedVisibility(visible = showFullRationale) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    result.rationale.forEach { bullet ->
                        Row(verticalAlignment = Alignment.Top) {
                            Text(text = "•", color = PrimaryNavy, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = bullet,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }

            // Banking Implications
            if (result.bankingImplications.isNotEmpty()) {
                Spacer(modifier = Modifier.height(14.dp))
                Text(
                    text = "FEMA Banking & Accounts",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Spacer(modifier = Modifier.height(6.dp))
                result.bankingImplications.forEach { bank ->
                    Row(
                        modifier = Modifier.padding(vertical = 2.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Icon(
                            imageVector = Icons.Default.CheckCircle,
                            contentDescription = null,
                            tint = GoldAccent,
                            modifier = Modifier
                                .size(14.dp)
                                .padding(top = 2.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = bank,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            // Compliance Notes
            if (result.complianceNotes.isNotEmpty()) {
                Spacer(modifier = Modifier.height(10.dp))
                result.complianceNotes.forEach { note ->
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 3.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(8.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Icon(
                                imageVector = Icons.Default.Info,
                                contentDescription = null,
                                tint = PrimaryNavy,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = note,
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onSaveToHistory,
                    modifier = Modifier
                        .weight(1f)
                        .testTag("fema_save_btn"),
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryNavy),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.BookmarkAdd,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Save")
                }

                OutlinedButton(
                    onClick = {
                        val reportText = buildFormalFemaReport(result)
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        val clip = ClipData.newPlainText("FEMA Residential Status Assessment", reportText)
                        clipboard.setPrimaryClip(clip)
                        Toast.makeText(context, "Assessment copied to clipboard!", Toast.LENGTH_SHORT).show()
                    },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("fema_copy_btn"),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Copy")
                }

                OutlinedButton(
                    onClick = {
                        val reportText = buildFormalFemaReport(result)
                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, reportText)
                            type = "text/plain"
                        }
                        val shareIntent = Intent.createChooser(sendIntent, "Share FEMA Assessment Report")
                        context.startActivity(shareIntent)
                    },
                    modifier = Modifier.testTag("fema_share_btn"),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Share,
                        contentDescription = "Share",
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

private fun buildFormalReport(res: IncomeTaxResult): String {
    return buildString {
        appendLine("====================================================")
        appendLine("P. R. BHUTA & CO. CHARTERED ACCOUNTANTS")
        appendLine("STATUTORY RESIDENTIAL STATUS DETERMINATION REPORT")
        appendLine("Under ${res.keyFactors["Governing Act"] ?: "Income Tax Act Rules"}")
        appendLine("====================================================")
        appendLine("STATUS: ${res.status.code} - ${res.status.title}")
        appendLine("STATUTORY PROVISION: ${res.statutoryProvision}")
        appendLine("----------------------------------------------------")
        appendLine("EXECUTIVE SUMMARY:")
        appendLine(res.executiveSummary)
        appendLine("----------------------------------------------------")
        appendLine("KEY FACTORS:")
        res.keyFactors.forEach { (k, v) -> appendLine("• $k: $v") }
        appendLine("----------------------------------------------------")
        appendLine("STATUTORY RATIONALE:")
        res.rationale.forEach { appendLine("• $it") }
        appendLine("----------------------------------------------------")
        appendLine("TAX IMPLICATIONS:")
        res.taxImplications.forEach { appendLine("• $it") }
        if (res.caveats.isNotEmpty()) {
            appendLine("----------------------------------------------------")
            appendLine("CAVEATS / STATUTORY COMPLIANCE:")
            res.caveats.forEach { appendLine("! $it") }
        }
        appendLine("====================================================")
        appendLine("Generated by P.R. Bhuta CAs Residential Status System")
    }
}

private fun buildFormalFemaReport(res: FemaResult): String {
    return buildString {
        appendLine("====================================================")
        appendLine("P. R. BHUTA & CO. CHARTERED ACCOUNTANTS")
        appendLine("FEMA RESIDENTIAL STATUS DETERMINATION REPORT")
        appendLine("Under FEMA, 1999 Provisions")
        appendLine("====================================================")
        appendLine("STATUS: ${res.status.code} - ${res.status.title}")
        appendLine("STATUTORY PROVISION: ${res.statutoryProvision}")
        appendLine("----------------------------------------------------")
        appendLine("EXECUTIVE SUMMARY:")
        appendLine(res.executiveSummary)
        appendLine("----------------------------------------------------")
        appendLine("KEY FACTORS:")
        res.keyFactors.forEach { (k, v) -> appendLine("• $k: $v") }
        appendLine("----------------------------------------------------")
        appendLine("STATUTORY RATIONALE:")
        res.rationale.forEach { appendLine("• $it") }
        appendLine("----------------------------------------------------")
        appendLine("BANKING & ACCOUNT REGULATIONS:")
        res.bankingImplications.forEach { appendLine("• $it") }
        if (res.complianceNotes.isNotEmpty()) {
            appendLine("----------------------------------------------------")
            appendLine("REGULATORY COMPLIANCE NOTES:")
            res.complianceNotes.forEach { appendLine("• $it") }
        }
        appendLine("====================================================")
        appendLine("Generated by P.R. Bhuta CAs Residential Status System")
    }
}
