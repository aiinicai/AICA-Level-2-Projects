package com.example.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.*
import kotlin.math.cos
import kotlin.math.sin

data class BarGroupData(
    val label: String,
    val assigned: Int,
    val completed: Int
)

data class DonutSliceData(
    val label: String,
    val value: Float,
    val color: Color
)

@Composable
fun InteractiveBarChart(
    data: List<BarGroupData>,
    modifier: Modifier = Modifier,
    onBarClick: (BarGroupData) -> Unit = {}
) {
    if (data.isEmpty()) {
        Box(
            modifier = modifier
                .fillMaxWidth()
                .height(180.dp),
            contentAlignment = Alignment.Center
        ) {
            Text("No employee task data available", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    val maxVal = data.maxOfOrNull { maxOf(it.assigned, it.completed) }?.coerceAtLeast(1) ?: 1

    Column(modifier = modifier.fillMaxWidth()) {
        // Legend
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(SlateBlue)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text("Assigned", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.width(12.dp))
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(StatusCompleted)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text("Completed", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        // Bars
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            data.forEach { item ->
                val assignedRatio by animateFloatAsState(
                    targetValue = (item.assigned.toFloat() / maxVal).coerceIn(0f, 1f),
                    animationSpec = tween(600),
                    label = "assignedRatio"
                )
                val completedRatio by animateFloatAsState(
                    targetValue = (item.completed.toFloat() / maxVal).coerceIn(0f, 1f),
                    animationSpec = tween(600),
                    label = "completedRatio"
                )

                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { onBarClick(item) }
                        .padding(vertical = 4.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = item.label,
                            fontWeight = FontWeight.Medium,
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "${item.completed}/${item.assigned} done",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    // Assigned Bar
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(assignedRatio)
                                .fillMaxHeight()
                                .clip(RoundedCornerShape(4.dp))
                                .background(SlateBlue)
                        )
                    }
                    Spacer(modifier = Modifier.height(2.dp))
                    // Completed Bar
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(completedRatio)
                                .fillMaxHeight()
                                .clip(RoundedCornerShape(4.dp))
                                .background(StatusCompleted)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun DonutPieChart(
    slices: List<DonutSliceData>,
    modifier: Modifier = Modifier,
    centerTitle: String = "Total",
    centerSubtitle: String = ""
) {
    val total = slices.sumOf { it.value.toDouble() }.toFloat().coerceAtLeast(1f)

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Canvas Donut
        Box(
            modifier = Modifier
                .size(140.dp)
                .padding(8.dp),
            contentAlignment = Alignment.Center
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val strokeWidth = 24.dp.toPx()
                val radius = (size.minDimension - strokeWidth) / 2
                val topLeft = Offset((size.width - radius * 2) / 2, (size.height - radius * 2) / 2)
                val arcSize = Size(radius * 2, radius * 2)

                var startAngle = -90f
                slices.forEach { slice ->
                    val sweepAngle = (slice.value / total) * 360f
                    if (sweepAngle > 0f) {
                        drawArc(
                            color = slice.color,
                            startAngle = startAngle,
                            sweepAngle = sweepAngle - 1f, // tiny gap
                            useCenter = false,
                            topLeft = topLeft,
                            size = arcSize,
                            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                        )
                        startAngle += sweepAngle
                    }
                }
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = centerTitle,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (centerSubtitle.isNotEmpty()) {
                    Text(
                        text = centerSubtitle,
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }

        Spacer(modifier = Modifier.width(16.dp))

        // Legend list
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            slices.forEach { slice ->
                val percentage = if (total > 0) ((slice.value / total) * 100).toInt() else 0
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.weight(1f)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(slice.color)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = slice.label,
                            fontSize = 12.sp,
                            maxLines = 1,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                    Text(
                        text = "${slice.value.toInt()} ($percentage%)",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
fun TrendLineChart(
    points: List<Pair<String, Int>>,
    modifier: Modifier = Modifier
) {
    if (points.isEmpty()) return

    val maxVal = points.maxOfOrNull { it.second }?.coerceAtLeast(1) ?: 1

    Column(modifier = modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(130.dp)
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val w = size.width
                val h = size.height
                val padY = 20.dp.toPx()
                val usableH = h - padY * 2
                val stepX = if (points.size > 1) w / (points.size - 1) else w

                val path = Path()
                val fillPath = Path()

                points.forEachIndexed { i, pt ->
                    val x = i * stepX
                    val normY = pt.second.toFloat() / maxVal
                    val y = h - padY - (normY * usableH)

                    if (i == 0) {
                        path.moveTo(x, y)
                        fillPath.moveTo(x, h)
                        fillPath.lineTo(x, y)
                    } else {
                        val prevX = (i - 1) * stepX
                        val prevY = h - padY - ((points[i - 1].second.toFloat() / maxVal) * usableH)
                        val cx = (prevX + x) / 2f
                        path.cubicTo(cx, prevY, cx, y, x, y)
                        fillPath.cubicTo(cx, prevY, cx, y, x, y)
                    }
                }

                fillPath.lineTo(w, h)
                fillPath.close()

                // Gradient fill
                drawPath(
                    path = fillPath,
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            GoldAccent.copy(alpha = 0.35f),
                            GoldAccent.copy(alpha = 0.02f)
                        )
                    )
                )

                // Smooth stroke
                drawPath(
                    path = path,
                    color = GoldAccent,
                    style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round)
                )

                // Dot markers
                points.forEachIndexed { i, pt ->
                    val x = i * stepX
                    val normY = pt.second.toFloat() / maxVal
                    val y = h - padY - (normY * usableH)
                    drawCircle(color = NavyPrimary, radius = 5.dp.toPx(), center = Offset(x, y))
                    drawCircle(color = GoldAccent, radius = 3.dp.toPx(), center = Offset(x, y))
                }
            }
        }

        // Labels
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            points.forEach { (label, value) ->
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = label,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "$value",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
    }
}

@Composable
fun MetricSummaryCard(
    title: String,
    count: String,
    icon: ImageVector? = null,
    accentColor: Color = NavyPrimary,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    progress: Float? = null,
    progressColor: Color = NavyPrimary,
    isAlert: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    val containerBg = if (isAlert) RedAlertBg else MaterialTheme.colorScheme.surface
    val borderStrokeColor = if (isAlert) RedAlertBorder else BorderSlate100
    val titleColor = if (isAlert) RedAlertText else TextSecondaryLight
    val valueColor = if (isAlert) RedAlertValue else NavyPrimary

    Card(
        modifier = modifier
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = containerBg),
        border = androidx.compose.foundation.BorderStroke(1.dp, borderStrokeColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(horizontal = 14.dp, vertical = 12.dp)
                .fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title.uppercase(),
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.5.sp,
                    color = titleColor,
                    maxLines = 1
                )
                if (icon != null) {
                    Box(
                        modifier = Modifier
                            .size(26.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(accentColor.copy(alpha = 0.12f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = icon,
                            contentDescription = title,
                            tint = accentColor,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = count,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = valueColor
            )

            if (progress != null) {
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(BorderSlate100)
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(progress.coerceIn(0f, 1f))
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(2.dp))
                            .background(progressColor)
                    )
                }
            } else if (subtitle != null) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = subtitle,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Medium,
                    color = if (isAlert) RedAlertText else AmberWarning,
                    maxLines = 1
                )
            }
        }
    }
}

@Composable
fun HighDensityDistributionCard(
    gstCount: Int,
    itrCount: Int,
    pmsCount: Int,
    auditCount: Int,
    completionPercentage: Int = 82,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate100),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Column {
                    Text(
                        "Filing Distribution",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp,
                        color = TextPrimaryLight
                    )
                    Text(
                        "Current Month Completion",
                        fontSize = 11.sp,
                        color = TextSecondaryLight
                    )
                }
                Text(
                    "$completionPercentage% Total",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = StatusCompleted
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            val maxVal = maxOf(gstCount, itrCount, pmsCount, auditCount, 1)

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(84.dp)
                    .padding(horizontal = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                // GST Bar (Navy)
                BarItem(
                    label = "GST",
                    ratio = (gstCount.toFloat() / maxVal).coerceIn(0.2f, 1f),
                    color = NavyPrimary,
                    modifier = Modifier.weight(1f)
                )
                // ITR Bar (Gold)
                BarItem(
                    label = "ITR",
                    ratio = (itrCount.toFloat() / maxVal).coerceIn(0.2f, 1f),
                    color = GoldAccent,
                    modifier = Modifier.weight(1f)
                )
                // PMS Bar (Slate)
                BarItem(
                    label = "PMS",
                    ratio = (pmsCount.toFloat() / maxVal).coerceIn(0.2f, 1f),
                    color = SoftSlate,
                    modifier = Modifier.weight(1f)
                )
                // AUDIT Bar (Navy/Slate Blue)
                BarItem(
                    label = "AUDIT",
                    ratio = (auditCount.toFloat() / maxVal).coerceIn(0.2f, 1f),
                    color = SlateBlue,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

@Composable
private fun BarItem(
    label: String,
    ratio: Float,
    color: Color,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxHeight(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Bottom
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(ratio)
                .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                .background(color)
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = label,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            color = TextMutedLight
        )
    }
}

@Composable
fun OverdueAlertCard(
    count: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    if (count <= 0) return

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = RedAlertBg
        ),
        border = androidx.compose.foundation.BorderStroke(1.dp, RedAlertBorder),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 14.dp, vertical = 10.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(32.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(RedAlertText)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "$count OVERDUE FILING${if (count > 1) "S" else ""}",
                    fontWeight = FontWeight.Bold,
                    fontSize = 11.sp,
                    letterSpacing = 0.5.sp,
                    color = RedAlertText
                )
                Text(
                    text = "Action required • Statutory deadline passed",
                    fontSize = 11.sp,
                    color = RedAlertValue,
                    fontWeight = FontWeight.Medium
                )
            }
            FilledTonalButton(
                onClick = onClick,
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = RedAlertText,
                    contentColor = Color.White
                ),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("View", fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
