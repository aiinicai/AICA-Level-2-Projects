package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.UserProfileEntity
import com.example.data.model.RiskProfile
import com.example.ui.theme.BlueAccent
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary

@Composable
fun ProfileDialog(
    initialProfile: UserProfileEntity,
    onDismiss: () -> Unit,
    onSaveProfile: (UserProfileEntity) -> Unit,
    onFetchAllDetails: ((UserProfileEntity) -> Unit)? = null
) {
    var name by remember { mutableStateOf(initialProfile.name) }
    var profession by remember { mutableStateOf(initialProfile.profession) }
    var monthlyIncomeStr by remember { mutableStateOf(initialProfile.monthlyIncome.toLong().toString()) }
    var currentAgeStr by remember { mutableStateOf(initialProfile.currentAge.toString()) }
    var retirementAgeStr by remember { mutableStateOf(initialProfile.retirementAge.toString()) }
    var city by remember { mutableStateOf(initialProfile.city) }
    var taxRegime by remember { mutableStateOf(initialProfile.taxRegime) }
    var riskProfile by remember { mutableStateOf(initialProfile.riskProfile) }
    var dependentsCountStr by remember { mutableStateOf(initialProfile.dependentsCount.toString()) }

    fun buildUpdatedProfile(): UserProfileEntity {
        val income = monthlyIncomeStr.toDoubleOrNull() ?: initialProfile.monthlyIncome
        val cAge = currentAgeStr.toIntOrNull() ?: initialProfile.currentAge
        val rAge = retirementAgeStr.toIntOrNull() ?: initialProfile.retirementAge
        val deps = dependentsCountStr.toIntOrNull() ?: initialProfile.dependentsCount
        return initialProfile.copy(
            name = name.ifBlank { "Subhamjit Patra" },
            profession = profession.ifBlank { "Principal Software Architect" },
            monthlyIncome = income,
            currentAge = cAge,
            retirementAge = rAge,
            city = city.ifBlank { "Bengaluru" },
            taxRegime = taxRegime,
            riskProfile = riskProfile,
            dependentsCount = deps,
            currencySymbol = "₹"
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
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
                            .clip(CircleShape)
                            .background(Brush.linearGradient(listOf(LavenderAccent, BlueAccent))),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.Person, contentDescription = null, tint = DarkBackground, modifier = Modifier.size(20.dp))
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text("Personal Profile", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text("Indian Financial Identity", color = TextSecondary, fontSize = 11.sp)
                    }
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "Update your identity, income in INR (₹), and retirement horizon:",
                    color = TextSecondary,
                    fontSize = 12.sp
                )

                // 1. Name Field
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Full Name", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null, tint = LavenderAccent, modifier = Modifier.size(18.dp)) },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )

                // 2. Profession
                OutlinedTextField(
                    value = profession,
                    onValueChange = { profession = it },
                    label = { Text("Profession / Designation", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )

                // 3. Monthly In-Hand Income (₹)
                OutlinedTextField(
                    value = monthlyIncomeStr,
                    onValueChange = { monthlyIncomeStr = it },
                    label = { Text("Monthly In-Hand Income (₹)", color = TextSecondary) },
                    placeholder = { Text("e.g. 225000", color = TextMuted) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )

                // 4. Age and Retirement Age
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = currentAgeStr,
                        onValueChange = { currentAgeStr = it },
                        label = { Text("Current Age", color = TextSecondary, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedBorderColor = LavenderAccent,
                            unfocusedBorderColor = DarkBorder
                        )
                    )
                    OutlinedTextField(
                        value = retirementAgeStr,
                        onValueChange = { retirementAgeStr = it },
                        label = { Text("Retirement Age", color = TextSecondary, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedBorderColor = LavenderAccent,
                            unfocusedBorderColor = DarkBorder
                        )
                    )
                }

                // 5. City and Dependents
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = city,
                        onValueChange = { city = it },
                        label = { Text("City (e.g. Bengaluru)", color = TextSecondary, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedBorderColor = LavenderAccent,
                            unfocusedBorderColor = DarkBorder
                        )
                    )
                    OutlinedTextField(
                        value = dependentsCountStr,
                        onValueChange = { dependentsCountStr = it },
                        label = { Text("Dependents", color = TextSecondary, fontSize = 11.sp) },
                        modifier = Modifier.weight(1f),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            focusedBorderColor = LavenderAccent,
                            unfocusedBorderColor = DarkBorder
                        )
                    )
                }

                // 6. Tax Regime Selector (New vs Old)
                Column {
                    Text("Income Tax Regime", color = TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.Medium)
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        val isNew = taxRegime.contains("New")
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (isNew) LavenderAccent.copy(alpha = 0.2f) else DarkSurfaceVariant)
                                .border(1.dp, if (isNew) LavenderAccent else DarkBorder, RoundedCornerShape(12.dp))
                                .clickable { taxRegime = "New Regime (Section 115BAC)" }
                                .padding(8.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                "New Regime (115BAC)",
                                fontSize = 11.sp,
                                color = if (isNew) LavenderAccent else TextSecondary,
                                fontWeight = if (isNew) FontWeight.Bold else FontWeight.Normal
                            )
                        }

                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (!isNew) LavenderAccent.copy(alpha = 0.2f) else DarkSurfaceVariant)
                                .border(1.dp, if (!isNew) LavenderAccent else DarkBorder, RoundedCornerShape(12.dp))
                                .clickable { taxRegime = "Old Regime (80C/80D)" }
                                .padding(8.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                "Old Regime (80C/80D)",
                                fontSize = 11.sp,
                                color = if (!isNew) LavenderAccent else TextSecondary,
                                fontWeight = if (!isNew) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Primary Action: Save Profile Changes
                Button(
                    onClick = {
                        val updated = buildUpdatedProfile()
                        onSaveProfile(updated)
                        onFetchAllDetails?.invoke(updated)
                        onDismiss()
                    },
                    modifier = Modifier.fillMaxWidth().height(46.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Save Profile & Recalculate", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }

                if (onFetchAllDetails != null) {
                    OutlinedButton(
                        onClick = {
                            val updated = buildUpdatedProfile()
                            onSaveProfile(updated)
                            onFetchAllDetails(updated)
                            onDismiss()
                        },
                        modifier = Modifier.fillMaxWidth().height(42.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorderLight)
                    ) {
                        Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(14.dp), tint = LavenderAccent)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Save & Fetch Accounts (AA)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp)
                    }
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = TextSecondary)
            }
        }
    )
}
