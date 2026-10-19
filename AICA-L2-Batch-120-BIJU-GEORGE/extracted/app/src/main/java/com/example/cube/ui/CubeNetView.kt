package com.example.cube.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeState

/**
 * Responsive 2D unfolded cube net representation:
 *        [ U ]
 *  [ L ] [ F ] [ R ] [ B ]
 *        [ D ]
 *
 * Automatically adapts tile size to available screen width so it NEVER overflows.
 */
@Composable
fun CubeNetView(
    cubeState: CubeState,
    modifier: Modifier = Modifier,
    tileSize: Dp? = null,
    selectedFace: CubeFace? = null,
    selectedStickerIndex: Int? = null,
    onStickerClick: ((face: CubeFace, indexOnFace: Int) -> Unit)? = null
) {
    BoxWithConstraints(modifier = modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        // Compute tile size dynamically if not explicitly provided or if provided size would overflow
        // Total width needed = 4 faces * (3 * tile + 2 * tileSpacing + 2 * facePadding) + 3 * interFaceSpacing
        // ≈ 12 * tile + 40dp
        val maxAvailable = maxWidth - 16.dp
        val calculatedTileSize = ((maxAvailable - 36.dp) / 12f).coerceIn(16.dp, 26.dp)
        val effectiveTileSize = tileSize?.coerceAtMost(calculatedTileSize) ?: calculatedTileSize

        val faceCellWidth = effectiveTileSize * 3 + 4.dp + 6.dp // 3 tiles + spacing + padding

        Column(
            modifier = Modifier.padding(vertical = 4.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            // TOP: U face (aligned in column 2, directly above F)
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Spacer(modifier = Modifier.width(faceCellWidth + 2.dp)) // Aligns with L
                FaceGrid(
                    face = CubeFace.U,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.U,
                    selectedStickerIndex = if (selectedFace == CubeFace.U) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
                Spacer(modifier = Modifier.width((faceCellWidth + 2.dp) * 2)) // Balances R and B
            }

            // MIDDLE: L, F, R, B faces side by side
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                FaceGrid(
                    face = CubeFace.L,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.L,
                    selectedStickerIndex = if (selectedFace == CubeFace.L) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
                FaceGrid(
                    face = CubeFace.F,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.F,
                    selectedStickerIndex = if (selectedFace == CubeFace.F) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
                FaceGrid(
                    face = CubeFace.R,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.R,
                    selectedStickerIndex = if (selectedFace == CubeFace.R) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
                FaceGrid(
                    face = CubeFace.B,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.B,
                    selectedStickerIndex = if (selectedFace == CubeFace.B) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
            }

            // BOTTOM: D face (aligned in column 2, directly below F)
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Spacer(modifier = Modifier.width(faceCellWidth + 2.dp)) // Aligns with L
                FaceGrid(
                    face = CubeFace.D,
                    cubeState = cubeState,
                    tileSize = effectiveTileSize,
                    isSelectedFace = selectedFace == CubeFace.D,
                    selectedStickerIndex = if (selectedFace == CubeFace.D) selectedStickerIndex else null,
                    onStickerClick = onStickerClick
                )
                Spacer(modifier = Modifier.width((faceCellWidth + 2.dp) * 2)) // Balances R and B
            }
        }
    }
}

@Composable
fun FaceGrid(
    face: CubeFace,
    cubeState: CubeState,
    tileSize: Dp,
    isSelectedFace: Boolean = false,
    selectedStickerIndex: Int? = null,
    onStickerClick: ((face: CubeFace, indexOnFace: Int) -> Unit)? = null
) {
    val stickers = cubeState.getFaceStickers(face)

    Column(
        modifier = Modifier
            .background(
                color = if (isSelectedFace) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                shape = RoundedCornerShape(6.dp)
            )
            .border(
                width = if (isSelectedFace) 1.5.dp else 0.5.dp,
                color = if (isSelectedFace) MaterialTheme.colorScheme.primary else Color(0x33FFFFFF),
                shape = RoundedCornerShape(6.dp)
            )
            .padding(horizontal = 3.dp, vertical = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = face.name,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            color = if (isSelectedFace) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 9.sp
        )

        for (row in 0..2) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(1.5.dp),
                modifier = Modifier.padding(vertical = 1.dp)
            ) {
                for (col in 0..2) {
                    val index = row * 3 + col
                    val color = stickers[index]
                    val isSelected = selectedStickerIndex == index

                    Box(
                        modifier = Modifier
                            .size(tileSize)
                            .clip(RoundedCornerShape(3.dp))
                            .background(color.composeColor)
                            .border(
                                width = if (isSelected) 2.dp else 0.5.dp,
                                color = if (isSelected) MaterialTheme.colorScheme.primary else Color(0x44000000),
                                shape = RoundedCornerShape(3.dp)
                            )
                            .clickable(enabled = onStickerClick != null) {
                                onStickerClick?.invoke(face, index)
                            }
                            .testTag("sticker_${face.name}_$index"),
                        contentAlignment = Alignment.Center
                    ) {
                        if (index == 4) {
                            // Center sticker indicator dot
                            Box(
                                modifier = Modifier
                                    .size(3.5.dp)
                                    .background(
                                        color.contrastTextColor.copy(alpha = 0.7f),
                                        shape = RoundedCornerShape(2.dp)
                                    )
                            )
                        }
                    }
                }
            }
        }
    }
}
