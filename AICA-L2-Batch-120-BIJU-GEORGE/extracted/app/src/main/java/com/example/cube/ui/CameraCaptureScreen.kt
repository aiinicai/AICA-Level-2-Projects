package com.example.cube.ui

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Rect
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Collections
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.example.cube.model.CubeColor
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.Executors

data class CaptureStep(
    val faceKey: String,
    val faceName: String,
    val centerColorTip: String,
    val instruction: String,
    val rotationTip: String
)

val ORDERED_CAPTURE_STEPS = listOf(
    CaptureStep(
        faceKey = "F",
        faceName = "FRONT (F)",
        centerColorTip = "Green center",
        instruction = "Hold reference face directly facing camera",
        rotationTip = "Keep this orientation as your spatial reference"
    ),
    CaptureStep(
        faceKey = "L",
        faceName = "LEFT (L)",
        centerColorTip = "Orange center",
        instruction = "Rotate cube 90° to the RIGHT",
        rotationTip = "Viewing the Left face"
    ),
    CaptureStep(
        faceKey = "R",
        faceName = "RIGHT (R)",
        centerColorTip = "Red center",
        instruction = "Rotate back to FRONT, then 90° to the LEFT",
        rotationTip = "Viewing the Right face"
    ),
    CaptureStep(
        faceKey = "U",
        faceName = "UP / TOP (U)",
        centerColorTip = "White center",
        instruction = "Tilt the Front face 90° DOWNWARD",
        rotationTip = "Viewing the Top face"
    ),
    CaptureStep(
        faceKey = "D",
        faceName = "DOWN / BOTTOM (D)",
        centerColorTip = "Yellow center",
        instruction = "Tilt the Front face 90° UPWARD",
        rotationTip = "Viewing the Bottom face"
    ),
    CaptureStep(
        faceKey = "B",
        faceName = "BACK (B)",
        centerColorTip = "Blue center",
        instruction = "Rotate 180° horizontally",
        rotationTip = "Viewing the Back face opposite Front"
    )
)

@Composable
fun CameraCaptureScreen(
    onPhotosCaptured: (Map<String, Bitmap>) -> Unit,
    onNavigateToManualEditor: () -> Unit,
    onBack: () -> Unit,
    isProcessing: Boolean = false
) {
    val context = LocalContext.current
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasCameraPermission = granted
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    if (!hasCameraPermission) {
        CameraPermissionFallback(
            onRequestPermission = { permissionLauncher.launch(Manifest.permission.CAMERA) },
            onUseManualEditor = onNavigateToManualEditor,
            onBack = onBack,
            onLoadSampleCube = { samples ->
                onPhotosCaptured(samples)
            }
        )
    } else {
        CameraCaptureContent(
            context = context,
            onPhotosCaptured = onPhotosCaptured,
            onNavigateToManualEditor = onNavigateToManualEditor,
            onBack = onBack,
            isProcessing = isProcessing
        )
    }
}

@Composable
private fun CameraCaptureContent(
    context: Context,
    onPhotosCaptured: (Map<String, Bitmap>) -> Unit,
    onNavigateToManualEditor: () -> Unit,
    onBack: () -> Unit,
    isProcessing: Boolean
) {
    val lifecycleOwner = LocalLifecycleOwner.current
    var currentStepIndex by remember { mutableIntStateOf(0) }
    val capturedBitmaps = remember { mutableStateMapOf<String, Bitmap>() }
    var previewViewRef by remember { mutableStateOf<PreviewView?>(null) }
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }
    val mainExecutor = remember { ContextCompat.getMainExecutor(context) }

    // State for photo preview confirmation
    var previewConfirmBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var previewConfirmFaceKey by remember { mutableStateOf<String?>(null) }

    // Gallery Picker launcher
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                val inputStream = context.contentResolver.openInputStream(uri)
                val rawBmp = BitmapFactory.decodeStream(inputStream)
                inputStream?.close()
                if (rawBmp != null) {
                    val size = minOf(rawBmp.width, rawBmp.height)
                    val x = (rawBmp.width - size) / 2
                    val y = (rawBmp.height - size) / 2
                    val cropped = Bitmap.createBitmap(rawBmp, x, y, size, size)
                    val step = ORDERED_CAPTURE_STEPS[currentStepIndex]
                    capturedBitmaps[step.faceKey] = cropped
                    if (currentStepIndex < 5) currentStepIndex++
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            cameraExecutor.shutdown()
        }
    }

    val currentStep = ORDERED_CAPTURE_STEPS[currentStepIndex]
    val allCompleted = ORDERED_CAPTURE_STEPS.all { capturedBitmaps.containsKey(it.faceKey) }

    Box(modifier = Modifier.fillMaxSize().background(Color.Black)) {
        // Camera Preview
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx).apply {
                    scaleType = PreviewView.ScaleType.FILL_CENTER
                }
                previewViewRef = previewView

                val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    val capture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build()
                    imageCapture = capture

                    val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(
                            lifecycleOwner,
                            cameraSelector,
                            preview,
                            capture
                        )
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }, ContextCompat.getMainExecutor(ctx))
                previewView
            }
        )

        // 3x3 Overlay Bounding Box Grid (Accurately sized to fit on screen)
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(bottom = 140.dp, top = 120.dp),
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .size(260.dp)
                    .border(3.5.dp, Color(0xFFFBBF24), RoundedCornerShape(14.dp))
                    .background(Color(0x11FBBF24), RoundedCornerShape(14.dp))
            ) {
                // 3x3 Grid lines
                Column(modifier = Modifier.fillMaxSize()) {
                    Row(modifier = Modifier.weight(1f).fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                    }
                    Row(modifier = Modifier.weight(1f).fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                        // Center square with target point
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .border(1.5.dp, Color(0xFFFBBF24)),
                            contentAlignment = Alignment.Center
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(Color(0xFFFBBF24), CircleShape)
                            )
                        }
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                    }
                    Row(modifier = Modifier.weight(1f).fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                        Box(modifier = Modifier.weight(1f).border(0.5.dp, Color(0x66FFFFFF)))
                    }
                }
            }
        }

        // Top Header & Step Guidance Banner
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, start = 16.dp, end = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier
                        .background(Color(0x99000000), CircleShape)
                        .testTag("back_button")
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = Color.White
                    )
                }

                Text(
                    text = "6-Face Capture Protocol",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )

                // Quick test sample button for emulator
                FilledTonalButton(
                    onClick = {
                        val sampleBitmaps = generateScrambledCubeSamplePhotos()
                        capturedBitmaps.clear()
                        capturedBitmaps.putAll(sampleBitmaps)
                    },
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = Color(0x99000000),
                        contentColor = Color(0xFFFBBF24)
                    ),
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                    modifier = Modifier.testTag("test_sample_cube_button")
                ) {
                    Icon(imageVector = Icons.Default.Shuffle, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Sample", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }

            // Step Progress Bar
            LinearProgressIndicator(
                progress = { (currentStepIndex + 1) / 6f },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = Color(0xFFFBBF24),
                trackColor = Color(0x44FFFFFF)
            )

            // Current Face Instruction Card
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xEE0F172A)),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Photo ${currentStepIndex + 1}/6: ${currentStep.faceName}",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFFBBF24)
                        )
                        Text(
                            text = currentStep.centerColorTip,
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF38BDF8)
                        )
                    }
                    Text(
                        text = currentStep.instruction,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        color = Color.White,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                    Text(
                        text = "Align all 9 stickers inside the yellow box • ${currentStep.rotationTip}",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF94A3B8),
                        modifier = Modifier.padding(top = 2.dp)
                    )
                }
            }
        }

        // Bottom Controls & Thumbnails
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .background(Color(0xF0090D16))
                .padding(vertical = 12.dp, horizontal = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Thumbnails strip of the 6 faces
            LazyRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                itemsIndexed(ORDERED_CAPTURE_STEPS) { idx, step ->
                    val bmp = capturedBitmaps[step.faceKey]
                    val isSelected = currentStepIndex == idx
                    val isDone = bmp != null

                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.clickable {
                            currentStepIndex = idx
                        }
                    ) {
                        Box(
                            modifier = Modifier
                                .size(46.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isDone) Color(0xFF1E293B) else Color(0x33FFFFFF))
                                .border(
                                    width = if (isSelected) 2.5.dp else 1.dp,
                                    color = if (isSelected) Color(0xFFFBBF24) else if (isDone) Color(0xFF10B981) else Color(0x66FFFFFF),
                                    shape = RoundedCornerShape(8.dp)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (bmp != null) {
                                Image(
                                    bitmap = bmp.asImageBitmap(),
                                    contentDescription = step.faceName,
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize()
                                )
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = null,
                                    tint = Color(0xFF10B981),
                                    modifier = Modifier
                                        .align(Alignment.TopEnd)
                                        .padding(2.dp)
                                        .size(12.dp)
                                )
                            } else {
                                Text(
                                    text = step.faceKey,
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                            }
                        }
                        Text(
                            text = step.faceKey,
                            style = MaterialTheme.typography.labelSmall,
                            color = if (isSelected) Color(0xFFFBBF24) else Color(0xFF94A3B8),
                            fontSize = 10.sp
                        )
                    }
                }
            }

            // Action row: Gallery import, Shutter Capture, Solve / Manual
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Import from gallery or manual
                FilledTonalButton(
                    onClick = {
                        photoPickerLauncher.launch(
                            androidx.activity.result.PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    },
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = Color(0xFF1E293B),
                        contentColor = Color.White
                    ),
                    contentPadding = ButtonDefaults.TextButtonContentPadding,
                    modifier = Modifier.testTag("gallery_picker_button")
                ) {
                    Icon(imageVector = Icons.Default.Collections, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Gallery", fontSize = 11.sp)
                }

                // Shutter Capture Button (High precision, crops yellow guide region directly)
                IconButton(
                    onClick = {
                        val previewView = previewViewRef
                        val pvBitmap = previewView?.bitmap

                        if (pvBitmap != null) {
                            // Extract exact yellow bounding box region from preview view bitmap
                            val viewW = previewView.width
                            val viewH = previewView.height
                            val bmpW = pvBitmap.width
                            val bmpH = pvBitmap.height

                            // Scale factors between view coordinates and bitmap
                            val scaleX = bmpW.toFloat() / maxOf(1, viewW)
                            val scaleY = bmpH.toFloat() / maxOf(1, viewH)

                            // Guide box is 260dp in center with offset top/bottom padding
                            // In relative coordinates, it occupies the central 60% of width
                            val cropSize = (minOf(bmpW, bmpH) * 0.65f).toInt()
                            val cropX = ((bmpW - cropSize) / 2).coerceIn(0, bmpW - cropSize)
                            val cropY = ((bmpH - cropSize) / 2).coerceIn(0, bmpH - cropSize)

                            val cropped = Bitmap.createBitmap(pvBitmap, cropX, cropY, cropSize, cropSize)
                            capturedBitmaps[currentStep.faceKey] = cropped

                            if (currentStepIndex < 5) {
                                currentStepIndex++
                            }
                        } else {
                            // Fallback to ImageCapture use case
                            val capture = imageCapture ?: return@IconButton
                            capture.takePicture(
                                cameraExecutor,
                                object : ImageCapture.OnImageCapturedCallback() {
                                    override fun onCaptureSuccess(image: ImageProxy) {
                                        val rotation = image.imageInfo.rotationDegrees
                                        val buffer = image.planes[0].buffer
                                        val bytes = ByteArray(buffer.remaining())
                                        buffer.get(bytes)
                                        val rawBitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                                        val rotated = if (rotation != 0 && rawBitmap != null) {
                                            val matrix = Matrix().apply { postRotate(rotation.toFloat()) }
                                            Bitmap.createBitmap(rawBitmap, 0, 0, rawBitmap.width, rawBitmap.height, matrix, true)
                                        } else {
                                            rawBitmap
                                        }

                                        if (rotated != null) {
                                            // Crop central 60% of sensor for yellow guide box
                                            val cropSize = (minOf(rotated.width, rotated.height) * 0.65f).toInt()
                                            val cropX = ((rotated.width - cropSize) / 2).coerceIn(0, rotated.width - cropSize)
                                            val cropY = ((rotated.height - cropSize) / 2).coerceIn(0, rotated.height - cropSize)
                                            val cropped = Bitmap.createBitmap(rotated, cropX, cropY, cropSize, cropSize)

                                            mainExecutor.execute {
                                                capturedBitmaps[currentStep.faceKey] = cropped
                                                if (currentStepIndex < 5) {
                                                    currentStepIndex++
                                                }
                                            }
                                        }
                                        image.close()
                                    }

                                    override fun onError(exception: ImageCaptureException) {
                                        exception.printStackTrace()
                                    }
                                }
                            )
                        }
                    },
                    modifier = Modifier
                        .size(68.dp)
                        .background(Color.White, CircleShape)
                        .border(4.dp, Color(0xFFFBBF24), CircleShape)
                        .testTag("shutter_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.CameraAlt,
                        contentDescription = "Capture face",
                        tint = Color.Black,
                        modifier = Modifier.size(30.dp)
                    )
                }

                // Send to Gemini or switch to Manual
                if (capturedBitmaps.size >= 6) {
                    Button(
                        onClick = {
                            onPhotosCaptured(capturedBitmaps.toMap())
                        },
                        enabled = !isProcessing,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF10B981),
                            contentColor = Color.White
                        ),
                        modifier = Modifier.testTag("solve_gemini_button")
                    ) {
                        if (isProcessing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(imageVector = Icons.Default.AutoFixHigh, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("Solve", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                } else {
                    FilledTonalButton(
                        onClick = onNavigateToManualEditor,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = Color(0xFF1E293B),
                            contentColor = Color(0xFF94A3B8)
                        ),
                        contentPadding = ButtonDefaults.TextButtonContentPadding,
                        modifier = Modifier.testTag("manual_edit_shortcut_button")
                    ) {
                        Icon(imageVector = Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Manual", fontSize = 11.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun CameraPermissionFallback(
    onRequestPermission: () -> Unit,
    onUseManualEditor: () -> Unit,
    onBack: () -> Unit,
    onLoadSampleCube: (Map<String, Bitmap>) -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Default.CameraAlt,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(64.dp)
            )

            Spacer(Modifier.height(16.dp))

            Text(
                text = "Camera Access Required",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = "The 6-face capture protocol scans all faces of your Rubik's cube with spatial rotation guidance.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(Modifier.height(24.dp))

            Button(
                onClick = onRequestPermission,
                modifier = Modifier.fillMaxWidth().testTag("grant_camera_permission_button")
            ) {
                Text("Grant Camera Permission")
            }

            Spacer(Modifier.height(10.dp))

            FilledTonalButton(
                onClick = {
                    val samples = generateScrambledCubeSamplePhotos()
                    onLoadSampleCube(samples)
                },
                modifier = Modifier.fillMaxWidth().testTag("use_sample_cube_button")
            ) {
                Icon(imageVector = Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Test with Sample Scrambled Cube")
            }

            Spacer(Modifier.height(10.dp))

            FilledTonalButton(
                onClick = onUseManualEditor,
                modifier = Modifier.fillMaxWidth().testTag("use_manual_editor_button")
            ) {
                Icon(imageVector = Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Use Manual Palette Editor")
            }

            Spacer(Modifier.height(10.dp))

            TextButton(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Back to Home")
            }
        }
    }
}

/**
 * Generates high quality 3x3 synthetic cube face bitmaps for testing.
 * Follows an interesting scrambled state with valid centers and parity.
 */
fun generateScrambledCubeSamplePhotos(): Map<String, Bitmap> {
    val (scrambleState, _) = CubeState.randomScramble()
    val faces = mapOf(
        "F" to CubeFace.F,
        "L" to CubeFace.L,
        "R" to CubeFace.R,
        "U" to CubeFace.U,
        "D" to CubeFace.D,
        "B" to CubeFace.B
    )

    val bitmaps = mutableMapOf<String, Bitmap>()
    val size = 300
    val tileSize = size / 3f

    faces.forEach { (key, face) ->
        val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        val stickers = scrambleState.getFaceStickers(face)

        // Background
        val bgPaint = Paint().apply { color = android.graphics.Color.parseColor("#111827") }
        canvas.drawRect(0f, 0f, size.toFloat(), size.toFloat(), bgPaint)

        val tilePaint = Paint().apply { isAntiAlias = true }
        val borderPaint = Paint().apply {
            color = android.graphics.Color.parseColor("#030712")
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }

        for (row in 0..2) {
            for (col in 0..2) {
                val idx = row * 3 + col
                val color = stickers[idx]
                val hex = when (color) {
                    CubeColor.WHITE -> "#F8FAFC"
                    CubeColor.RED -> "#EF4444"
                    CubeColor.GREEN -> "#10B981"
                    CubeColor.YELLOW -> "#FBBF24"
                    CubeColor.ORANGE -> "#F97316"
                    CubeColor.BLUE -> "#2563EB"
                }
                tilePaint.color = android.graphics.Color.parseColor(hex)

                val left = col * tileSize + 4f
                val top = row * tileSize + 4f
                val right = (col + 1) * tileSize - 4f
                val bottom = (row + 1) * tileSize - 4f

                canvas.drawRoundRect(left, top, right, bottom, 12f, 12f, tilePaint)
                canvas.drawRoundRect(left, top, right, bottom, 12f, 12f, borderPaint)
            }
        }

        bitmaps[key] = bmp
    }

    return bitmaps
}
