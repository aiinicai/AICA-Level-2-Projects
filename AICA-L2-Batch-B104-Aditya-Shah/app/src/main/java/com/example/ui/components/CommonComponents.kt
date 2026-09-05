package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Gavel
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.TextVerificationStatus
import com.example.ui.theme.EmeraldContainer
import com.example.ui.theme.EmeraldGreen
import com.example.ui.theme.PurpleAi
import com.example.ui.theme.PurpleAiContainer
import com.example.ui.theme.SaffronAmber
import com.example.ui.theme.SaffronContainer

@Composable
fun TextVerificationBadge(
    status: TextVerificationStatus,
    modifier: Modifier = Modifier
) {
    val (bg, textColor, icon) = when (status) {
        TextVerificationStatus.TEXT_VERIFIED -> Triple(EmeraldContainer, EmeraldGreen, Icons.Default.CheckCircle)
        TextVerificationStatus.TEXT_PENDING_REVIEW -> Triple(Color(0xFFFEF3C7), Color(0xFFD97706), Icons.Default.Info)
        TextVerificationStatus.TEXT_NOT_LOADED -> Triple(Color(0xFFF1F5F9), Color(0xFF64748B), Icons.Default.Info)
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = status.label,
            tint = textColor,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = status.label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Bold,
                fontSize = 10.sp,
                color = textColor,
                letterSpacing = 0.5.sp
            )
        )
    }
}

@Composable
fun StatutoryDisclaimerCard(
    modifier: Modifier = Modifier,
    compact: Boolean = false
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .testTag("disclaimer_card"),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier.padding(if (compact) 10.dp else 14.dp),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Info,
                contentDescription = "Legal Disclaimer",
                tint = SaffronAmber,
                modifier = Modifier.size(if (compact) 18.dp else 22.dp)
            )
            Column {
                Text(
                    text = "Statutory & Educational Disclaimer",
                    style = MaterialTheme.typography.labelMedium.copy(
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "TaxBridge AI is an educational and research tool. AI-generated explanations should not be treated as legal or tax advice. Users should verify provisions against the prevailing law and official sources.",
                    style = MaterialTheme.typography.bodySmall.copy(
                        fontSize = if (compact) 11.sp else 12.sp,
                        lineHeight = if (compact) 15.sp else 17.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )
            }
        }
    }
}

@Composable
fun StatusBadge(
    status: MappingStatus,
    modifier: Modifier = Modifier
) {
    val (bg, textColor, icon) = when (status) {
        MappingStatus.VERIFIED -> Triple(EmeraldContainer, EmeraldGreen, Icons.Default.CheckCircle)
        MappingStatus.PENDING_REVIEW -> Triple(Color(0xFFFEF3C7), Color(0xFFD97706), Icons.Default.Info)
        MappingStatus.UNVERIFIED -> Triple(SaffronContainer, Color(0xFF92400E), Icons.Default.Warning)
        MappingStatus.NOT_LOADED -> Triple(Color(0xFFE2E8F0), Color(0xFF475569), Icons.Default.Info)
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = status.label,
            tint = textColor,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = status.label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Bold,
                fontSize = 10.sp,
                color = textColor,
                letterSpacing = 0.5.sp
            )
        )
    }
}

@Composable
fun MappingTypeBadge(
    type: MappingType,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(6.dp),
        color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f)
    ) {
        Text(
            text = type.label,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.SemiBold,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        )
    }
}

@Composable
fun CategoryBadge(
    category: String,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(6.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Text(
            text = category,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
            style = MaterialTheme.typography.labelSmall.copy(
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        )
    }
}

@Composable
fun StatutorySourcePill(
    sourceText: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = Icons.Default.Gavel,
            contentDescription = "Official Source",
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = sourceText,
            style = MaterialTheme.typography.labelSmall.copy(
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            ),
            maxLines = 1
        )
    }
}

@Composable
fun AiGeneratedBadge(
    modifier: Modifier = Modifier,
    label: String = "AI-Generated Analysis"
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(PurpleAiContainer)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = Icons.Default.AutoAwesome,
            contentDescription = "AI Generated",
            tint = PurpleAi,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Bold,
                fontSize = 10.sp,
                color = PurpleAi
            )
        )
    }
}

@Composable
fun VerifiedSourceDataBadge(
    modifier: Modifier = Modifier,
    label: String = "VERIFIED SOURCE DATA"
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(EmeraldContainer)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = Icons.Default.CheckCircle,
            contentDescription = "Verified Source Data",
            tint = EmeraldGreen,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Bold,
                fontSize = 10.sp,
                color = EmeraldGreen,
                letterSpacing = 0.5.sp
            )
        )
    }
}

@Composable
fun SourceBasedExplanationBadge(
    modifier: Modifier = Modifier,
    label: String = "Source-based explanation"
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.8f))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = Icons.Default.Info,
            contentDescription = "Source-based explanation",
            tint = MaterialTheme.colorScheme.onSecondaryContainer,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.SemiBold,
                fontSize = 10.sp,
                color = MaterialTheme.colorScheme.onSecondaryContainer
            )
        )
    }
}
