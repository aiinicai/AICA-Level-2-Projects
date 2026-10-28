package com.example.cube.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.example.cube.model.CubeColor
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import kotlin.math.cos
import kotlin.math.sin

/**
 * Interactive 3D Rubik's Cube renderer with drag-to-rotate,
 * painter's algorithm depth sorting, and active move indicator arrows.
 */
@Composable
fun Cube3DView(
    cubeState: CubeState,
    modifier: Modifier = Modifier,
    activeMove: CubeMove? = null,
    highlightActiveFace: Boolean = true
) {
    // Rotation angles in degrees
    var rotX by remember { mutableFloatStateOf(24f) }
    var rotY by remember { mutableFloatStateOf(38f) }

    // Pulse animation for active move arrow
    val arrowPulse = remember { Animatable(0f) }
    LaunchedEffect(activeMove) {
        if (activeMove != null) {
            arrowPulse.snapTo(0f)
            arrowPulse.animateTo(1f, animationSpec = tween(600))
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    rotY = (rotY + dragAmount.x * 0.45f) % 360f
                    rotX = (rotX - dragAmount.y * 0.45f).coerceIn(-80f, 80f)
                }
            },
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier.fillMaxSize()
        ) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val cubeScale = minOf(size.width, size.height) * 0.15f

            drawRubiksCube(
                cubeState = cubeState,
                center = center,
                scale = cubeScale,
                rotX = rotX,
                rotY = rotY,
                activeMove = activeMove,
                highlightActiveFace = highlightActiveFace
            )
        }

        // Reset camera angle button
        FilledTonalIconButton(
            onClick = {
                rotX = 24f
                rotY = 38f
            },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(12.dp)
                .size(40.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Refresh,
                contentDescription = "Reset 3D view",
                tint = MaterialTheme.colorScheme.onSecondaryContainer
            )
        }
    }
}

private class Quad3D(
    val p0: FloatArray,
    val p1: FloatArray,
    val p2: FloatArray,
    val p3: FloatArray,
    val color: Color,
    val face: CubeFace,
    val isSticker: Boolean
)

private fun DrawScope.drawRubiksCube(
    cubeState: CubeState,
    center: Offset,
    scale: Float,
    rotX: Float,
    rotY: Float,
    activeMove: CubeMove?,
    highlightActiveFace: Boolean
) {
    val radX = Math.toRadians(rotX.toDouble()).toFloat()
    val radY = Math.toRadians(rotY.toDouble()).toFloat()

    val cosX = cos(radX); val sinX = sin(radX)
    val cosY = cos(radY); val sinY = sin(radY)

    fun transform(x: Float, y: Float, z: Float): FloatArray {
        // Rotate Y
        val x1 = x * cosY + z * sinY
        val y1 = y
        val z1 = -x * sinY + z * cosY

        // Rotate X
        val x2 = x1
        val y2 = y1 * cosX - z1 * sinX
        val z2 = y1 * sinX + z1 * cosX

        return floatArrayOf(x2, y2, z2)
    }

    val quads = mutableListOf<Quad3D>()

    // Generate quads for the 54 facelets
    // Coordinate system:
    // x: Left (-1.5) to Right (+1.5)
    // y: Top (-1.5) to Bottom (+1.5)
    // z: Back (-1.5) to Front (+1.5)
    val stickerMargin = 0.08f
    val tileSize = 1.0f

    // 1. Top face (U): y = -1.5, normal points (0, -1, 0)
    for (row in 0..2) { // z goes from -1.5 (Back) to +1.5 (Front)
        for (col in 0..2) { // x goes from -1.5 (Left) to +1.5 (Right)
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[0 * 9 + stickerIdx].composeColor

            val x0 = -1.5f + col * tileSize + stickerMargin
            val x1 = x0 + tileSize - 2 * stickerMargin
            val z0 = -1.5f + row * tileSize + stickerMargin
            val z1 = z0 + tileSize - 2 * stickerMargin
            val y = -1.5f

            quads.add(
                Quad3D(
                    transform(x0, y, z0),
                    transform(x1, y, z0),
                    transform(x1, y, z1),
                    transform(x0, y, z1),
                    color, CubeFace.U, true
                )
            )
        }
    }

    // 2. Bottom face (D): y = +1.5, normal points (0, 1, 0)
    for (row in 0..2) { // row 0 is Front (z=+0.5..+1.5), row 2 is Back (z=-1.5)
        for (col in 0..2) {
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[3 * 9 + stickerIdx].composeColor

            val x0 = -1.5f + col * tileSize + stickerMargin
            val x1 = x0 + tileSize - 2 * stickerMargin
            val z0 = 1.5f - (row + 1) * tileSize + stickerMargin
            val z1 = z0 + tileSize - 2 * stickerMargin
            val y = 1.5f

            quads.add(
                Quad3D(
                    transform(x0, y, z0),
                    transform(x1, y, z0),
                    transform(x1, y, z1),
                    transform(x0, y, z1),
                    color, CubeFace.D, true
                )
            )
        }
    }

    // 3. Front face (F): z = +1.5, normal points (0, 0, 1)
    for (row in 0..2) { // y from -1.5 to +1.5
        for (col in 0..2) { // x from -1.5 to +1.5
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[2 * 9 + stickerIdx].composeColor

            val x0 = -1.5f + col * tileSize + stickerMargin
            val x1 = x0 + tileSize - 2 * stickerMargin
            val y0 = -1.5f + row * tileSize + stickerMargin
            val y1 = y0 + tileSize - 2 * stickerMargin
            val z = 1.5f

            quads.add(
                Quad3D(
                    transform(x0, y0, z),
                    transform(x1, y0, z),
                    transform(x1, y1, z),
                    transform(x0, y1, z),
                    color, CubeFace.F, true
                )
            )
        }
    }

    // 4. Back face (B): z = -1.5, normal points (0, 0, -1)
    for (row in 0..2) {
        for (col in 0..2) { // col 0 is Right (x = +0.5..+1.5), col 2 is Left (x = -1.5)
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[5 * 9 + stickerIdx].composeColor

            val x0 = 1.5f - (col + 1) * tileSize + stickerMargin
            val x1 = x0 + tileSize - 2 * stickerMargin
            val y0 = -1.5f + row * tileSize + stickerMargin
            val y1 = y0 + tileSize - 2 * stickerMargin
            val z = -1.5f

            quads.add(
                Quad3D(
                    transform(x0, y0, z),
                    transform(x1, y0, z),
                    transform(x1, y1, z),
                    transform(x0, y1, z),
                    color, CubeFace.B, true
                )
            )
        }
    }

    // 5. Left face (L): x = -1.5, normal points (-1, 0, 0)
    for (row in 0..2) {
        for (col in 0..2) { // col 0 is Back (z = -1.5), col 2 is Front (z = +1.5)
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[4 * 9 + stickerIdx].composeColor

            val z0 = -1.5f + col * tileSize + stickerMargin
            val z1 = z0 + tileSize - 2 * stickerMargin
            val y0 = -1.5f + row * tileSize + stickerMargin
            val y1 = y0 + tileSize - 2 * stickerMargin
            val x = -1.5f

            quads.add(
                Quad3D(
                    transform(x, y0, z0),
                    transform(x, y0, z1),
                    transform(x, y1, z1),
                    transform(x, y1, z0),
                    color, CubeFace.L, true
                )
            )
        }
    }

    // 6. Right face (R): x = +1.5, normal points (1, 0, 0)
    for (row in 0..2) {
        for (col in 0..2) { // col 0 is Front (z = +1.5), col 2 is Back (z = -1.5)
            val stickerIdx = row * 3 + col
            val color = cubeState.facelets[1 * 9 + stickerIdx].composeColor

            val z0 = 1.5f - (col + 1) * tileSize + stickerMargin
            val z1 = z0 + tileSize - 2 * stickerMargin
            val y0 = -1.5f + row * tileSize + stickerMargin
            val y1 = y0 + tileSize - 2 * stickerMargin
            val x = 1.5f

            quads.add(
                Quad3D(
                    transform(x, y0, z0),
                    transform(x, y0, z1),
                    transform(x, y1, z1),
                    transform(x, y1, z0),
                    color, CubeFace.R, true
                )
            )
        }
    }

    // Sort quads by average Z (Painter's algorithm: smallest Z drawn first, largest Z drawn on top)
    val sortedQuads = quads.filter { quad ->
        // Backface culling: check normal z
        val v1x = quad.p1[0] - quad.p0[0]
        val v1y = quad.p1[1] - quad.p0[1]
        val v2x = quad.p3[0] - quad.p0[0]
        val v2y = quad.p3[1] - quad.p0[1]
        val crossZ = v1x * v2y - v1y * v2x
        crossZ < 0f
    }.sortedBy { quad ->
        (quad.p0[2] + quad.p1[2] + quad.p2[2] + quad.p3[2]) / 4f
    }

    // Draw sorted quads
    for (quad in sortedQuads) {
        val path = Path().apply {
            moveTo(center.x + quad.p0[0] * scale, center.y + quad.p0[1] * scale)
            lineTo(center.x + quad.p1[0] * scale, center.y + quad.p1[1] * scale)
            lineTo(center.x + quad.p2[0] * scale, center.y + quad.p2[1] * scale)
            lineTo(center.x + quad.p3[0] * scale, center.y + quad.p3[1] * scale)
            close()
        }

        // Shading factor based on face orientation
        val shade = when (quad.face) {
            CubeFace.U -> 1.0f
            CubeFace.F -> 0.92f
            CubeFace.R -> 0.85f
            CubeFace.L -> 0.78f
            CubeFace.B -> 0.72f
            CubeFace.D -> 0.65f
        }
        val shadedColor = Color(
            red = quad.color.red * shade,
            green = quad.color.green * shade,
            blue = quad.color.blue * shade,
            alpha = 1f
        )

        // Draw sticker polygon
        drawPath(path = path, color = shadedColor)

        // Draw border bevel
        val isFaceActive = highlightActiveFace && activeMove?.face == quad.face
        val strokeColor = if (isFaceActive) Color(0xFFFBBF24) else Color(0x33000000)
        val strokeWidth = if (isFaceActive) 3.5f else 1.5f
        drawPath(path = path, color = strokeColor, style = Stroke(width = strokeWidth))
    }

    // Draw active rotation indicator arrow on active face
    if (activeMove != null) {
        drawActiveMoveIndicator(
            face = activeMove.face,
            move = activeMove,
            center = center,
            scale = scale,
            transform = ::transform
        )
    }
}

private fun DrawScope.drawActiveMoveIndicator(
    face: CubeFace,
    move: CubeMove,
    center: Offset,
    scale: Float,
    transform: (Float, Float, Float) -> FloatArray
) {
    val radius = 1.0f
    val arcSteps = 18
    val isCw = move.isClockwise
    val is180 = move.isDoubleTurn

    val sweep = if (isCw) {
        if (is180) 2.8f else 2.1f
    } else {
        if (is180) -2.8f else -2.1f
    }
    val startAngle = if (isCw) -1.0f else 1.1f

    val arcPoints = mutableListOf<FloatArray>()

    for (i in 0..arcSteps) {
        val t = i.toFloat() / arcSteps
        val angle = startAngle + sweep * t

        val (x, y, z) = when (face) {
            CubeFace.U -> Triple(radius * cos(angle), -1.65f, radius * sin(angle))
            CubeFace.D -> Triple(radius * cos(angle), 1.65f, -radius * sin(angle))
            CubeFace.F -> Triple(radius * cos(angle), radius * sin(angle), 1.65f)
            CubeFace.B -> Triple(-radius * cos(angle), radius * sin(angle), -1.65f)
            CubeFace.R -> Triple(1.65f, radius * sin(angle), -radius * cos(angle))
            CubeFace.L -> Triple(-1.65f, radius * sin(angle), radius * cos(angle))
        }
        arcPoints.add(transform(x, y, z))
    }

    if (arcPoints.size < 2) return

    val screenPoints = arcPoints.map { tf ->
        Offset(center.x + tf[0] * scale, center.y + tf[1] * scale)
    }

    val arrowPath = Path().apply {
        moveTo(screenPoints[0].x, screenPoints[0].y)
        for (i in 1 until screenPoints.size) {
            lineTo(screenPoints[i].x, screenPoints[i].y)
        }
    }

    val arrowColor = Color(0xFFFBBF24)

    // Outer Glow Halo
    drawPath(
        path = arrowPath,
        color = arrowColor.copy(alpha = 0.4f),
        style = Stroke(width = 10f, cap = StrokeCap.Round)
    )

    // Core Arrow Line
    drawPath(
        path = arrowPath,
        color = arrowColor,
        style = Stroke(width = 4.5f, cap = StrokeCap.Round)
    )

    // Arrowhead at the tip
    val tip = screenPoints.last()
    val prev = screenPoints[screenPoints.size - 2]
    val dx = tip.x - prev.x
    val dy = tip.y - prev.y
    val tipAngle = kotlin.math.atan2(dy, dx)
    val headLen = 13f

    val headPath = Path().apply {
        moveTo(tip.x, tip.y)
        lineTo(
            tip.x - headLen * cos(tipAngle - 0.5f),
            tip.y - headLen * sin(tipAngle - 0.5f)
        )
        lineTo(
            tip.x - headLen * cos(tipAngle + 0.5f),
            tip.y - headLen * sin(tipAngle + 0.5f)
        )
        close()
    }
    drawPath(path = headPath, color = arrowColor)
    drawPath(path = headPath, color = Color.White, style = Stroke(width = 1.2f))

    // If 180° double turn: draw arrowhead on starting tip
    if (is180 && screenPoints.size >= 2) {
        val startTip = screenPoints.first()
        val next = screenPoints[1]
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
        drawPath(path = head2Path, color = arrowColor)
    }
}
