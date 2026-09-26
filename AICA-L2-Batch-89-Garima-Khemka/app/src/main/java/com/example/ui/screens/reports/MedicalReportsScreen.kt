package com.example.ui.screens.reports

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CompareArrows
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.MedicalInformation
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import com.example.data.model.MedicalReport
import com.example.ui.components.AccessibleText
import com.example.ui.components.CalendarDatePickerField
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class ParsedMetric(
    var metric: String,
    var value: String,
    var unit: String,
    var normalRange: String
)

@Composable
fun MedicalReportsScreen(
    reports: List<MedicalReport>,
    onAddReport: (title: String, labName: String, date: String, metricsJson: String, notes: String, fileUri: String?) -> Unit,
    onUpdateReport: (MedicalReport) -> Unit,
    onDeleteReport: (Long) -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) } // 0: All Reports, 1: Compare Past 3 Reports
    var showAddDialog by remember { mutableStateOf(false) }
    var reportToEdit by remember { mutableStateOf<MedicalReport?>(null) }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_upload_report")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Upload Medical Report")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 14.dp)
        ) {
            Spacer(modifier = Modifier.height(4.dp))
            AccessibleText(
                text = "Medical Lab Reports",
                fontSize = 22.sp,
                fontWeight = FontWeight.ExtraBold
            )
            AccessibleText(
                text = "Track blood tests, lipid panels, and compare past 3 reports side-by-side.",
                fontSize = 13.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Upload & Autofill Banner
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showAddDialog = true }
                    .testTag("card_upload_autofill_report"),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF059669).copy(alpha = 0.12f)),
                shape = RoundedCornerShape(14.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(Color(0xFF059669)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Color.White, modifier = Modifier.size(22.dp))
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            AccessibleText(
                                text = "Upload & Autofill Lab Report",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )
                            AccessibleText(
                                text = "Autofills Lab name, Test name, parameters for review/edit.",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    Button(
                        onClick = { showAddDialog = true },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF059669)),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Upload", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Tabs: All Reports vs Compare Past 3 Reports
            TabRow(
                selectedTabIndex = selectedTab,
                modifier = Modifier.fillMaxWidth()
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Description, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("All Reports (${reports.size})")
                        }
                    },
                    modifier = Modifier.testTag("tab_all_reports")
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.CompareArrows, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Compare Past 3")
                        }
                    },
                    modifier = Modifier.testTag("tab_compare_reports")
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            if (selectedTab == 0) {
                // List of all reports
                if (reports.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.MedicalInformation,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(56.dp)
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            AccessibleText(
                                text = "No lab reports uploaded yet",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold
                            )
                            AccessibleText(
                                text = "Upload lab results from Gallery, Camera, or Files to compare trends.",
                                fontSize = 13.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 80.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(reports, key = { it.id }) { report ->
                            ReportCard(
                                report = report,
                                onEdit = { reportToEdit = report },
                                onDelete = { onDeleteReport(report.id) }
                            )
                        }
                    }
                }
            } else {
                ComparePast3ReportsView(reports = reports.take(3))
            }
        }
    }

    // Add Lab Report Dialog with Autofill, Review, Edit, Add & Delete metrics
    if (showAddDialog) {
        LabReportEditDialog(
            report = null,
            onDismiss = { showAddDialog = false },
            onSave = { title, lab, date, metricsJson, notes, uri ->
                onAddReport(title, lab, date, metricsJson, notes, uri)
                showAddDialog = false
            }
        )
    }

    // Edit Existing Lab Report Dialog
    reportToEdit?.let { report ->
        LabReportEditDialog(
            report = report,
            onDismiss = { reportToEdit = null },
            onSave = { title, lab, date, metricsJson, notes, uri ->
                val updated = report.copy(
                    reportTitle = title,
                    labName = lab,
                    reportDate = date,
                    keyMetricsJson = metricsJson,
                    doctorNotes = notes,
                    fileUri = uri
                )
                onUpdateReport(updated)
                reportToEdit = null
            }
        )
    }
}

@Composable
fun LabReportEditDialog(
    report: MedicalReport?,
    onDismiss: () -> Unit,
    onSave: (title: String, lab: String, date: String, metricsJson: String, notes: String, uri: String?) -> Unit
) {
    val isEditing = report != null
    var title by remember { mutableStateOf(report?.reportTitle ?: "") }
    var labName by remember { mutableStateOf(report?.labName ?: "") }
    var date by remember {
        mutableStateOf(if (report != null) com.example.util.DateUtils.formatDisplayDate(report.reportDate) else SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date()))
    }
    var notes by remember { mutableStateOf(report?.doctorNotes ?: "") }
    var fileUri by remember { mutableStateOf(report?.fileUri) }
    var isAutofilled by remember { mutableStateOf(false) }

    // Dynamic metrics list for Review, Edit, Add, Delete
    val metricsList = remember {
        mutableStateListOf<ParsedMetric>().apply {
            if (report != null) {
                addAll(parseMetricsFromJson(report.keyMetricsJson))
            }
        }
    }

    // Autofill simulation function
    val triggerAutofill = {
        title = "Comprehensive Metabolic & Lipid Profile"
        labName = "Dr. Lal PathLabs"
        notes = "Fasting blood sugar and HbA1c slightly elevated. Cholesterol within borderline range. Normal creatinine."
        fileUri = "file://documents/lal_pathlabs_report.pdf"
        metricsList.clear()
        metricsList.add(ParsedMetric("HbA1c", "6.4", "%", "< 5.7"))
        metricsList.add(ParsedMetric("Fasting Blood Sugar", "112", "mg/dL", "70-99"))
        metricsList.add(ParsedMetric("Total Cholesterol", "198", "mg/dL", "< 200"))
        metricsList.add(ParsedMetric("Serum Creatinine", "0.9", "mg/dL", "0.7-1.3"))
        metricsList.add(ParsedMetric("SpO2 / Hemoglobin", "14.2", "g/dL", "13.0-17.0"))
        isAutofilled = true
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(decorFitsSystemWindows = false),
        title = {
            AccessibleText(
                text = if (isEditing) "Edit Medical Lab Report" else "Upload & Autofill Lab Report",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .imePadding()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // One-tap Autofill action
                if (!isEditing) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Color(0xFF059669), modifier = Modifier.size(20.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                AccessibleText(
                                    text = "One-Tap Document Scanner & Autofill",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF047857)
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            AccessibleText(
                                text = "Autofills Lab name, Test name, and imported values for your review.",
                                fontSize = 11.sp,
                                color = Color(0xFF065F46)
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Button(
                                    onClick = triggerAutofill,
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF059669)),
                                    shape = RoundedCornerShape(8.dp),
                                    modifier = Modifier.testTag("btn_autofill_lab_report")
                                ) {
                                    Icon(Icons.Default.PhotoCamera, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    AccessibleText(text = "Scan & Autofill Lab Data", fontSize = 11.sp, color = Color.White, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }

                if (isAutofilled) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = Color(0xFFECFDF5)
                    ) {
                        AccessibleText(
                            text = "✓ Lab details autofilled! Patient can review, edit, delete, or add test parameters below before approving.",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF047857),
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                }

                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Report Title / Test Name") },
                    modifier = Modifier.fillMaxWidth().testTag("input_report_title"),
                    singleLine = true
                )
                OutlinedTextField(
                    value = labName,
                    onValueChange = { labName = it },
                    label = { Text("Diagnostic Center / Lab Name") },
                    modifier = Modifier.fillMaxWidth().testTag("input_lab_name"),
                    singleLine = true
                )
                CalendarDatePickerField(
                    value = date,
                    onValueChange = { date = it },
                    label = "Report Date (Calendar)",
                    tag = "input_report_date",
                    modifier = Modifier.fillMaxWidth()
                )

                // Review, Edit, Delete, Add Test Metrics section
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AccessibleText(
                        text = "Lab Test Metrics (${metricsList.size}):",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )

                    OutlinedButton(
                        onClick = {
                            metricsList.add(ParsedMetric("New Metric", "", "", ""))
                        },
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Add Test", fontSize = 11.sp)
                    }
                }

                metricsList.forEachIndexed { index, item ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))
                    ) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = item.metric,
                                    onValueChange = { item.metric = it },
                                    label = { Text("Test Name", fontSize = 10.sp) },
                                    modifier = Modifier.weight(1f),
                                    singleLine = true
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                OutlinedTextField(
                                    value = item.value,
                                    onValueChange = { item.value = it },
                                    label = { Text("Value", fontSize = 10.sp) },
                                    modifier = Modifier.width(90.dp),
                                    singleLine = true
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                OutlinedTextField(
                                    value = item.unit,
                                    onValueChange = { item.unit = it },
                                    label = { Text("Unit", fontSize = 10.sp) },
                                    modifier = Modifier.width(80.dp),
                                    singleLine = true
                                )
                                IconButton(
                                    onClick = { metricsList.removeAt(index) },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFDC2626), modifier = Modifier.size(16.dp))
                                }
                            }
                        }
                    }
                }

                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Doctor's Remarks / Findings") },
                    modifier = Modifier.fillMaxWidth()
                )

                // Document upload buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    OutlinedButton(
                        onClick = { fileUri = "file://documents/lab_report.pdf" },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.UploadFile, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Files / Drive", fontSize = 11.sp)
                    }

                    OutlinedButton(
                        onClick = { fileUri = "content://gallery/report_image.jpg" },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.AddPhotoAlternate, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Gallery", fontSize = 11.sp)
                    }
                }

                if (!fileUri.isNullOrEmpty()) {
                    AccessibleText(text = "✓ Document Attached", fontSize = 12.sp, color = Color(0xFF047857))
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (title.isNotBlank()) {
                        val metricsJsonArray = metricsList.filter { it.metric.isNotBlank() && it.value.isNotBlank() }.map {
                            "{\"metric\":\"${it.metric.trim()}\",\"value\":\"${it.value.trim()}\",\"unit\":\"${it.unit.trim()}\",\"normalRange\":\"${it.normalRange.trim()}\"}"
                        }
                        val finalJson = "[${metricsJsonArray.joinToString(",")}]"
                        onSave(title.trim(), labName.trim(), date.trim(), finalJson, notes.trim(), fileUri)
                    }
                },
                modifier = Modifier.testTag("btn_approve_save_report")
            ) {
                Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text(if (isEditing) "Save Changes" else "Review & Approve")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun ReportCard(
    report: MedicalReport,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    val metrics = remember(report.keyMetricsJson) {
        parseMetricsFromJson(report.keyMetricsJson)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(16.dp))
            .testTag("card_report_${report.id}"),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF059669)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.MedicalInformation,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        AccessibleText(
                            text = report.reportTitle,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold
                        )
                        AccessibleText(
                            text = "${report.labName} • ${com.example.util.DateUtils.formatDisplayDate(report.reportDate)}",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Row {
                    IconButton(onClick = onEdit, modifier = Modifier.testTag("btn_edit_report_${report.id}")) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit Lab Report", tint = MaterialTheme.colorScheme.primary)
                    }
                    IconButton(onClick = onDelete, modifier = Modifier.testTag("btn_delete_report_${report.id}")) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFDC2626))
                    }
                }
            }

            // Display parsed key metrics
            if (metrics.isNotEmpty()) {
                Spacer(modifier = Modifier.height(10.dp))
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    metrics.forEach { m ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 8.dp, vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            AccessibleText(text = m.metric, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                            AccessibleText(text = "${m.value} ${m.unit}", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            if (report.doctorNotes.isNotBlank()) {
                Spacer(modifier = Modifier.height(8.dp))
                AccessibleText(
                    text = "Remarks: ${report.doctorNotes}",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            // Attached document badge
            if (!report.fileUri.isNullOrEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFEFF6FF)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Description, contentDescription = null, tint = Color(0xFF2563EB), modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(text = "Document Attached", fontSize = 11.sp, color = Color(0xFF1D4ED8), fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}

@Composable
fun ComparePast3ReportsView(reports: List<MedicalReport>) {
    if (reports.isEmpty()) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(32.dp),
            contentAlignment = Alignment.Center
        ) {
            AccessibleText(text = "Need at least 1 report to display comparison.", fontSize = 15.sp)
        }
        return
    }

    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(bottom = 20.dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.TrendingDown, contentDescription = null, tint = Color(0xFF15803D))
                Spacer(modifier = Modifier.width(8.dp))
                AccessibleText(
                    text = "Side-by-side comparison of your latest ${reports.size} lab reports to track health trends over time.",
                    fontSize = 12.sp,
                    color = Color(0xFF14532D)
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Comparison Table
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(scrollState),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                // Table Header with Dates
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AccessibleText(
                        text = "Test Metric",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.width(140.dp)
                    )

                    reports.forEach { report ->
                        Column(
                            modifier = Modifier.width(120.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            AccessibleText(
                                text = com.example.util.DateUtils.formatDisplayDate(report.reportDate),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            AccessibleText(
                                text = report.labName.take(15),
                                fontSize = 10.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))
                Box(modifier = Modifier.height(1.dp).fillMaxWidth().background(MaterialTheme.colorScheme.outlineVariant))
                Spacer(modifier = Modifier.height(10.dp))

                // Standard Metrics Rows
                val metricsToCompare = listOf(
                    "HbA1c" to "% (Normal: < 5.7)",
                    "Fasting Blood Sugar" to "mg/dL (70-99)",
                    "Total Cholesterol" to "mg/dL (< 200)",
                    "Serum Creatinine" to "mg/dL (0.7-1.3)"
                )

                metricsToCompare.forEach { (metricName, unitRange) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.width(140.dp)) {
                            AccessibleText(text = metricName, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                            AccessibleText(text = unitRange, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }

                        reports.forEach { report ->
                            val value = extractMetricValue(report.keyMetricsJson, metricName)
                            Column(
                                modifier = Modifier.width(120.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = if (value != "-") Color(0xFFF1F5F9) else Color.Transparent
                                ) {
                                    AccessibleText(
                                        text = value,
                                        fontSize = 15.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }
                    }
                    Box(modifier = Modifier.height(1.dp).fillMaxWidth().background(MaterialTheme.colorScheme.surfaceVariant))
                }
            }
        }
    }
}

private fun extractMetricValue(json: String, metricName: String): String {
    return try {
        if (!json.contains(metricName)) return "-"
        val regex = "\"metric\":\\s*\"$metricName\",\\s*\"value\":\\s*\"([^\"]+)\"".toRegex()
        val match = regex.find(json)
        match?.groupValues?.get(1) ?: "-"
    } catch (_: Exception) {
        "-"
    }
}

private fun parseMetricsFromJson(json: String): List<ParsedMetric> {
    val result = mutableListOf<ParsedMetric>()
    try {
        val pattern = "\"metric\":\\s*\"([^\"]+)\",\\s*\"value\":\\s*\"([^\"]+)\",\\s*\"unit\":\\s*\"([^\"]*)\"".toRegex()
        pattern.findAll(json).forEach { match ->
            val metric = match.groupValues[1]
            val value = match.groupValues[2]
            val unit = match.groupValues[3]
            result.add(ParsedMetric(metric, value, unit, ""))
        }
    } catch (_: Exception) {}
    return result
}
