package com.example.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun GardenPlantView(
    stage: Int, // 1 to 5
    modifier: Modifier = Modifier,
    size: Dp = 120.dp
) {
    val infiniteTransition = rememberInfiniteTransition(label = "plantSway")
    val swayAngle by infiniteTransition.animateFloat(
        initialValue = -2.5f,
        targetValue = 2.5f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2400, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "sway"
    )

    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .background(
                Brush.radialGradient(
                    colors = listOf(Color(0xFFE8F5E9), Color(0xFFC8E6C9), Color(0xFFA5D6A7))
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val w = this.size.width
            val h = this.size.height

            // 1. Draw soil mound at bottom
            val soilPath = Path().apply {
                moveTo(w * 0.15f, h * 0.85f)
                quadraticTo(w * 0.5f, h * 0.72f, w * 0.85f, h * 0.85f)
                lineTo(w * 0.85f, h)
                lineTo(w * 0.15f, h)
                close()
            }
            drawPath(
                path = soilPath,
                color = Color(0xFF5D4037)
            )

            // Soil rim highlights
            drawOval(
                color = Color(0xFF795548),
                topLeft = Offset(w * 0.25f, h * 0.76f),
                size = Size(w * 0.5f, h * 0.12f)
            )

            when (stage.coerceIn(1, 5)) {
                1 -> drawSeedStage(w, h)
                2 -> drawSproutStage(w, h, swayAngle)
                3 -> drawGrowingPlantStage(w, h, swayAngle)
                4 -> drawBuddingFlowerStage(w, h, swayAngle)
                5 -> drawFruitTreeStage(w, h, swayAngle)
            }
        }
    }
}

private fun DrawScope.drawSeedStage(w: Float, h: Float) {
    // Golden seed in soil
    drawOval(
        color = Color(0xFFF59E0B),
        topLeft = Offset(w * 0.44f, h * 0.70f),
        size = Size(w * 0.12f, h * 0.08f)
    )
    // Tiny green sprout tip
    val tipPath = Path().apply {
        moveTo(w * 0.50f, h * 0.70f)
        quadraticTo(w * 0.53f, h * 0.64f, w * 0.51f, h * 0.60f)
        quadraticTo(w * 0.48f, h * 0.65f, w * 0.50f, h * 0.70f)
    }
    drawPath(tipPath, color = Color(0xFF4CAF50))
}

private fun DrawScope.drawSproutStage(w: Float, h: Float, sway: Float) {
    val stemPath = Path().apply {
        moveTo(w * 0.50f, h * 0.76f)
        cubicTo(
            w * 0.50f, h * 0.60f,
            w * (0.50f + sway * 0.01f), h * 0.52f,
            w * (0.50f + sway * 0.015f), h * 0.44f
        )
    }
    drawPath(
        path = stemPath,
        color = Color(0xFF4CAF50),
        style = androidx.compose.ui.graphics.drawscope.Stroke(width = w * 0.04f)
    )

    // Left leaf
    val leftLeaf = Path().apply {
        val cx = w * 0.49f
        val cy = h * 0.48f
        moveTo(cx, cy)
        quadraticTo(cx - w * 0.18f, cy - h * 0.08f, cx - w * 0.22f, cy)
        quadraticTo(cx - w * 0.12f, cy + h * 0.06f, cx, cy)
    }
    drawPath(leftLeaf, color = Color(0xFF66BB6A))

    // Right leaf
    val rightLeaf = Path().apply {
        val cx = w * 0.51f
        val cy = h * 0.46f
        moveTo(cx, cy)
        quadraticTo(cx + w * 0.18f, cy - h * 0.08f, cx + w * 0.22f, cy)
        quadraticTo(cx + w * 0.12f, cy + h * 0.06f, cx, cy)
    }
    drawPath(rightLeaf, color = Color(0xFF81C784))
}

private fun DrawScope.drawGrowingPlantStage(w: Float, h: Float, sway: Float) {
    // Thicker stem
    val stemPath = Path().apply {
        moveTo(w * 0.50f, h * 0.76f)
        cubicTo(
            w * 0.50f, h * 0.55f,
            w * (0.50f + sway * 0.01f), h * 0.40f,
            w * (0.50f + sway * 0.02f), h * 0.32f
        )
    }
    drawPath(
        path = stemPath,
        color = Color(0xFF2E7D32),
        style = androidx.compose.ui.graphics.drawscope.Stroke(width = w * 0.05f)
    )

    // Lower leaves
    drawOval(color = Color(0xFF4CAF50), topLeft = Offset(w * 0.26f, h * 0.50f), size = Size(w * 0.24f, h * 0.12f))
    drawOval(color = Color(0xFF66BB6A), topLeft = Offset(w * 0.50f, h * 0.46f), size = Size(w * 0.24f, h * 0.12f))

    // Upper foliage
    drawCircle(color = Color(0xFF81C784), radius = w * 0.14f, center = Offset(w * 0.50f, h * 0.30f))
    drawCircle(color = Color(0xFFA5D6A7), radius = w * 0.09f, center = Offset(w * 0.44f, h * 0.26f))
}

private fun DrawScope.drawBuddingFlowerStage(w: Float, h: Float, sway: Float) {
    drawGrowingPlantStage(w, h, sway)

    // Lavender flower petals on top
    val cx = w * 0.50f + sway * 0.02f * w
    val cy = h * 0.28f
    val petalColor = Color(0xFF8B5CF6)
    val petalRadius = w * 0.06f

    drawCircle(color = petalColor, radius = petalRadius, center = Offset(cx - petalRadius, cy))
    drawCircle(color = petalColor, radius = petalRadius, center = Offset(cx + petalRadius, cy))
    drawCircle(color = petalColor, radius = petalRadius, center = Offset(cx, cy - petalRadius))
    drawCircle(color = petalColor, radius = petalRadius, center = Offset(cx, cy + petalRadius))
    // Golden center
    drawCircle(color = Color(0xFFFBBF24), radius = petalRadius * 0.7f, center = Offset(cx, cy))
}

private fun DrawScope.drawFruitTreeStage(w: Float, h: Float, sway: Float) {
    // Tree Trunk
    val trunkPath = Path().apply {
        moveTo(w * 0.46f, h * 0.76f)
        lineTo(w * 0.47f, h * 0.45f)
        lineTo(w * 0.53f, h * 0.45f)
        lineTo(w * 0.54f, h * 0.76f)
        close()
    }
    drawPath(trunkPath, color = Color(0xFF6D4C41))

    // Lush Crown
    drawCircle(color = Color(0xFF2E7D32), radius = w * 0.22f, center = Offset(w * 0.50f, h * 0.38f))
    drawCircle(color = Color(0xFF388E3C), radius = w * 0.18f, center = Offset(w * 0.36f, h * 0.35f))
    drawCircle(color = Color(0xFF4CAF50), radius = w * 0.18f, center = Offset(w * 0.64f, h * 0.35f))
    drawCircle(color = Color(0xFF81C784), radius = w * 0.16f, center = Offset(w * 0.50f, h * 0.25f))

    // Golden Coin Fruits hanging from tree!
    drawCircle(color = Color(0xFFF59E0B), radius = w * 0.05f, center = Offset(w * 0.38f, h * 0.32f))
    drawCircle(color = Color(0xFFFBBF24), radius = w * 0.035f, center = Offset(w * 0.38f, h * 0.32f))

    drawCircle(color = Color(0xFFF59E0B), radius = w * 0.05f, center = Offset(w * 0.62f, h * 0.32f))
    drawCircle(color = Color(0xFFFBBF24), radius = w * 0.035f, center = Offset(w * 0.62f, h * 0.32f))

    drawCircle(color = Color(0xFFF59E0B), radius = w * 0.05f, center = Offset(w * 0.50f, h * 0.20f))
    drawCircle(color = Color(0xFFFBBF24), radius = w * 0.035f, center = Offset(w * 0.50f, h * 0.20f))
}
