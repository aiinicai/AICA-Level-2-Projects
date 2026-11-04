package com.example.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Artistic Mandala Decoration
 * Draws a multi-layered sacred geometric mandala inspired by ISKCON traditional craftsmanship
 * with concentric rings, radial lotus petals, and radiant sun dots.
 */
@Composable
fun MandalaDecor(
    modifier: Modifier = Modifier,
    size: Dp = 80.dp,
    tint: Color = Color(0xFFD4AF37),
    alpha: Float = 0.28f,
    petalCount: Int = 12
) {
    Box(
        modifier = modifier.size(size),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(size)) {
            val center = Offset(this.size.width / 2f, this.size.height / 2f)
            val radius = this.size.minDimension / 2f
            val baseColor = tint.copy(alpha = alpha)

            // Inner core circle
            drawCircle(
                color = baseColor,
                radius = radius * 0.15f,
                center = center,
                style = Stroke(width = 1.8.dp.toPx())
            )

            // Central solid bindu
            drawCircle(
                color = baseColor,
                radius = radius * 0.06f,
                center = center
            )

            // Middle concentric ring
            drawCircle(
                color = baseColor,
                radius = radius * 0.45f,
                center = center,
                style = Stroke(width = 1.4.dp.toPx())
            )

            // Outer decorative ring
            drawCircle(
                color = baseColor,
                radius = radius * 0.82f,
                center = center,
                style = Stroke(width = 1.8.dp.toPx())
            )

            // Innermost 8 lotus petals
            for (i in 0 until 8) {
                val angle = (i * (2 * PI / 8)).toFloat()
                val petallen = radius * 0.42f
                val tipX = center.x + cos(angle) * petallen
                val tipY = center.y + sin(angle) * petallen

                val leftAngle = angle - 0.22f
                val rightAngle = angle + 0.22f
                val ctrlLen = radius * 0.22f

                val p1X = center.x + cos(leftAngle) * ctrlLen
                val p1Y = center.y + sin(leftAngle) * ctrlLen
                val p2X = center.x + cos(rightAngle) * ctrlLen
                val p2Y = center.y + sin(rightAngle) * ctrlLen

                val path = Path().apply {
                    moveTo(center.x, center.y)
                    quadraticTo(p1X, p1Y, tipX, tipY)
                    quadraticTo(p2X, p2Y, center.x, center.y)
                    close()
                }
                drawPath(path = path, color = baseColor, style = Stroke(width = 1.4.dp.toPx()))
            }

            // Outer radial petals (12 or 16)
            for (i in 0 until petalCount) {
                val angle = (i * (2 * PI / petalCount)).toFloat()
                val startR = radius * 0.45f
                val endR = radius * 0.80f

                val tipX = center.x + cos(angle) * endR
                val tipY = center.y + sin(angle) * endR

                val leftAngle = angle - (PI / petalCount).toFloat() * 0.75f
                val rightAngle = angle + (PI / petalCount).toFloat() * 0.75f

                val sideX1 = center.x + cos(leftAngle) * startR
                val sideY1 = center.y + sin(leftAngle) * startR
                val sideX2 = center.x + cos(rightAngle) * startR
                val sideY2 = center.y + sin(rightAngle) * startR

                val path = Path().apply {
                    moveTo(sideX1, sideY1)
                    quadraticTo(
                        center.x + cos(angle) * (startR + (endR - startR) * 0.5f),
                        center.y + sin(angle) * (startR + (endR - startR) * 0.5f),
                        tipX,
                        tipY
                    )
                    quadraticTo(
                        center.x + cos(angle) * (startR + (endR - startR) * 0.5f),
                        center.y + sin(angle) * (startR + (endR - startR) * 0.5f),
                        sideX2,
                        sideY2
                    )
                }
                drawPath(path = path, color = baseColor, style = Stroke(width = 1.5.dp.toPx(), cap = StrokeCap.Round))

                // Radiant bead dot at tip
                val beadX = center.x + cos(angle) * (radius * 0.92f)
                val beadY = center.y + sin(angle) * (radius * 0.92f)
                drawCircle(
                    color = baseColor,
                    radius = 2.2.dp.toPx(),
                    center = Offset(beadX, beadY)
                )
            }
        }
    }
}
