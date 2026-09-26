package com.example.ui.screens.vitals

import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Air
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.ArrowDropUp
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.Scale
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import com.example.data.model.RoutineVitalLog
import com.example.ui.components.AccessibleText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun VitalsScreen(
    vitals: List<RoutineVitalLog>,
    onAddVital: (
        recordDate: String,
        recordTime: String,
        vitalCategory: String,
        systolicBp: Int?,
        diastolicBp: Int?,
        pulseBpm: Int?,
        bloodSugarFasting: Float?,
        bloodSugarPostPrandial: Float?,
        bloodSugarRandom: Float?,
        weightKg: Float?,
        heightCm: Float?,
        bmi: Float?,
        bodyFatPercentage: Float?,
        spo2Percentage: Int?,
        temperatureF: Float?,
        notes: String
    ) -> Unit,
    onUpdateVital: (RoutineVitalLog) -> Unit,
    onDeleteVital: (Long) -> Unit,
    onExportReport: (context: Context, format: String, durationDays: Int) -> Unit
) {
    val context = LocalContext.current
    var activeVitalScreen by remember { mutableStateOf<String?>(null) }
    var vitalToEdit by remember { mutableStateOf<RoutineVitalLog?>(null) }
    var showExportDialog by remember { mutableStateOf(false) }
    var showFirstTimeGuide by remember { mutableStateOf(false) }

    // If an individual vital screen is selected, open the dedicated input screen
    if (activeVitalScreen != null) {
        IndividualVitalInputScreen(
            vitalType = activeVitalScreen!!,
            vitals = vitals,
            onBack = { activeVitalScreen = null },
            onSaveVital = onAddVital,
            onDeleteVital = onDeleteVital
        )
        return
    }

    // Prepare last 4 readings for each individual vital
    val bpReadings = remember(vitals) {
        vitals.filter { it.systolicBp != null || it.diastolicBp != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    val sugarReadings = remember(vitals) {
        vitals.filter { it.bloodSugarFasting != null || it.bloodSugarPostPrandial != null || it.bloodSugarRandom != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    val pulseReadings = remember(vitals) {
        vitals.filter { it.pulseBpm != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    val spo2Readings = remember(vitals) {
        vitals.filter { it.spo2Percentage != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    val tempReadings = remember(vitals) {
        vitals.filter { it.temperatureF != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    val weightReadings = remember(vitals) {
        vitals.filter { it.weightKg != null || it.bmi != null }
            .sortedWith(compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }.thenByDescending { it.recordTime })
            .take(4)
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { activeVitalScreen = "BLOOD_PRESSURE" },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_add_vital")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Input Vital")
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 14.dp),
            contentPadding = PaddingValues(bottom = 80.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Header Section
            item {
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        AccessibleText(
                            text = "Routine Vitals",
                            fontSize = 22.sp,
                            fontWeight = FontWeight.ExtraBold
                        )
                        AccessibleText(
                            text = "Track last 4 readings of each vital. Tap any vital to input.",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    // Doctor Export Button
                    Button(
                        onClick = { showExportDialog = true },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.testTag("btn_export_vitals_doctor")
                    ) {
                        Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(text = "For Doctor", fontSize = 12.sp, color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }

            // Separate buttons to input individual vitals
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    AccessibleText(
                        text = "Input Individual Vitals",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )

                    // Individual Vital Launch Buttons
                    FlowRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        VitalQuickButton(
                            title = "Blood Pressure",
                            icon = Icons.Default.Favorite,
                            color = Color(0xFFDC2626),
                            testTag = "btn_open_input_bp",
                            onClick = { activeVitalScreen = "BLOOD_PRESSURE" }
                        )
                        VitalQuickButton(
                            title = "Blood Sugar",
                            icon = Icons.Default.WaterDrop,
                            color = Color(0xFF0284C7),
                            testTag = "btn_open_input_sugar",
                            onClick = { activeVitalScreen = "BLOOD_SUGAR" }
                        )
                        VitalQuickButton(
                            title = "Heart Rate",
                            icon = Icons.Default.MonitorHeart,
                            color = Color(0xFFE11D48),
                            testTag = "btn_open_input_heart_rate",
                            onClick = { activeVitalScreen = "HEART_RATE" }
                        )
                        VitalQuickButton(
                            title = "SpO2 (Oxygen)",
                            icon = Icons.Default.Air,
                            color = Color(0xFF0D9488),
                            testTag = "btn_open_input_spo2",
                            onClick = { activeVitalScreen = "SPO2" }
                        )
                        VitalQuickButton(
                            title = "Temperature",
                            icon = Icons.Default.Thermostat,
                            color = Color(0xFFEA580C),
                            testTag = "btn_open_input_temperature",
                            onClick = { activeVitalScreen = "TEMPERATURE" }
                        )
                        VitalQuickButton(
                            title = "Weight & BMI",
                            icon = Icons.Default.Scale,
                            color = Color(0xFF059669),
                            testTag = "btn_open_input_weight",
                            onClick = { activeVitalScreen = "WEIGHT_BMI" }
                        )
                    }
                }
            }

            // First-Time User Guide & Field Reference
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showFirstTimeGuide = !showFirstTimeGuide }
                        .testTag("card_first_time_guide"),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)
                    ),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.HelpOutline,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(20.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                AccessibleText(
                                    text = "Clinical Target Reference Guide",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }
                            Icon(
                                imageVector = if (showFirstTimeGuide) Icons.Default.ArrowDropUp else Icons.Default.ArrowDropDown,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary
                            )
                        }

                        AnimatedVisibility(visible = showFirstTimeGuide) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 10.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                VitalGuideRow(
                                    vitalName = "Blood Pressure (SYS / DIA):",
                                    description = "Top = Systolic (< 120), Bottom = Diastolic (< 80). Pulse = 60-100 bpm.",
                                    color = Color(0xFFDC2626)
                                )
                                VitalGuideRow(
                                    vitalName = "Blood Sugar (Fasting & PP):",
                                    description = "Fasting: 70-99 mg/dL. Post-Prandial (2h): < 140 mg/dL.",
                                    color = Color(0xFF0284C7)
                                )
                                VitalGuideRow(
                                    vitalName = "Weight, BMI & SpO2:",
                                    description = "Normal BMI: 18.5 - 24.9. Normal SpO2: 95% - 100%.",
                                    color = Color(0xFF059669)
                                )
                            }
                        }
                    }
                }
            }

            // Section 1: Blood Pressure Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Blood Pressure",
                    targetRange = "Target: < 120 / < 80 mmHg",
                    vitalTypeKey = "BLOOD_PRESSURE",
                    icon = Icons.Default.Favorite,
                    accentColor = Color(0xFFDC2626),
                    readings = bpReadings,
                    onInputClick = { activeVitalScreen = "BLOOD_PRESSURE" },
                    onDeleteVital = onDeleteVital
                )
            }

            // Section 2: Blood Sugar Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Blood Sugar (Glucose)",
                    targetRange = "Target Fasting: 70-99 • PP: < 140 mg/dL",
                    vitalTypeKey = "BLOOD_SUGAR",
                    icon = Icons.Default.WaterDrop,
                    accentColor = Color(0xFF0284C7),
                    readings = sugarReadings,
                    onInputClick = { activeVitalScreen = "BLOOD_SUGAR" },
                    onDeleteVital = onDeleteVital
                )
            }

            // Section 3: Heart Rate / Pulse Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Heart Rate / Pulse",
                    targetRange = "Target: 60 - 100 Beats Per Min",
                    vitalTypeKey = "HEART_RATE",
                    icon = Icons.Default.MonitorHeart,
                    accentColor = Color(0xFFE11D48),
                    readings = pulseReadings,
                    onInputClick = { activeVitalScreen = "HEART_RATE" },
                    onDeleteVital = onDeleteVital
                )
            }

            // Section 4: Oxygen Saturation (SpO2) Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Oxygen Saturation (SpO2)",
                    targetRange = "Target: 95% - 100% SpO2",
                    vitalTypeKey = "SPO2",
                    icon = Icons.Default.Air,
                    accentColor = Color(0xFF0D9488),
                    readings = spo2Readings,
                    onInputClick = { activeVitalScreen = "SPO2" },
                    onDeleteVital = onDeleteVital
                )
            }

            // Section 5: Body Temperature Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Body Temperature",
                    targetRange = "Target: 97.8 °F - 99.0 °F",
                    vitalTypeKey = "TEMPERATURE",
                    icon = Icons.Default.Thermostat,
                    accentColor = Color(0xFFEA580C),
                    readings = tempReadings,
                    onInputClick = { activeVitalScreen = "TEMPERATURE" },
                    onDeleteVital = onDeleteVital
                )
            }

            // Section 6: Body Weight & BMI Card (Shows Last 4 Readings)
            item {
                VitalCategoryCardWithLast4Readings(
                    vitalName = "Body Weight & BMI",
                    targetRange = "Target BMI: 18.5 - 24.9 kg/m²",
                    vitalTypeKey = "WEIGHT_BMI",
                    icon = Icons.Default.Scale,
                    accentColor = Color(0xFF059669),
                    readings = weightReadings,
                    onInputClick = { activeVitalScreen = "WEIGHT_BMI" },
                    onDeleteVital = onDeleteVital
                )
            }
        }
    }

    // Export Dialog for Doctor
    if (showExportDialog) {
        ExportVitalsDialog(
            onDismiss = { showExportDialog = false },
            onExport = { format, days ->
                onExportReport(context, format, days)
                showExportDialog = false
            }
        )
    }
}

@Composable
private fun VitalQuickButton(
    title: String,
    icon: ImageVector,
    color: Color,
    testTag: String,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        colors = ButtonDefaults.buttonColors(containerColor = color.copy(alpha = 0.12f)),
        shape = RoundedCornerShape(10.dp),
        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp),
        modifier = Modifier.testTag(testTag)
    ) {
        Icon(imageVector = icon, contentDescription = null, tint = color, modifier = Modifier.size(16.dp))
        Spacer(modifier = Modifier.width(6.dp))
        Text(text = title, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = color)
    }
}

@Composable
private fun VitalCategoryCardWithLast4Readings(
    vitalName: String,
    targetRange: String,
    vitalTypeKey: String,
    icon: ImageVector,
    accentColor: Color,
    readings: List<RoutineVitalLog>,
    onInputClick: () -> Unit,
    onDeleteVital: (Long) -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("card_category_${vitalTypeKey.lowercase()}"),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header with title and "+ Input" action
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(accentColor.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(imageVector = icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(18.dp))
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        AccessibleText(text = vitalName, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        AccessibleText(text = targetRange, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }

                Button(
                    onClick = onInputClick,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = accentColor),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.testTag("btn_input_${vitalTypeKey.lowercase()}")
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(2.dp))
                    Text("Input", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Last 4 Readings Display
            if (readings.isEmpty()) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "No readings logged yet.",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "Tap Input to add",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = accentColor,
                            modifier = Modifier.clickable { onInputClick() }
                        )
                    }
                }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    readings.forEachIndexed { index, vital ->
                        val (valText, statusText, statusColor) = formatVitalValue(vital, vitalTypeKey)
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 10.dp, vertical = 6.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Surface(
                                        shape = CircleShape,
                                        color = if (index == 0) accentColor else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                                        modifier = Modifier.size(20.dp)
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Text(
                                                text = "${index + 1}",
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = if (index == 0) Color.White else MaterialTheme.colorScheme.onSurface
                                            )
                                        }
                                    }

                                    Spacer(modifier = Modifier.width(8.dp))

                                    Column {
                                        AccessibleText(
                                            text = valText,
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                        AccessibleText(
                                            text = "${com.example.util.DateUtils.formatDisplayDate(vital.recordDate)} at ${vital.recordTime}${if (vital.notes.isNotBlank()) " • ${vital.notes}" else ""}",
                                            fontSize = 11.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Surface(
                                        color = statusColor.copy(alpha = 0.15f),
                                        shape = RoundedCornerShape(4.dp)
                                    ) {
                                        Text(
                                            text = statusText,
                                            fontSize = 9.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = statusColor,
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                    IconButton(
                                        onClick = { onDeleteVital(vital.id) },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFDC2626), modifier = Modifier.size(16.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun formatVitalValue(vital: RoutineVitalLog, vitalTypeKey: String): Triple<String, String, Color> {
    return when (vitalTypeKey) {
        "BLOOD_PRESSURE" -> {
            val s = vital.systolicBp ?: 0
            val d = vital.diastolicBp ?: 0
            val p = if (vital.pulseBpm != null) " (Pulse: ${vital.pulseBpm} bpm)" else ""
            val status = if (s < 120 && d < 80) "Normal" else if (s < 130 && d < 80) "Elevated" else "High"
            val color = if (s < 120 && d < 80) Color(0xFF059669) else if (s < 130 && d < 80) Color(0xFFD97706) else Color(0xFFDC2626)
            Triple("$s / $d mmHg$p", status, color)
        }

        "BLOOD_SUGAR" -> {
            val (valStr, typeStr, status, col) = when {
                vital.bloodSugarFasting != null -> {
                    val v = vital.bloodSugarFasting
                    val st = if (v < 100) "Normal" else if (v < 126) "Pre-Diabetes" else "High"
                    val c = if (v < 100) Color(0xFF059669) else if (v < 126) Color(0xFFD97706) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "Fasting", st, c)
                }
                vital.bloodSugarPostPrandial != null -> {
                    val v = vital.bloodSugarPostPrandial
                    val st = if (v < 140) "Normal" else if (v < 200) "Elevated" else "High"
                    val c = if (v < 140) Color(0xFF059669) else if (v < 200) Color(0xFFD97706) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "PP", st, c)
                }
                vital.bloodSugarRandom != null -> {
                    val v = vital.bloodSugarRandom
                    val st = if (v < 140) "Normal" else "High"
                    val c = if (v < 140) Color(0xFF059669) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "Random", st, c)
                }
                else -> listOf("-- mg/dL", "Sugar", "Recorded", Color.Gray)
            }
            Triple("${valStr as String} (${typeStr as String})", status as String, col as Color)
        }

        "HEART_RATE" -> {
            val bpm = vital.pulseBpm ?: 0
            val status = if (bpm in 60..100) "Normal" else if (bpm < 60) "Low" else "High"
            val col = if (bpm in 60..100) Color(0xFF059669) else Color(0xFFDC2626)
            Triple("$bpm BPM", status, col)
        }

        "SPO2" -> {
            val spo2 = vital.spo2Percentage ?: 0
            val status = if (spo2 >= 95) "Optimal" else if (spo2 >= 90) "Low" else "Critical"
            val col = if (spo2 >= 95) Color(0xFF059669) else if (spo2 >= 90) Color(0xFFD97706) else Color(0xFFDC2626)
            Triple("$spo2% SpO2", status, col)
        }

        "TEMPERATURE" -> {
            val temp = vital.temperatureF ?: 0f
            val status = if (temp in 97.5f..99.0f) "Normal" else if (temp > 100.4f) "Fever" else "Mild Fever"
            val col = if (temp in 97.5f..99.0f) Color(0xFF059669) else Color(0xFFDC2626)
            Triple("$temp °F", status, col)
        }

        "WEIGHT_BMI" -> {
            val wt = vital.weightKg ?: 0f
            val bmiText = if (vital.bmi != null) " • BMI ${vital.bmi}" else ""
            val status = if (vital.bmi != null) {
                if (vital.bmi < 18.5f) "Underweight" else if (vital.bmi < 25f) "Normal" else if (vital.bmi < 30f) "Overweight" else "Obese"
            } else "Recorded"
            val col = if (vital.bmi != null && vital.bmi in 18.5f..24.9f) Color(0xFF059669) else Color(0xFF2563EB)
            Triple("$wt kg$bmiText", status, col)
        }

        else -> Triple("Recorded", "Logged", Color(0xFF059669))
    }
}

@Composable
private fun VitalGuideRow(vitalName: String, description: String, color: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(color)
                .padding(top = 4.dp)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Column {
            AccessibleText(text = vitalName, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = color)
            AccessibleText(text = description, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
fun ExportVitalsDialog(
    onDismiss: () -> Unit,
    onExport: (format: String, days: Int) -> Unit
) {
    var selectedFormat by remember { mutableStateOf("PDF") }
    var selectedDays by remember { mutableIntStateOf(30) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            AccessibleText(
                text = "Download / Share for Doctor",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                AccessibleText(
                    text = "Generate a formatted clinical report of routine vitals for your doctor's review.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                AccessibleText(text = "Select Duration:", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                listOf(
                    7 to "Past 7 Days (Recent)",
                    15 to "Past 15 Days (Follow-up)",
                    30 to "Past 30 Days (Monthly)",
                    90 to "Past 90 Days (Quarterly)"
                ).forEach { (days, label) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { selectedDays = days },
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(
                            selected = selectedDays == days,
                            onClick = { selectedDays = days }
                        )
                        AccessibleText(text = label, fontSize = 13.sp)
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))
                AccessibleText(text = "Export Format:", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("PDF" to "PDF Summary", "WORD" to "Word Doc (.doc)").forEach { (fmt, label) ->
                        OutlinedButton(
                            onClick = { selectedFormat = fmt },
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = if (selectedFormat == fmt) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                            )
                        ) {
                            Text(label, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { onExport(selectedFormat, selectedDays) },
                modifier = Modifier.testTag("btn_confirm_export_doctor")
            ) {
                Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                AccessibleText(text = "Download & Share", color = Color.White)
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                AccessibleText(text = "Cancel")
            }
        }
    )
}
