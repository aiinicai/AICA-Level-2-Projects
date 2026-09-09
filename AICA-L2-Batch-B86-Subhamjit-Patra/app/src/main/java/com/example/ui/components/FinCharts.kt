package com.example.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.*
import kotlin.math.cos
import kotlin.math.sin

/**
 * Reusable Net Worth Trend Chart (Bézier curve with gradient area under curve)
 */
@Composable
fun NetWorthTrendChart(
    dataPoints: List<Pair<String, Double>>,
    modifier: Modifier = Modifier,
    lineColor: Color = LavenderAccent,
    gradientColors: List<Color> = listOf(LavenderAccent.copy(alpha = 0.35f), Color.Transparent)
) {
    if (dataPoints.isEmpty()) return

    val minVal = (dataPoints.minOfOrNull { it.second } ?: 0.0) * 0.95
    val maxVal = (dataPoints.maxOfOrNull { it.second } ?: 1.0) * 1.02
    val range = if (maxVal > minVal) maxVal - minVal else 1.0

    var selectedIndex by remember { mutableStateOf<Int?>(null) }

    Column(modifier = modifier) {
        // Active point tooltip
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            val displayIdx = selectedIndex ?: (dataPoints.size - 1)
            val selected = dataPoints.getOrNull(displayIdx) ?: dataPoints.last()
            Text(
                text = "${selected.first}: $${String.format("%,.0f", selected.second)}",
                color = LavenderAccent,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Tap points to inspect",
                color = TextSecondary,
                fontSize = 11.sp
            )
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(130.dp)
        ) {
            val w = size.width
            val h = size.height
            val stepX = if (dataPoints.size > 1) w / (dataPoints.size - 1) else w

            val path = Path()
            val fillPath = Path()

            val points = dataPoints.mapIndexed { index, pair ->
                val x = index * stepX
                val normalizedY = ((pair.second - minVal) / range).toFloat()
                val y = h - (normalizedY * (h - 20f)) - 10f
                Offset(x, y)
            }

            if (points.isNotEmpty()) {
                path.moveTo(points.first().x, points.first().y)
                fillPath.moveTo(points.first().x, h)
                fillPath.lineTo(points.first().x, points.first().y)

                for (i in 0 until points.size - 1) {
                    val p1 = points[i]
                    val p2 = points[i + 1]
                    val controlX1 = (p1.x + p2.x) / 2f
                    val controlY1 = p1.y
                    val controlX2 = (p1.x + p2.x) / 2f
                    val controlY2 = p2.y

                    path.cubicTo(controlX1, controlY1, controlX2, controlY2, p2.x, p2.y)
                    fillPath.cubicTo(controlX1, controlY1, controlX2, controlY2, p2.x, p2.y)
                }

                fillPath.lineTo(points.last().x, h)
                fillPath.close()

                // Draw gradient under curve
                drawPath(
                    path = fillPath,
                    brush = Brush.verticalGradient(
                        colors = gradientColors,
                        startY = 0f,
                        endY = h
                    )
                )

                // Draw curve stroke
                drawPath(
                    path = path,
                    color = lineColor,
                    style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round)
                )

                // Draw points
                points.forEachIndexed { i, pt ->
                    val isSelected = selectedIndex == i || (selectedIndex == null && i == points.size - 1)
                    drawCircle(
                        color = if (isSelected) MintSuccess else lineColor,
                        radius = if (isSelected) 5.dp.toPx() else 3.5.dp.toPx(),
                        center = pt
                    )
                    drawCircle(
                        color = DarkBackground,
                        radius = if (isSelected) 2.5.dp.toPx() else 1.5.dp.toPx(),
                        center = pt
                    )
                }
            }
        }

        // X-Axis labels
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            dataPoints.forEachIndexed { i, pair ->
                Text(
                    text = pair.first,
                    color = if (selectedIndex == i) LavenderAccent else TextSecondary,
                    fontSize = 10.sp,
                    fontWeight = if (selectedIndex == i) FontWeight.Bold else FontWeight.Normal,
                    modifier = Modifier.clickable { selectedIndex = i }
                )
            }
        }
    }
}

/**
 * Reusable Monthly Cash Flow Bar Chart (Income vs Expense side-by-side)
 */
@Composable
fun CashFlowBarChart(
    months: List<String>,
    incomes: List<Double>,
    expenses: List<Double>,
    modifier: Modifier = Modifier
) {
    val maxAmount = maxOf(
        incomes.maxOrNull() ?: 1.0,
        expenses.maxOrNull() ?: 1.0
    ) * 1.15

    Column(modifier = modifier) {
        // Legend
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(modifier = Modifier.size(8.dp).background(MintSuccess, RoundedCornerShape(2.dp)))
            Spacer(modifier = Modifier.width(4.dp))
            Text("Income", color = TextSecondary, fontSize = 11.sp)
            Spacer(modifier = Modifier.width(12.dp))
            Box(modifier = Modifier.size(8.dp).background(CoralExpense, RoundedCornerShape(2.dp)))
            Spacer(modifier = Modifier.width(4.dp))
            Text("Expense", color = TextSecondary, fontSize = 11.sp)
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(130.dp)
        ) {
            val w = size.width
            val h = size.height
            val count = months.size
            val groupWidth = w / count
            val barWidth = (groupWidth * 0.32f).coerceAtMost(16.dp.toPx())
            val spacing = 4.dp.toPx()

            months.forEachIndexed { i, _ ->
                val groupCenter = i * groupWidth + (groupWidth / 2f)

                val incomeVal = incomes.getOrElse(i) { 0.0 }
                val expenseVal = expenses.getOrElse(i) { 0.0 }

                val incomeHeight = ((incomeVal / maxAmount).toFloat() * (h - 10f)).coerceAtLeast(4f)
                val expenseHeight = ((expenseVal / maxAmount).toFloat() * (h - 10f)).coerceAtLeast(4f)

                // Income bar (Mint)
                drawRoundRect(
                    color = MintSuccess,
                    topLeft = Offset(groupCenter - barWidth - (spacing / 2f), h - incomeHeight),
                    size = Size(barWidth, incomeHeight),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )

                // Expense bar (Coral)
                drawRoundRect(
                    color = CoralExpense,
                    topLeft = Offset(groupCenter + (spacing / 2f), h - expenseHeight),
                    size = Size(barWidth, expenseHeight),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )
            }
        }

        // Labels
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            horizontalArrangement = Arrangement.SpaceAround
        ) {
            months.forEach { month ->
                Text(text = month, color = TextSecondary, fontSize = 10.sp)
            }
        }
    }
}

/**
 * Reusable Donut Chart for Expense Breakdown & Portfolio Allocation
 */
data class DonutSegment(
    val label: String,
    val value: Double,
    val color: Color
)

@Composable
fun ExpenseBreakdownDonutChart(
    segments: List<DonutSegment>,
    centerTitle: String,
    centerValue: String,
    modifier: Modifier = Modifier
) {
    val total = segments.sumOf { it.value }

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Donut Canvas
        Box(
            modifier = Modifier.size(130.dp),
            contentAlignment = Alignment.Center
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val strokeWidth = 18.dp.toPx()
                val radius = (size.minDimension - strokeWidth) / 2f
                val center = Offset(size.width / 2f, size.height / 2f)

                var startAngle = -90f
                segments.forEach { seg ->
                    val sweep = if (total > 0) ((seg.value / total) * 360f).toFloat() else 0f
                    drawArc(
                        color = seg.color,
                        startAngle = startAngle,
                        sweepAngle = (sweep - 2f).coerceAtLeast(1f),
                        useCenter = false,
                        topLeft = Offset(center.x - radius, center.y - radius),
                        size = Size(radius * 2, radius * 2),
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                    startAngle += sweep
                }
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(text = centerTitle, color = TextSecondary, fontSize = 9.sp)
                Text(text = centerValue, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
        }

        Spacer(modifier = Modifier.width(16.dp))

        // Legend list
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            segments.take(5).forEach { seg ->
                val pct = if (total > 0) (seg.value / total * 100).toInt() else 0
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(modifier = Modifier.size(7.dp).background(seg.color, CircleShape))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = seg.label,
                            color = TextPrimary,
                            fontSize = 11.sp,
                            maxLines = 1
                        )
                    }
                    Text(
                        text = "$pct%",
                        color = TextSecondary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
}

/**
 * Reusable Financial Health Score Gauge
 */
@Composable
fun HealthScoreGauge(
    score: Int,
    rating: String,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier.size(100.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val stroke = 10.dp.toPx()
            val radius = (size.minDimension - stroke) / 2f
            val center = Offset(size.width / 2f, size.height / 2f)

            // Background arc (240 degrees)
            drawArc(
                color = DarkBorder,
                startAngle = 150f,
                sweepAngle = 240f,
                useCenter = false,
                topLeft = Offset(center.x - radius, center.y - radius),
                size = Size(radius * 2, radius * 2),
                style = Stroke(width = stroke, cap = StrokeCap.Round)
            )

            // Active progress arc with gradient
            val sweep = (score / 100f) * 240f
            drawArc(
                brush = Brush.horizontalGradient(
                    colors = listOf(LavenderAccent, BlueAccent, MintSuccess)
                ),
                startAngle = 150f,
                sweepAngle = sweep,
                useCenter = false,
                topLeft = Offset(center.x - radius, center.y - radius),
                size = Size(radius * 2, radius * 2),
                style = Stroke(width = stroke, cap = StrokeCap.Round)
            )
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "$score",
                color = LavenderAccent,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = rating,
                color = MintSuccess,
                fontSize = 9.sp,
                fontWeight = FontWeight.ExtraBold
            )
        }
    }
}
