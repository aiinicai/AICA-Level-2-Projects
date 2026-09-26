package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.FemaStatus
import com.example.model.IncomeTaxStatus
import com.example.ui.theme.StatusNrBlue
import com.example.ui.theme.StatusNrBlueBg
import com.example.ui.theme.StatusPriTeal
import com.example.ui.theme.StatusPriTealBg
import com.example.ui.theme.StatusProiPurple
import com.example.ui.theme.StatusProiPurpleBg
import com.example.ui.theme.StatusRnorAmber
import com.example.ui.theme.StatusRnorAmberBg
import com.example.ui.theme.StatusRorGreen
import com.example.ui.theme.StatusRorGreenBg

@Composable
fun IncomeTaxStatusBadge(
    status: IncomeTaxStatus,
    modifier: Modifier = Modifier,
    isLarge: Boolean = false
) {
    val (bgColor, fgColor, borderColor) = when (status) {
        IncomeTaxStatus.ROR -> Triple(StatusRorGreenBg, StatusRorGreen, StatusRorGreen.copy(alpha = 0.4f))
        IncomeTaxStatus.RNOR -> Triple(StatusRnorAmberBg, StatusRnorAmber, StatusRnorAmber.copy(alpha = 0.4f))
        IncomeTaxStatus.NR -> Triple(StatusNrBlueBg, StatusNrBlue, StatusNrBlue.copy(alpha = 0.4f))
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(bgColor)
            .border(1.dp, borderColor, RoundedCornerShape(8.dp))
            .padding(
                horizontal = if (isLarge) 14.dp else 10.dp,
                vertical = if (isLarge) 8.dp else 4.dp
            )
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(if (isLarge) 10.dp else 7.dp)
                    .clip(CircleShape)
                    .background(fgColor)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "${status.code} • ${status.title}",
                color = fgColor,
                style = if (isLarge) {
                    MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                } else {
                    MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }
            )
        }
    }
}

@Composable
fun FemaStatusBadge(
    status: FemaStatus,
    modifier: Modifier = Modifier,
    isLarge: Boolean = false
) {
    val (bgColor, fgColor, borderColor) = when (status) {
        FemaStatus.PRI -> Triple(StatusPriTealBg, StatusPriTeal, StatusPriTeal.copy(alpha = 0.4f))
        FemaStatus.PROI -> Triple(StatusProiPurpleBg, StatusProiPurple, StatusProiPurple.copy(alpha = 0.4f))
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(bgColor)
            .border(1.dp, borderColor, RoundedCornerShape(8.dp))
            .padding(
                horizontal = if (isLarge) 14.dp else 10.dp,
                vertical = if (isLarge) 8.dp else 4.dp
            )
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(if (isLarge) 10.dp else 7.dp)
                    .clip(CircleShape)
                    .background(fgColor)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "${status.code} • ${status.title}",
                color = fgColor,
                style = if (isLarge) {
                    MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                } else {
                    MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }
            )
        }
    }
}
