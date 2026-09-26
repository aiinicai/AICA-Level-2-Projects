package com.example.ui.components

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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted

@Composable
fun NumericDaysInput(
    label: String,
    value: Int,
    onValueChange: (Int) -> Unit,
    maxLimit: Int = 366,
    minLimit: Int = 0,
    helperText: String? = null,
    testTagPrefix: String = "days_input",
    modifier: Modifier = Modifier
) {
    var isError by remember { mutableStateOf(false) }

    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(modifier = Modifier.height(6.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Decrement Button (-10)
            Surface(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .testTag("${testTagPrefix}_dec_fast"),
                color = MaterialTheme.colorScheme.surfaceVariant,
                onClick = {
                    val newVal = (value - 10).coerceAtLeast(minLimit)
                    onValueChange(newVal)
                }
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = "-10",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            // Decrement Button (-1)
            IconButton(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .border(1.dp, SlateBorder, RoundedCornerShape(8.dp))
                    .testTag("${testTagPrefix}_dec"),
                onClick = {
                    val newVal = (value - 1).coerceAtLeast(minLimit)
                    onValueChange(newVal)
                }
            ) {
                Icon(
                    imageVector = Icons.Default.Remove,
                    contentDescription = "Decrease 1 day",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Numeric Input Field
            OutlinedTextField(
                value = if (value == 0) "" else value.toString(),
                onValueChange = { input ->
                    if (input.isBlank()) {
                        isError = false
                        onValueChange(0)
                    } else {
                        val parsed = input.toIntOrNull()
                        if (parsed != null && parsed in minLimit..maxLimit) {
                            isError = false
                            onValueChange(parsed)
                        } else if (parsed != null && parsed > maxLimit) {
                            isError = true
                        }
                    }
                },
                modifier = Modifier
                    .weight(1f)
                    .testTag("${testTagPrefix}_field"),
                singleLine = true,
                isError = isError,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                placeholder = { Text("0 days") },
                suffix = { Text("days", style = MaterialTheme.typography.bodySmall, color = SlateMuted) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = PrimaryNavy,
                    unfocusedBorderColor = SlateBorder
                )
            )

            // Increment Button (+1)
            IconButton(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .border(1.dp, SlateBorder, RoundedCornerShape(8.dp))
                    .testTag("${testTagPrefix}_inc"),
                onClick = {
                    val newVal = (value + 1).coerceAtMost(maxLimit)
                    onValueChange(newVal)
                }
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = "Increase 1 day",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Increment Button (+10)
            Surface(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .testTag("${testTagPrefix}_inc_fast"),
                color = MaterialTheme.colorScheme.surfaceVariant,
                onClick = {
                    val newVal = (value + 10).coerceAtMost(maxLimit)
                    onValueChange(newVal)
                }
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = "+10",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        if (helperText != null) {
            Spacer(modifier = Modifier.height(4.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = SlateMuted,
                    modifier = Modifier.size(13.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = helperText,
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                    color = SlateMuted
                )
            }
        }
    }
}
