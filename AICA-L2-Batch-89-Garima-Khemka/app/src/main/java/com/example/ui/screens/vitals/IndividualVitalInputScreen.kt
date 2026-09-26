package com.example.ui.screens.vitals

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Air
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.Scale
import androidx.compose.material.icons.filled.Thermostat
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import com.example.ui.components.CalendarDatePickerField
import com.example.ui.components.ClockTimePickerField
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.RoutineVitalLog
import com.example.ui.components.AccessibleText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IndividualVitalInputScreen(
    vitalType: String, // "BLOOD_PRESSURE", "BLOOD_SUGAR", "HEART_RATE", "SPO2", "TEMPERATURE", "WEIGHT_BMI"
    vitals: List<RoutineVitalLog>,
    onBack: () -> Unit,
    onSaveVital: (
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
    onDeleteVital: (Long) -> Unit
) {
    val dateFormat = remember { SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()) }
    val timeFormat = remember { SimpleDateFormat("HH:mm", Locale.getDefault()) }

    var dateInput by remember { mutableStateOf(dateFormat.format(Date())) }
    var timeInput by remember { mutableStateOf(timeFormat.format(Date())) }
    var notesInput by remember { mutableStateOf("") }
    var showSavedBanner by remember { mutableStateOf(false) }

    // Vital specific state
    // 1. Blood Pressure
    var systolicInput by remember { mutableStateOf("") }
    var diastolicInput by remember { mutableStateOf("") }
    var bpPulseInput by remember { mutableStateOf("") }

    // 2. Blood Sugar
    var sugarType by remember { mutableStateOf("FASTING") } // FASTING, PP, RANDOM
    var sugarValueInput by remember { mutableStateOf("") }

    // 3. Heart Rate
    var heartRateInput by remember { mutableStateOf("") }
    var hrState by remember { mutableStateOf("Resting") }

    // 4. SpO2
    var spo2Input by remember { mutableStateOf("") }

    // 5. Temperature
    var tempInput by remember { mutableStateOf("") }
    var tempSite by remember { mutableStateOf("Oral") }

    // 6. Weight & BMI
    var weightInput by remember { mutableStateOf("") }
    var heightInput by remember { mutableStateOf("") }
    var bodyFatInput by remember { mutableStateOf("") }

    val liveBmi = remember {
        derivedStateOf {
            val w = weightInput.toFloatOrNull()
            val h = heightInput.toFloatOrNull()
            if (w != null && h != null && h > 0) {
                val hm = h / 100f
                val b = w / (hm * hm)
                String.format(Locale.getDefault(), "%.1f", b)
            } else null
        }
    }

    val (screenTitle, titleColor, screenIcon) = when (vitalType) {
        "BLOOD_PRESSURE" -> Triple("Blood Pressure", Color(0xFFDC2626), Icons.Default.Favorite)
        "BLOOD_SUGAR" -> Triple("Blood Sugar (Glucose)", Color(0xFF0284C7), Icons.Default.WaterDrop)
        "HEART_RATE" -> Triple("Heart Rate / Pulse", Color(0xFFE11D48), Icons.Default.MonitorHeart)
        "SPO2" -> Triple("Oxygen Saturation (SpO2)", Color(0xFF0D9488), Icons.Default.Air)
        "TEMPERATURE" -> Triple("Body Temperature", Color(0xFFEA580C), Icons.Default.Thermostat)
        "WEIGHT_BMI" -> Triple("Body Weight & BMI", Color(0xFF059669), Icons.Default.Scale)
        else -> Triple("Vital Noting", MaterialTheme.colorScheme.primary, Icons.Default.Favorite)
    }

    // Filter readings for this specific vital and get the 5 most recent
    val recentReadings = remember(vitals, vitalType) {
        val filtered = when (vitalType) {
            "BLOOD_PRESSURE" -> vitals.filter { it.systolicBp != null || it.diastolicBp != null }
            "BLOOD_SUGAR" -> vitals.filter { it.bloodSugarFasting != null || it.bloodSugarPostPrandial != null || it.bloodSugarRandom != null }
            "HEART_RATE" -> vitals.filter { it.pulseBpm != null }
            "SPO2" -> vitals.filter { it.spo2Percentage != null }
            "TEMPERATURE" -> vitals.filter { it.temperatureF != null }
            "WEIGHT_BMI" -> vitals.filter { it.weightKg != null || it.bmi != null }
            else -> vitals
        }
        filtered.sortedWith(
            compareByDescending<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }
                .thenByDescending { it.recordTime }
        ).take(5)
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = screenIcon, contentDescription = null, tint = titleColor, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        AccessibleText(text = "Input $screenTitle", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack, modifier = Modifier.testTag("btn_back_individual_vital")) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to Vitals")
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
                .imePadding(),
            contentPadding = PaddingValues(top = 10.dp, bottom = 80.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Success Notification Banner
            item {
                AnimatedVisibility(visible = showSavedBanner, enter = fadeIn(), exit = fadeOut()) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF059669).copy(alpha = 0.15f)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF059669))
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                AccessibleText(
                                    text = "Reading Recorded Successfully!",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF059669)
                                )
                                AccessibleText(
                                    text = "Updated list of 5 readings is displayed below.",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }
                        }
                    }
                }
            }

            // Dedicated Input Card for this vital only
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(titleColor.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(imageVector = screenIcon, contentDescription = null, tint = titleColor, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                AccessibleText(text = "Enter $screenTitle", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                                AccessibleText(
                                    text = "Only this vital will be saved to your health record.",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        // Calendar & Clock based date and time inputs
                        CalendarDatePickerField(
                            value = dateInput,
                            onValueChange = { dateInput = it },
                            label = "Measurement Date (Calendar)",
                            tag = "input_vital_date",
                            modifier = Modifier.fillMaxWidth()
                        )

                        Spacer(modifier = Modifier.height(6.dp))

                        ClockTimePickerField(
                            value = timeInput,
                            onValueChange = { timeInput = it },
                            label = "Measurement Time (Clock)",
                            tag = "input_vital_time",
                            modifier = Modifier.fillMaxWidth()
                        )

                        // Specific Input Fields based on vitalType
                        when (vitalType) {
                            "BLOOD_PRESSURE" -> {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedTextField(
                                        value = systolicInput,
                                        onValueChange = { systolicInput = it },
                                        label = { Text("Systolic (SYS)") },
                                        placeholder = { Text("120") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                        modifier = Modifier
                                            .weight(1f)
                                            .testTag("input_systolic_bp"),
                                        singleLine = true
                                    )
                                    OutlinedTextField(
                                        value = diastolicInput,
                                        onValueChange = { diastolicInput = it },
                                        label = { Text("Diastolic (DIA)") },
                                        placeholder = { Text("80") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                        modifier = Modifier
                                            .weight(1f)
                                            .testTag("input_diastolic_bp"),
                                        singleLine = true
                                    )
                                }
                                OutlinedTextField(
                                    value = bpPulseInput,
                                    onValueChange = { bpPulseInput = it },
                                    label = { Text("Pulse / Heart Rate (BPM) (Optional)") },
                                    placeholder = { Text("72") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true
                                )
                                Text(
                                    text = "Target: Normal BP is < 120 SYS / < 80 DIA mmHg.",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            "BLOOD_SUGAR" -> {
                                Text(text = "Measurement Condition:", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    listOf(
                                        "FASTING" to "Fasting",
                                        "PP" to "Post-Prandial (2h)",
                                        "RANDOM" to "Random"
                                    ).forEach { (typeKey, label) ->
                                        OutlinedButton(
                                            onClick = { sugarType = typeKey },
                                            modifier = Modifier.weight(1f),
                                            colors = ButtonDefaults.outlinedButtonColors(
                                                containerColor = if (sugarType == typeKey) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                                            ),
                                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 6.dp)
                                        ) {
                                            Text(label, fontSize = 10.sp, maxLines = 1)
                                        }
                                    }
                                }

                                OutlinedTextField(
                                    value = sugarValueInput,
                                    onValueChange = { sugarValueInput = it },
                                    label = { Text("Blood Sugar Value (mg/dL)") },
                                    placeholder = { Text("e.g. 95") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("input_blood_sugar"),
                                    singleLine = true
                                )
                                Text(
                                    text = if (sugarType == "FASTING") "Target Fasting: 70 - 99 mg/dL." else "Target PP: < 140 mg/dL.",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            "HEART_RATE" -> {
                                OutlinedTextField(
                                    value = heartRateInput,
                                    onValueChange = { heartRateInput = it },
                                    label = { Text("Pulse Rate (BPM)") },
                                    placeholder = { Text("e.g. 72") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("input_pulse_rate"),
                                    singleLine = true
                                )
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    listOf("Resting", "Walking", "After Exercise").forEach { st ->
                                        OutlinedButton(
                                            onClick = { hrState = st },
                                            modifier = Modifier.weight(1f),
                                            colors = ButtonDefaults.outlinedButtonColors(
                                                containerColor = if (hrState == st) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                                            )
                                        ) {
                                            Text(st, fontSize = 11.sp)
                                        }
                                    }
                                }
                                Text(
                                    text = "Target: Normal resting heart rate is 60 - 100 beats per minute.",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            "SPO2" -> {
                                OutlinedTextField(
                                    value = spo2Input,
                                    onValueChange = { spo2Input = it },
                                    label = { Text("Oxygen Saturation (%)") },
                                    placeholder = { Text("e.g. 98") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("input_spo2"),
                                    singleLine = true
                                )
                                Text(
                                    text = "Target: Normal SpO2 is 95% - 100%. Less than 92% requires attention.",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            "TEMPERATURE" -> {
                                OutlinedTextField(
                                    value = tempInput,
                                    onValueChange = { tempInput = it },
                                    label = { Text("Body Temperature (°F)") },
                                    placeholder = { Text("e.g. 98.6") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("input_temperature"),
                                    singleLine = true
                                )
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    listOf("Oral", "Forehead", "Axillary").forEach { site ->
                                        OutlinedButton(
                                            onClick = { tempSite = site },
                                            modifier = Modifier.weight(1f),
                                            colors = ButtonDefaults.outlinedButtonColors(
                                                containerColor = if (tempSite == site) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                                            )
                                        ) {
                                            Text(site, fontSize = 11.sp)
                                        }
                                    }
                                }
                                Text(
                                    text = "Target: Normal body temperature is 97.8 °F - 99.0 °F.",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            "WEIGHT_BMI" -> {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedTextField(
                                        value = weightInput,
                                        onValueChange = { weightInput = it },
                                        label = { Text("Weight (kg)") },
                                        placeholder = { Text("e.g. 70.0") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                        modifier = Modifier
                                            .weight(1f)
                                            .testTag("input_weight"),
                                        singleLine = true
                                    )
                                    OutlinedTextField(
                                        value = heightInput,
                                        onValueChange = { heightInput = it },
                                        label = { Text("Height (cm)") },
                                        placeholder = { Text("e.g. 175") },
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                        modifier = Modifier
                                            .weight(1f)
                                            .testTag("input_height"),
                                        singleLine = true
                                    )
                                }

                                if (liveBmi.value != null) {
                                    Surface(
                                        color = Color(0xFF059669).copy(alpha = 0.15f),
                                        shape = RoundedCornerShape(8.dp),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text(
                                            text = "Auto Calculated BMI: ${liveBmi.value} kg/m²",
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 13.sp,
                                            color = Color(0xFF059669),
                                            modifier = Modifier.padding(10.dp)
                                        )
                                    }
                                }

                                OutlinedTextField(
                                    value = bodyFatInput,
                                    onValueChange = { bodyFatInput = it },
                                    label = { Text("Body Fat % (Optional)") },
                                    placeholder = { Text("e.g. 18.5") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true
                                )
                            }
                        }

                        // Notes field
                        OutlinedTextField(
                            value = notesInput,
                            onValueChange = { notesInput = it },
                            label = { Text("Notes (optional)") },
                            placeholder = { Text("e.g. Taken right after morning walk") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )

                        // Save Button
                        Button(
                            onClick = {
                                val d = dateInput.ifBlank { dateFormat.format(Date()) }
                                val t = timeInput.ifBlank { timeFormat.format(Date()) }

                                val finalNotes = when (vitalType) {
                                    "HEART_RATE" -> if (notesInput.isNotBlank()) "$hrState - $notesInput" else hrState
                                    "TEMPERATURE" -> if (notesInput.isNotBlank()) "$tempSite - $notesInput" else tempSite
                                    else -> notesInput
                                }

                                when (vitalType) {
                                    "BLOOD_PRESSURE" -> {
                                        val sys = systolicInput.toIntOrNull()
                                        val dia = diastolicInput.toIntOrNull()
                                        val pulse = bpPulseInput.toIntOrNull()
                                        if (sys != null || dia != null) {
                                            onSaveVital(
                                                d, t, "Blood Pressure",
                                                sys, dia, pulse,
                                                null, null, null,
                                                null, null, null, null,
                                                null, null, finalNotes
                                            )
                                            systolicInput = ""
                                            diastolicInput = ""
                                            bpPulseInput = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }

                                    "BLOOD_SUGAR" -> {
                                        val sugar = sugarValueInput.toFloatOrNull()
                                        if (sugar != null) {
                                            val f = if (sugarType == "FASTING") sugar else null
                                            val pp = if (sugarType == "PP") sugar else null
                                            val r = if (sugarType == "RANDOM") sugar else null
                                            onSaveVital(
                                                d, t, "Blood Sugar",
                                                null, null, null,
                                                f, pp, r,
                                                null, null, null, null,
                                                null, null, finalNotes
                                            )
                                            sugarValueInput = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }

                                    "HEART_RATE" -> {
                                        val hr = heartRateInput.toIntOrNull()
                                        if (hr != null) {
                                            onSaveVital(
                                                d, t, "Heart Rate",
                                                null, null, hr,
                                                null, null, null,
                                                null, null, null, null,
                                                null, null, finalNotes
                                            )
                                            heartRateInput = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }

                                    "SPO2" -> {
                                        val spo2 = spo2Input.toIntOrNull()
                                        if (spo2 != null) {
                                            onSaveVital(
                                                d, t, "SpO2 & Temp",
                                                null, null, null,
                                                null, null, null,
                                                null, null, null, null,
                                                spo2, null, finalNotes
                                            )
                                            spo2Input = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }

                                    "TEMPERATURE" -> {
                                        val temp = tempInput.toFloatOrNull()
                                        if (temp != null) {
                                            onSaveVital(
                                                d, t, "SpO2 & Temp",
                                                null, null, null,
                                                null, null, null,
                                                null, null, null, null,
                                                null, temp, finalNotes
                                            )
                                            tempInput = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }

                                    "WEIGHT_BMI" -> {
                                        val wt = weightInput.toFloatOrNull()
                                        val ht = heightInput.toFloatOrNull()
                                        val bmiVal = liveBmi.value?.toFloatOrNull()
                                        val fat = bodyFatInput.toFloatOrNull()
                                        if (wt != null) {
                                            onSaveVital(
                                                d, t, "Weight & BMI",
                                                null, null, null,
                                                null, null, null,
                                                wt, ht, bmiVal, fat,
                                                null, null, finalNotes
                                            )
                                            weightInput = ""
                                            heightInput = ""
                                            bodyFatInput = ""
                                            notesInput = ""
                                            showSavedBanner = true
                                        }
                                    }
                                }
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp)
                                .testTag("btn_save_individual_vital"),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = titleColor)
                        ) {
                            Text("Save $screenTitle Reading", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Section: Show 5 Readings on Screen when saved
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        AccessibleText(
                            text = "Last 5 Readings Recorded",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        AccessibleText(
                            text = "Showing up to 5 most recent notings for $screenTitle",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Surface(
                        color = titleColor.copy(alpha = 0.12f),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text(
                            text = "${recentReadings.size} / 5",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = titleColor,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        )
                    }
                }
            }

            if (recentReadings.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(24.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(imageVector = screenIcon, contentDescription = null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(36.dp))
                                Spacer(modifier = Modifier.height(8.dp))
                                AccessibleText(text = "No readings recorded yet.", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                                AccessibleText(text = "Fill the form above and tap Save to see your readings here.", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            } else {
                itemsIndexed(recentReadings, key = { _, item -> item.id }) { index, vital ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("vital_reading_item_${vital.id}"),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(1.5.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(
                                modifier = Modifier.weight(1f),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Surface(
                                    shape = CircleShape,
                                    color = titleColor.copy(alpha = 0.15f),
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Box(contentAlignment = Alignment.Center) {
                                        Text(
                                            text = "#${index + 1}",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = titleColor
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.width(10.dp))

                                Column {
                                    AccessibleText(
                                        text = "${com.example.util.DateUtils.formatDisplayDate(vital.recordDate)} at ${vital.recordTime}",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )

                                    // Display value corresponding to this vital
                                    val (displayText, statusLabel, statusColor) = formatVitalReading(vital, vitalType)
                                    AccessibleText(
                                        text = displayText,
                                        fontSize = 15.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )

                                    if (statusLabel.isNotBlank()) {
                                        Surface(
                                            color = statusColor.copy(alpha = 0.15f),
                                            shape = RoundedCornerShape(4.dp),
                                            modifier = Modifier.padding(top = 2.dp)
                                        ) {
                                            Text(
                                                text = statusLabel,
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = statusColor,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }

                                    if (vital.notes.isNotBlank()) {
                                        Text(
                                            text = "Note: ${vital.notes}",
                                            fontSize = 11.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            modifier = Modifier.padding(top = 2.dp)
                                        )
                                    }
                                }
                            }

                            IconButton(
                                onClick = { onDeleteVital(vital.id) },
                                modifier = Modifier.testTag("btn_delete_reading_${vital.id}")
                            ) {
                                Icon(Icons.Default.Delete, contentDescription = "Delete Reading", tint = Color(0xFFDC2626), modifier = Modifier.size(20.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun formatVitalReading(vital: RoutineVitalLog, vitalType: String): Triple<String, String, Color> {
    return when (vitalType) {
        "BLOOD_PRESSURE" -> {
            val s = vital.systolicBp ?: 0
            val d = vital.diastolicBp ?: 0
            val pulseText = if (vital.pulseBpm != null) " • Pulse: ${vital.pulseBpm} bpm" else ""
            val status = if (s < 120 && d < 80) "Normal" else if (s < 130 && d < 80) "Elevated" else "High"
            val color = if (s < 120 && d < 80) Color(0xFF059669) else if (s < 130 && d < 80) Color(0xFFD97706) else Color(0xFFDC2626)
            Triple("$s / $d mmHg$pulseText", status, color)
        }

        "BLOOD_SUGAR" -> {
            val (valStr, typeStr, status, color) = when {
                vital.bloodSugarFasting != null -> {
                    val v = vital.bloodSugarFasting
                    val st = if (v < 100) "Normal Fasting" else if (v < 126) "Pre-Diabetes" else "High Fasting"
                    val col = if (v < 100) Color(0xFF059669) else if (v < 126) Color(0xFFD97706) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "Fasting", st, col)
                }
                vital.bloodSugarPostPrandial != null -> {
                    val v = vital.bloodSugarPostPrandial
                    val st = if (v < 140) "Normal PP" else if (v < 200) "Elevated PP" else "High PP"
                    val col = if (v < 140) Color(0xFF059669) else if (v < 200) Color(0xFFD97706) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "Post-Prandial (2h)", st, col)
                }
                vital.bloodSugarRandom != null -> {
                    val v = vital.bloodSugarRandom
                    val st = if (v < 140) "Normal Random" else "High Random"
                    val col = if (v < 140) Color(0xFF059669) else Color(0xFFDC2626)
                    listOf("$v mg/dL", "Random", st, col)
                }
                else -> listOf("-- mg/dL", "Sugar", "Recorded", Color.Gray)
            }
            Triple("${valStr as String} (${typeStr as String})", status as String, color as Color)
        }

        "HEART_RATE" -> {
            val bpm = vital.pulseBpm ?: 0
            val status = if (bpm in 60..100) "Normal Resting" else if (bpm < 60) "Low (Bradycardia)" else "High (Tachycardia)"
            val col = if (bpm in 60..100) Color(0xFF059669) else Color(0xFFDC2626)
            Triple("$bpm BPM", status, col)
        }

        "SPO2" -> {
            val spo2 = vital.spo2Percentage ?: 0
            val status = if (spo2 >= 95) "Optimal" else if (spo2 >= 90) "Low - Alert" else "Critical Low"
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
            val bmiText = if (vital.bmi != null) " • BMI: ${vital.bmi}" else ""
            val status = if (vital.bmi != null) {
                if (vital.bmi < 18.5f) "Underweight" else if (vital.bmi < 25f) "Normal Weight" else if (vital.bmi < 30f) "Overweight" else "Obese"
            } else "Recorded"
            val col = if (vital.bmi != null && vital.bmi in 18.5f..24.9f) Color(0xFF059669) else Color(0xFF2563EB)
            Triple("$wt kg$bmiText", status, col)
        }

        else -> Triple("Reading", "Recorded", Color(0xFF059669))
    }
}
