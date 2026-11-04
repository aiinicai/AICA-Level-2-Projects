package com.example.cube.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.RotateRight
import androidx.compose.material.icons.filled.PanTool
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeMove
import kotlin.math.cos
import kotlin.math.sin

/**
 * Professional visual guide illustrating Rubik's cube turn notations (e.g. R, U', F2, L, D, B)
 * using a modern 3D isometric cube render with highlighted rotation layers,
 * luminous directional trajectory arrows, and speedcubing finger-trick instructions.
 */
@Composable
fun MoveVisualDiagram(
    move: CubeMove,
    modifier: Modifier = Modifier,
    size: Dp = 150.dp,
    showDetailedGrip: Boolean = true
) {
    // Continuous animation progress (0f to 1f) for the sweeping glow along the arrow
    val animProgress = remember { Animatable(0f) }
    LaunchedEffect(move) {
        animProgress.snapTo(0f)
        animProgress.animateTo(
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = 1500, easing = LinearEasing),
                repeatMode = RepeatMode.Restart
            )
        )
    }

    // Toggle between 3D Isometric View and 2D Planar Action View
    var isIsometricMode by remember { mutableStateOf(true) }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
        )
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header Bar: Notation Badge, Title, Direction Chip & View Mode Toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                // Notation Badge + Description
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .background(
                                brush = Brush.linearGradient(
                                    colors = listOf(
                                        MaterialTheme.colorScheme.primary,
                                        MaterialTheme.colorScheme.tertiary
                                    )
                                ),
                                shape = RoundedCornerShape(12.dp)
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = move.notation,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.ExtraBold,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text(
                            text = move.description,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface,
                            maxLines = 1
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = move.layerLabel,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = " • ${move.directionName}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                // Angle Badge & View Switcher
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .background(
                                MaterialTheme.colorScheme.primaryContainer,
                                RoundedCornerShape(8.dp)
                            )
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = if (move.isDoubleTurn) "180°" else if (move.isClockwise) "90° CW" else "90° CCW",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }

                    Spacer(Modifier.width(6.dp))

                    Box(
                        modifier = Modifier
                            .clip(CircleShape)
                            .clickable { isIsometricMode = !isIsometricMode }
                            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.7f))
                            .padding(6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (isIsometricMode) Icons.Default.Visibility else Icons.AutoMirrored.Filled.RotateRight,
                            contentDescription = "Switch Visual Mode",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }

            Spacer(Modifier.height(12.dp))

            // Professional Diagram Canvas (3D Isometric or 2D Planar)
            Box(
                modifier = Modifier
                    .size(width = size * 1.5f, height = size)
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        brush = Brush.verticalGradient(
                            colors = listOf(
                                Color(0xFF0F172A),
                                Color(0xFF1E293B)
                            )
                        )
                    )
                    .border(1.dp, Color(0x3338BDF8), RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    if (isIsometricMode) {
                        drawProfessional3DIsoMove(
                            move = move,
                            animProgress = animProgress.value
                        )
                    } else {
                        drawProfessional2DPlanarMove(
                            move = move,
                            animProgress = animProgress.value
                        )
                    }
                }

                // Small mode label overlay
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(6.dp)
                        .background(Color(0x99000000), RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = if (isIsometricMode) "3D Isometric View" else "Frontal Action View",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color(0xFF94A3B8),
                        fontSize = 9.sp
                    )
                }
            }

            // Finger trick tip & Physical Grip Guidance
            if (showDetailedGrip) {
                Spacer(Modifier.height(10.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.65f))
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.PanTool,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Speedcuber Grip & Finger Trick",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            text = move.fingerTrickTip,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 11.sp,
                            lineHeight = 15.sp
                        )
                    }
                }
            }
        }
    }
}

/**
 * Draws an isometric 3D Rubik's cube with realistic cubie sticker tiles,
 * highlighted rotating layer, and 3D luminous directional curved rotation arrow.
 */
private fun DrawScope.drawProfessional3DIsoMove(
    move: CubeMove,
    animProgress: Float
) {
    val w = size.width
    val h = size.height
    val centerX = w / 2f
    val centerY = h / 2f + 4f

    // Scale parameter for cubies
    val cubieSize = minOf(w, h) * 0.17f

    // Isometric unit vectors (30 degree inclination)
    val cos30 = 0.8660254f
    val sin30 = 0.5f

    // Project 3D coordinate (x, y, z) into 2D isometric screen space
    // x: right (+), y: up (+), z: forward/front (+)
    fun project(x: Float, y: Float, z: Float): Offset {
        val screenX = centerX + (x - z) * cos30 * cubieSize
        val screenY = centerY - y * cubieSize + (x + z) * sin30 * cubieSize
        return Offset(screenX, screenY)
    }

    // Determine perspective orientation based on the active move's face:
    // If the move operates on Back (B), Left (L), or Down (D), we adjust orientation so that
    // the moving face is fully visible to the user!
    val isFacingLeft = move.face == CubeFace.L
    val isFacingBottom = move.face == CubeFace.D
    val isFacingBack = move.face == CubeFace.B

    // Standard face colors
    val colWhite = Color(0xFFF8FAFC)
    val colYellow = Color(0xFFFACC15)
    val colGreen = Color(0xFF10B981)
    val colBlue = Color(0xFF3B82F6)
    val colRed = Color(0xFFEF4444)
    val colOrange = Color(0xFFF97316)

    // Highlight color for the rotating layer
    val activeGlow = Color(0xFF38BDF8)
    val arrowGold = Color(0xFFF59E0B)

    // Draw Top Face (U) (y = 1.5)
    // Consists of 3x3 cubies indexed by c (x from -1.5 to 1.5) and r (z from -1.5 to 1.5)
    for (r in 0..2) {
        for (c in 0..2) {
            val x0 = -1.5f + c
            val x1 = x0 + 1f
            val z0 = -1.5f + r
            val z1 = z0 + 1f
            val y = 1.5f

            // Inner sticker padding
            val p = 0.08f
            val p0 = project(x0 + p, y, z0 + p)
            val p1 = project(x1 - p, y, z0 + p)
            val p2 = project(x1 - p, y, z1 - p)
            val p3 = project(x0 + p, y, z1 - p)

            val stickerPath = Path().apply {
                moveTo(p0.x, p0.y)
                lineTo(p1.x, p1.y)
                lineTo(p2.x, p2.y)
                lineTo(p3.x, p3.y)
                close()
            }

            // Is this cubie part of the active layer?
            val isLayerActive = when (move.face) {
                CubeFace.U -> true
                CubeFace.R -> c == 2
                CubeFace.L -> c == 0
                CubeFace.F -> r == 2
                CubeFace.B -> r == 0
                CubeFace.D -> false
            }

            val stickerColor = if (isFacingBottom) colYellow else colWhite
            val shadedColor = if (isLayerActive) {
                activeGlow.copy(alpha = 0.85f)
            } else {
                stickerColor.copy(alpha = 0.9f)
            }

            drawPath(path = stickerPath, color = shadedColor, style = Fill)
            drawPath(
                path = stickerPath,
                color = if (isLayerActive) Color(0xFFE0F2FE) else Color(0x33000000),
                style = Stroke(width = if (isLayerActive) 2.2f else 1.2f)
            )
        }
    }

    // Draw Front Face (F) (z = 1.5)
    // Consists of 3x3 cubies indexed by c (x from -1.5 to 1.5) and r (y from 1.5 down to -1.5)
    for (r in 0..2) {
        for (c in 0..2) {
            val x0 = -1.5f + c
            val x1 = x0 + 1f
            val y1 = 1.5f - r
            val y0 = y1 - 1f
            val z = 1.5f

            val p = 0.08f
            val p0 = project(x0 + p, y1 - p, z)
            val p1 = project(x1 - p, y1 - p, z)
            val p2 = project(x1 - p, y0 + p, z)
            val p3 = project(x0 + p, y0 + p, z)

            val stickerPath = Path().apply {
                moveTo(p0.x, p0.y)
                lineTo(p1.x, p1.y)
                lineTo(p2.x, p2.y)
                lineTo(p3.x, p3.y)
                close()
            }

            val isLayerActive = when (move.face) {
                CubeFace.F -> true
                CubeFace.U -> r == 0
                CubeFace.D -> r == 2
                CubeFace.R -> c == 2
                CubeFace.L -> c == 0
                CubeFace.B -> false
            }

            val stickerColor = if (isFacingBack) colBlue else colGreen
            val shadedColor = if (isLayerActive) {
                activeGlow.copy(alpha = 0.85f)
            } else {
                stickerColor.copy(alpha = 0.88f)
            }

            drawPath(path = stickerPath, color = shadedColor, style = Fill)
            drawPath(
                path = stickerPath,
                color = if (isLayerActive) Color(0xFFE0F2FE) else Color(0x33000000),
                style = Stroke(width = if (isLayerActive) 2.2f else 1.2f)
            )
        }
    }

    // Draw Right Face (R) (x = 1.5)
    // Consists of 3x3 cubies indexed by c (z from 1.5 down to -1.5) and r (y from 1.5 down to -1.5)
    for (r in 0..2) {
        for (c in 0..2) {
            val z1 = 1.5f - c
            val z0 = z1 - 1f
            val y1 = 1.5f - r
            val y0 = y1 - 1f
            val x = 1.5f

            val p = 0.08f
            val p0 = project(x, y1 - p, z1 - p)
            val p1 = project(x, y1 - p, z0 + p)
            val p2 = project(x, y0 + p, z0 + p)
            val p3 = project(x, y0 + p, z1 - p)

            val stickerPath = Path().apply {
                moveTo(p0.x, p0.y)
                lineTo(p1.x, p1.y)
                lineTo(p2.x, p2.y)
                lineTo(p3.x, p3.y)
                close()
            }

            val isLayerActive = when (move.face) {
                CubeFace.R -> true
                CubeFace.U -> r == 0
                CubeFace.D -> r == 2
                CubeFace.F -> c == 0
                CubeFace.B -> c == 2
                CubeFace.L -> false
            }

            val stickerColor = if (isFacingLeft) colOrange else colRed
            val shadedColor = if (isLayerActive) {
                activeGlow.copy(alpha = 0.85f)
            } else {
                stickerColor.copy(alpha = 0.82f)
            }

            drawPath(path = stickerPath, color = shadedColor, style = Fill)
            drawPath(
                path = stickerPath,
                color = if (isLayerActive) Color(0xFFE0F2FE) else Color(0x33000000),
                style = Stroke(width = if (isLayerActive) 2.2f else 1.2f)
            )
        }
    }

    // Draw 3D Isometric Curved Rotation Arrow wrapping around the active layer
    drawIsometricDirectionArrow(
        move = move,
        project = ::project,
        cubieSize = cubieSize,
        animProgress = animProgress,
        arrowColor = arrowGold
    )
}

/**
 * Draws the 3D-transformed curved trajectory arrow and glowing arrowheads
 * wrapping around the specific rotating slice in isometric perspective.
 */
private fun DrawScope.drawIsometricDirectionArrow(
    move: CubeMove,
    project: (Float, Float, Float) -> Offset,
    cubieSize: Float,
    animProgress: Float,
    arrowColor: Color
) {
    val isCw = move.isClockwise
    val is180 = move.isDoubleTurn

    // Calculate arc points in 3D depending on the face
    val arcPoints = mutableListOf<Offset>()
    val steps = 24

    when (move.face) {
        CubeFace.R, CubeFace.L -> {
            // Rotates around X axis at x = +/- 1.7
            val xPos = if (move.face == CubeFace.R) 1.65f else -1.65f
            val radius = 1.6f
            val startAng = if (isCw) 0.3f else 2.6f
            val sweepAng = if (isCw) 2.3f else -2.3f
            val actualSweep = if (is180) sweepAng * 1.35f else sweepAng

            for (i in 0..steps) {
                val t = i.toFloat() / steps
                val angle = startAng + actualSweep * t
                val y = radius * sin(angle)
                val z = radius * cos(angle)
                arcPoints.add(project(xPos, y, z))
            }
        }
        CubeFace.U, CubeFace.D -> {
            // Rotates around Y axis at y = +/- 1.7
            val yPos = if (move.face == CubeFace.U) 1.65f else -1.65f
            val radius = 1.6f
            val startAng = if (isCw) -0.4f else 2.5f
            val sweepAng = if (isCw) 2.5f else -2.5f
            val actualSweep = if (is180) sweepAng * 1.35f else sweepAng

            for (i in 0..steps) {
                val t = i.toFloat() / steps
                val angle = startAng + actualSweep * t
                val x = radius * cos(angle)
                val z = radius * sin(angle)
                arcPoints.add(project(x, yPos, z))
            }
        }
        CubeFace.F, CubeFace.B -> {
            // Rotates around Z axis at z = +/- 1.7
            val zPos = if (move.face == CubeFace.F) 1.65f else -1.65f
            val radius = 1.6f
            val startAng = if (isCw) 2.2f else -0.3f
            val sweepAng = if (isCw) -2.4f else 2.4f
            val actualSweep = if (is180) sweepAng * 1.35f else sweepAng

            for (i in 0..steps) {
                val t = i.toFloat() / steps
                val angle = startAng + actualSweep * t
                val x = radius * cos(angle)
                val y = radius * sin(angle)
                arcPoints.add(project(x, y, zPos))
            }
        }
    }

    if (arcPoints.size < 2) return

    // Draw Glowing Background Halo along the arc
    val path = Path().apply {
        moveTo(arcPoints[0].x, arcPoints[0].y)
        for (i in 1 until arcPoints.size) {
            lineTo(arcPoints[i].x, arcPoints[i].y)
        }
    }

    // Outer Neon Glow
    drawPath(
        path = path,
        color = arrowColor.copy(alpha = 0.35f),
        style = Stroke(width = 11f, cap = StrokeCap.Round)
    )

    // Core Sharp Arrow Stroke
    drawPath(
        path = path,
        color = arrowColor,
        style = Stroke(width = 5.5f, cap = StrokeCap.Round)
    )

    // Animated sweeping energy packet along the trajectory
    val packetIdx = (animProgress * (arcPoints.size - 1)).toInt().coerceIn(0, arcPoints.size - 1)
    val packetPos = arcPoints[packetIdx]
    drawCircle(
        color = Color.White,
        radius = 4.5f,
        center = packetPos
    )

    // Draw Arrowhead at the tip
    val tip = arcPoints.last()
    val prev = arcPoints[arcPoints.size - 2]
    val dx = tip.x - prev.x
    val dy = tip.y - prev.y
    val angle = kotlin.math.atan2(dy, dx)
    val headLen = 14f

    val headPath = Path().apply {
        moveTo(tip.x, tip.y)
        lineTo(
            tip.x - headLen * cos(angle - 0.5f),
            tip.y - headLen * sin(angle - 0.5f)
        )
        lineTo(
            tip.x - headLen * cos(angle + 0.5f),
            tip.y - headLen * sin(angle + 0.5f)
        )
        close()
    }
    drawPath(path = headPath, color = arrowColor, style = Fill)
    drawPath(path = headPath, color = Color.White, style = Stroke(width = 1.5f))

    // If 180° double turn: draw arrowhead on starting tip as well
    if (is180 && arcPoints.size >= 2) {
        val startTip = arcPoints.first()
        val next = arcPoints[1]
        val sdx = startTip.x - next.x
        val sdy = startTip.y - next.y
        val sAngle = kotlin.math.atan2(sdy, sdx)

        val head2Path = Path().apply {
            moveTo(startTip.x, startTip.y)
            lineTo(
                startTip.x - headLen * cos(sAngle - 0.5f),
                startTip.y - headLen * sin(sAngle - 0.5f)
            )
            lineTo(
                startTip.x - headLen * cos(sAngle + 0.5f),
                startTip.y - headLen * sin(sAngle + 0.5f)
            )
            close()
        }
        drawPath(path = head2Path, color = arrowColor, style = Fill)
    }
}

/**
 * Draws the 2D planar action diagram showing direct face view with rotation trajectory.
 */
private fun DrawScope.drawProfessional2DPlanarMove(
    move: CubeMove,
    animProgress: Float
) {
    val w = size.width
    val h = size.height
    val padding = minOf(w, h) * 0.16f
    val gridSize = minOf(w, h) - padding * 2
    val tileSize = gridSize / 3f
    val startX = (w - gridSize) / 2f
    val startY = (h - gridSize) / 2f

    // Face color base palette
    val faceColor = when (move.face) {
        CubeFace.U -> Color(0xFFF8FAFC)
        CubeFace.R -> Color(0xFFEF4444)
        CubeFace.F -> Color(0xFF10B981)
        CubeFace.D -> Color(0xFFFACC15)
        CubeFace.L -> Color(0xFFF97316)
        CubeFace.B -> Color(0xFF3B82F6)
    }

    // Draw 3x3 tiles
    for (row in 0..2) {
        for (col in 0..2) {
            val x = startX + col * tileSize
            val y = startY + row * tileSize
            val inset = 2f

            drawRect(
                color = Color(0xFF1E293B),
                topLeft = Offset(x + inset, y + inset),
                size = androidx.compose.ui.geometry.Size(tileSize - inset * 2, tileSize - inset * 2)
            )
            drawRect(
                color = faceColor.copy(alpha = 0.25f),
                topLeft = Offset(x + inset + 1f, y + inset + 1f),
                size = androidx.compose.ui.geometry.Size(tileSize - (inset + 1f) * 2, tileSize - (inset + 1f) * 2)
            )
        }
    }

    // Center sticker face letter
    val centerTile = Offset(startX + tileSize * 1.5f, startY + tileSize * 1.5f)
    drawCircle(
        color = faceColor,
        radius = tileSize * 0.35f,
        center = centerTile
    )

    // Rotation Sweep Arc
    val arcRadius = gridSize * 0.44f
    val arcRect = Rect(
        centerTile.x - arcRadius,
        centerTile.y - arcRadius,
        centerTile.x + arcRadius,
        centerTile.y + arcRadius
    )

    val isCw = move.isClockwise
    val is180 = move.isDoubleTurn
    val startAngle = if (isCw) 195f else 345f
    val sweepAngle = if (isCw) {
        if (is180) 280f else 220f
    } else {
        if (is180) -280f else -220f
    }

    val arrowPath = Path().apply {
        arcTo(
            rect = arcRect,
            startAngleDegrees = startAngle,
            sweepAngleDegrees = sweepAngle,
            forceMoveTo = true
        )
    }

    val arrowColor = Color(0xFFF59E0B)

    // Halo
    drawPath(
        path = arrowPath,
        color = arrowColor.copy(alpha = 0.35f),
        style = Stroke(width = 11f, cap = StrokeCap.Round)
    )

    // Core
    drawPath(
        path = arrowPath,
        color = arrowColor,
        style = Stroke(width = 5.5f, cap = StrokeCap.Round)
    )

    // Arrowhead
    val tipRad = Math.toRadians((startAngle + sweepAngle).toDouble())
    val tipX = centerTile.x + arcRadius * cos(tipRad).toFloat()
    val tipY = centerTile.y + arcRadius * sin(tipRad).toFloat()
    val tanAngle = if (isCw) tipRad + Math.PI / 2 else tipRad - Math.PI / 2
    val headSize = 15f

    val tipPath = Path().apply {
        moveTo(tipX, tipY)
        lineTo(
            tipX - headSize * cos(tanAngle - 0.5f).toFloat(),
            tipY - headSize * sin(tanAngle - 0.5f).toFloat()
        )
        lineTo(
            tipX - headSize * cos(tanAngle + 0.5f).toFloat(),
            tipY - headSize * sin(tanAngle + 0.5f).toFloat()
        )
        close()
    }
    drawPath(path = tipPath, color = arrowColor, style = Fill)
    drawPath(path = tipPath, color = Color.White, style = Stroke(width = 1.5f))
}
