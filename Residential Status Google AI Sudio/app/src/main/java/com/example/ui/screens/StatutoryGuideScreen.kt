package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.RegulatoryGuideData
import com.example.ui.theme.GoldAccent
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted

@Composable
fun StatutoryGuideScreen(modifier: Modifier = Modifier) {
    val scrollState = rememberScrollState()
    val expandedStates = remember {
        mutableStateMapOf<Int, Boolean>().apply {
            // First topic expanded by default
            put(0, true)
            put(1, true)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("guide_screen"),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // --- Header Card ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.MenuBook,
                        contentDescription = null,
                        tint = PrimaryNavy,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Statutory Reference & CA Guide",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Authored by P. R. Bhuta & Co. Chartered Accountants for tax practitioners, CAs, and NRI clients navigating Indian tax and foreign exchange residency.",
                    style = MaterialTheme.typography.bodySmall,
                    color = SlateMuted
                )
            }
        }

        // --- Quick Summary Matrix: Scope of Income ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Scope of Total Income Taxability Matrix",
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Spacer(modifier = Modifier.height(10.dp))

                // Scope table
                ScopeTableRow(
                    type = "Income received / accrued in India",
                    ror = "Taxable",
                    rnor = "Taxable",
                    nr = "Taxable"
                )
                ScopeTableRow(
                    type = "Income deemed to accrue in India",
                    ror = "Taxable",
                    rnor = "Taxable",
                    nr = "Taxable"
                )
                ScopeTableRow(
                    type = "Foreign business controlled in India",
                    ror = "Taxable",
                    rnor = "Taxable",
                    nr = "Not Taxable"
                )
                ScopeTableRow(
                    type = "Foreign pure income (salary/dividend/rent)",
                    ror = "Taxable",
                    rnor = "Exempt",
                    nr = "Exempt"
                )
            }
        }

        // --- Detailed Topic Accordions ---
        RegulatoryGuideData.topics.forEachIndexed { index, topic ->
            val isExpanded = expandedStates[index] ?: false

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { expandedStates[index] = !isExpanded },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(PrimaryNavy.copy(alpha = 0.08f))
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = "${topic.act} • Residency Guidelines",
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 10.sp
                                    ),
                                    color = PrimaryNavy
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = topic.title,
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = PrimaryNavy
                            )
                        }

                        Icon(
                            imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                            contentDescription = null,
                            tint = PrimaryNavy
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = topic.summary,
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )

                    AnimatedVisibility(visible = isExpanded) {
                        Column(modifier = Modifier.padding(top = 12.dp)) {
                            HorizontalDivider(color = SlateBorder)
                            Spacer(modifier = Modifier.height(10.dp))

                            topic.keyPoints.forEach { point ->
                                Row(
                                    modifier = Modifier.padding(vertical = 4.dp),
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.VerifiedUser,
                                        contentDescription = null,
                                        tint = GoldAccent,
                                        modifier = Modifier
                                            .size(15.dp)
                                            .padding(top = 2.dp)
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = point,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- Firm Footer ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = PrimaryNavy),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(
                modifier = Modifier.padding(18.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "P. R. BHUTA & CO.",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.ExtraBold,
                        letterSpacing = 1.2.sp
                    ),
                    color = Color.White
                )
                Text(
                    text = "Chartered Accountants • Mumbai, India",
                    style = MaterialTheme.typography.bodySmall,
                    color = GoldAccent
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Statutory Residential Status Determination System. This tool provides statutory interpretations based on the Income Tax Act, 2025 / 1961, and Foreign Exchange Management Act, 1999 as amended up to date.",
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                    color = Color(0xFFD2DCE6),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun ScopeTableRow(
    type: String,
    ror: String,
    rnor: String,
    nr: String
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = RoundedCornerShape(6.dp)
    ) {
        Column(modifier = Modifier.padding(8.dp)) {
            Text(
                text = type,
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold),
                color = PrimaryNavy
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text("ROR: $ror", style = MaterialTheme.typography.labelSmall, color = if (ror == "Taxable") Color(0xFFB71C1C) else Color(0xFF2E7D32))
                Text("RNOR: $rnor", style = MaterialTheme.typography.labelSmall, color = if (rnor == "Taxable") Color(0xFFB71C1C) else Color(0xFF2E7D32))
                Text("NR: $nr", style = MaterialTheme.typography.labelSmall, color = if (nr == "Taxable") Color(0xFFB71C1C) else Color(0xFF2E7D32))
            }
        }
    }
}
