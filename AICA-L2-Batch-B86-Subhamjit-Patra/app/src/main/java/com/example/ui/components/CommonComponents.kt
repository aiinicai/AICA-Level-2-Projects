package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.AssetCategory
import com.example.data.model.GoalCategory
import com.example.ui.theme.BlueAccent
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary

@Composable
fun SophisticatedCard(
    modifier: Modifier = Modifier,
    cornerRadius: Int = 24,
    backgroundColor: Color = DarkSurface,
    borderColor: Color = DarkBorder,
    content: @Composable () -> Unit
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(cornerRadius.dp))
            .background(backgroundColor)
            .border(1.dp, borderColor, RoundedCornerShape(cornerRadius.dp))
    ) {
        content()
    }
}

@Composable
fun GradientProgressBar(
    progress: Float,
    modifier: Modifier = Modifier,
    height: Int = 6,
    brush: Brush = Brush.horizontalGradient(listOf(LavenderAccent, BlueAccent)),
    trackColor: Color = DarkBackground
) {
    val clampedProgress = progress.coerceIn(0f, 1f)
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height.dp)
            .clip(CircleShape)
            .background(trackColor)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(clampedProgress)
                .height(height.dp)
                .clip(CircleShape)
                .background(brush)
        )
    }
}

@Composable
fun PillBadge(
    text: String,
    textColor: Color = MintSuccess,
    backgroundColor: Color = DarkSurfaceVariant,
    borderColor: Color = DarkBorderLight
) {
    Box(
        modifier = Modifier
            .clip(CircleShape)
            .background(backgroundColor)
            .border(1.dp, borderColor, CircleShape)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp,
            color = textColor
        )
    }
}

@Composable
fun AddAssetDialog(
    onDismiss: () -> Unit,
    onAdd: (name: String, category: AssetCategory, amount: Double, institution: String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var amountStr by remember { mutableStateOf("") }
    var institution by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text("Add Asset", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Asset Name (e.g. S&P 500 Index)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = amountStr,
                    onValueChange = { amountStr = it },
                    label = { Text("Amount / Value ($)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = institution,
                    onValueChange = { institution = it },
                    label = { Text("Institution (e.g. Vanguard, Chase)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amountStr.toDoubleOrNull() ?: 0.0
                    if (name.isNotBlank() && amt > 0) {
                        onAdd(name, AssetCategory.MUTUAL_FUNDS, amt, institution)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
            ) {
                Text("Add Asset", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = TextSecondary)
            }
        }
    )
}

@Composable
fun AddGoalDialog(
    onDismiss: () -> Unit,
    onAdd: (title: String, category: GoalCategory, targetAmount: Double, currentAmount: Double, targetYears: Int) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var targetStr by remember { mutableStateOf("") }
    var currentStr by remember { mutableStateOf("") }
    var yearsStr by remember { mutableStateOf("5") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text("Create Financial Goal", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        },
        text = {
            Column {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Goal Title (e.g. Dream House Downpayment)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = targetStr,
                    onValueChange = { targetStr = it },
                    label = { Text("Target Amount ($)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = currentStr,
                    onValueChange = { currentStr = it },
                    label = { Text("Current Accumulated ($)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = yearsStr,
                    onValueChange = { yearsStr = it },
                    label = { Text("Time Horizon (Years)", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        focusedBorderColor = LavenderAccent,
                        unfocusedBorderColor = DarkBorder
                    )
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val target = targetStr.toDoubleOrNull() ?: 0.0
                    val current = currentStr.toDoubleOrNull() ?: 0.0
                    val years = yearsStr.toIntOrNull() ?: 5
                    if (title.isNotBlank() && target > 0) {
                        onAdd(title, GoalCategory.WEALTH, target, current, years)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
            ) {
                Text("Save Goal", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = TextSecondary)
            }
        }
    )
}
