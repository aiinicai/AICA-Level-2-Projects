package com.example.ui.screens.prescriptions

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import com.example.service.ExtractedPrescription
import com.example.service.PrescriptionReaderService
import com.example.ui.components.AccessibleText
import com.example.ui.components.CalendarDatePickerField
import com.example.ui.components.TimeSlotEditor
import com.example.ui.viewmodel.AutofillMedInfo
import com.example.util.ImageStorageHelper
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.FilterChipDefaults
import kotlinx.coroutines.launch
import android.net.Uri
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalLayoutApi::class, ExperimentalMaterial3Api::class)
@Composable
fun PrescriptionsScreen(
    prescriptions: List<Prescription>,
    allMedicines: List<Medicine>,
    profiles: List<PatientProfile> = emptyList(),
    activeProfileId: Long? = null,
    onApproveAndSavePrescription: (
        doctorName: String,
        clinic: String,
        disease: String,
        startDate: String,
        endDate: String?,
        advice: String,
        imageUri: String?,
        notes: String,
        isFollowUp: Boolean,
        parentPrescriptionId: Long?,
        medicines: List<AutofillMedInfo>,
        targetProfileId: Long?
    ) -> Unit,
    onUpdatePrescription: (Prescription) -> Unit,
    onDeletePrescription: (Long) -> Unit,
    onAddMedicineClick: (prescriptionId: Long) -> Unit,
    onEditMedicineClick: (Medicine) -> Unit,
    onDeleteMedicineClick: (Long) -> Unit,
    onUpdateMedicine: (Medicine) -> Unit = {}
) {
    var showAddDialog by remember { mutableStateOf(false) }
    var preselectedParentPrescriptionId by remember { mutableStateOf<Long?>(null) }
    var prescriptionToEdit by remember { mutableStateOf<Prescription?>(null) }
    var medicineToEditInPrescription by remember { mutableStateOf<Medicine?>(null) }
    var fullScreenImageUri by remember { mutableStateOf<String?>(null) }

    // Filters for Doctor Name, Medicine Name, Disease
    var selectedDoctorFilter by remember { mutableStateOf<String?>(null) }
    var selectedMedicineFilter by remember { mutableStateOf<String?>(null) }
    var selectedDiseaseFilter by remember { mutableStateOf<String?>(null) }

    // Unique filter options extracted from data
    val allDoctorNames = remember(prescriptions) {
        prescriptions.map { it.doctorName }.filter { it.isNotBlank() }.distinct()
    }
    val allDiseaseNames = remember(prescriptions) {
        prescriptions.map { it.diseaseOrDiagnosis }.filter { it.isNotBlank() }.distinct()
    }
    val allMedicineNames = remember(allMedicines) {
        allMedicines.map { it.name }.filter { it.isNotBlank() }.distinct()
    }

    // Filter logic
    val filteredPrescriptions = prescriptions.filter { pres ->
        val matchesDoctor = selectedDoctorFilter == null || pres.doctorName.equals(selectedDoctorFilter, ignoreCase = true)
        val matchesDisease = selectedDiseaseFilter == null || pres.diseaseOrDiagnosis.equals(selectedDiseaseFilter, ignoreCase = true)
        val matchesMedicine = selectedMedicineFilter == null || allMedicines.any {
            it.prescriptionId == pres.id && it.name.equals(selectedMedicineFilter, ignoreCase = true)
        }
        matchesDoctor && matchesDisease && matchesMedicine
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    preselectedParentPrescriptionId = null
                    showAddDialog = true
                },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_upload_prescription")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Upload Prescription")
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
            item {
                Spacer(modifier = Modifier.height(4.dp))
                AccessibleText(
                    text = "Doctor Prescriptions",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                AccessibleText(
                    text = "Upload prescriptions with autofill. Follow-up prescriptions are linked to originals.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Quick Upload & Autofill Banner Card
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            preselectedParentPrescriptionId = null
                            showAddDialog = true
                        }
                        .testTag("card_upload_autofill_prescription"),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(CircleShape)
                                    .background(MaterialTheme.colorScheme.primary),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Color.White, modifier = Modifier.size(24.dp))
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                AccessibleText(
                                    text = "Upload & Autofill Prescription",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                AccessibleText(
                                    text = "Autofills doctor, diagnosis, medicines & dosages for your approval.",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        Button(
                            onClick = {
                                preselectedParentPrescriptionId = null
                                showAddDialog = true
                            },
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Text("Upload", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Filter Chips Section
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            AccessibleText(
                                text = "Search & Filter Prescriptions:",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold
                            )
                            if (selectedDoctorFilter != null || selectedDiseaseFilter != null || selectedMedicineFilter != null) {
                                Text(
                                    text = "Clear All",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.clickable {
                                        selectedDoctorFilter = null
                                        selectedDiseaseFilter = null
                                        selectedMedicineFilter = null
                                    }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(6.dp))

                        // Filter by Doctor
                        Row(
                            modifier = Modifier.horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            FilterChip(
                                selected = selectedDoctorFilter == null,
                                onClick = { selectedDoctorFilter = null },
                                label = { Text("All Doctors") }
                            )
                            allDoctorNames.forEach { doc ->
                                FilterChip(
                                    selected = selectedDoctorFilter == doc,
                                    onClick = { selectedDoctorFilter = if (selectedDoctorFilter == doc) null else doc },
                                    label = { Text(doc) }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(4.dp))

                        // Filter by Disease
                        Row(
                            modifier = Modifier.horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            FilterChip(
                                selected = selectedDiseaseFilter == null,
                                onClick = { selectedDiseaseFilter = null },
                                label = { Text("All Diagnoses") }
                            )
                            allDiseaseNames.forEach { dis ->
                                FilterChip(
                                    selected = selectedDiseaseFilter == dis,
                                    onClick = { selectedDiseaseFilter = if (selectedDiseaseFilter == dis) null else dis },
                                    label = { Text(dis) }
                                )
                            }
                        }
                    }
                }
            }

            if (filteredPrescriptions.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        AccessibleText(
                            text = "No prescriptions matching current filters.",
                            fontSize = 15.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                items(filteredPrescriptions, key = { it.id }) { pres ->
                    val linkedMedicines = allMedicines.filter { it.prescriptionId == pres.id }
                    val followUps = prescriptions.filter { it.parentPrescriptionId == pres.id }
                    val parentPrescription = if (pres.isFollowUp && pres.parentPrescriptionId != null) {
                        prescriptions.firstOrNull { it.id == pres.parentPrescriptionId }
                    } else null

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(18.dp))
                            .testTag("prescription_card_${pres.id}"),
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(2.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            // Follow-up Badge if this is a follow-up
                            if (pres.isFollowUp) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = Color(0xFFFEF3C7),
                                    modifier = Modifier.padding(bottom = 8.dp)
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(Icons.Default.Info, contentDescription = null, tint = Color(0xFFD97706), modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(6.dp))
                                        AccessibleText(
                                            text = "Follow-up Visit ${parentPrescription?.let { "to original with ${it.doctorName}" } ?: ""}",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFF92400E)
                                        )
                                    }
                                }
                            }

                            // Patient Profile Owner Badge
                            val profileOwner = profiles.firstOrNull { it.id == pres.profileId }
                            if (profileOwner != null) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = Color(0xFFEFF6FF),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)),
                                    modifier = Modifier.padding(bottom = 8.dp)
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(Icons.Default.Person, contentDescription = null, tint = Color(0xFF2563EB), modifier = Modifier.size(14.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        AccessibleText(
                                            text = "Patient: ${profileOwner.name} (${profileOwner.age}y)",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFF1D4ED8)
                                        )
                                    }
                                }
                            }

                            // Header: Doctor & Hospital
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(42.dp)
                                            .clip(CircleShape)
                                            .background(if (pres.isFollowUp) Color(0xFFD97706) else Color(0xFF0D9488)),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.LocalHospital,
                                            contentDescription = null,
                                            tint = Color.White,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column {
                                        AccessibleText(
                                            text = pres.doctorName,
                                            fontSize = 17.sp,
                                            fontWeight = FontWeight.Bold
                                        )
                                        AccessibleText(
                                            text = pres.clinicOrHospital,
                                            fontSize = 13.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }

                                Row {
                                    IconButton(onClick = { prescriptionToEdit = pres }) {
                                        Icon(Icons.Default.Edit, contentDescription = "Edit Prescription")
                                    }
                                    IconButton(onClick = { onDeletePrescription(pres.id) }) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFDC2626))
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            // Diagnosis & Date
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = MaterialTheme.colorScheme.primaryContainer
                            ) {
                                AccessibleText(
                                    text = "Diagnosis: ${pres.diseaseOrDiagnosis}",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            val startDisplay = com.example.util.DateUtils.formatDisplayDate(pres.startDate)
                            val endDisplay = com.example.util.DateUtils.formatDisplayDate(pres.endDate)
                            val dateLabel = if (pres.endDate.isNullOrBlank()) {
                                "Prescribed: $startDisplay • Regular / Ongoing Medication"
                            } else {
                                "Duration: $startDisplay to $endDisplay"
                            }
                            AccessibleText(
                                text = dateLabel,
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            if (pres.dischargeAdvice.isNotBlank()) {
                                Spacer(modifier = Modifier.height(8.dp))
                                AccessibleText(
                                    text = "Advice: ${pres.dischargeAdvice}",
                                    fontSize = 13.sp,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }

                            // Attached prescription photo thumbnail
                            if (!pres.imageUri.isNullOrEmpty()) {
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(10.dp))
                                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                                        .clickable { fullScreenImageUri = pres.imageUri }
                                        .padding(8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    AsyncImage(
                                        model = pres.imageUri,
                                        contentDescription = "Prescription Photo",
                                        modifier = Modifier
                                            .size(52.dp)
                                            .clip(RoundedCornerShape(8.dp)),
                                        contentScale = ContentScale.Crop
                                    )
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column(modifier = Modifier.weight(1f)) {
                                        AccessibleText(text = "Prescription Document Attached", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                                        AccessibleText(text = "Tap to view full image & zoom", fontSize = 11.sp, color = MaterialTheme.colorScheme.primary)
                                    }
                                }
                            }

                            // Linked Prescribed Medicines List
                            Spacer(modifier = Modifier.height(12.dp))
                            AccessibleText(
                                text = "Prescribed Medicines (${linkedMedicines.size}):",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )

                            linkedMedicines.forEach { med ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                                        .padding(horizontal = 10.dp, vertical = 6.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        AccessibleText(text = med.name, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                                        AccessibleText(text = "${med.dosage} • ${med.instructions} • Times: ${med.scheduledTimes}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                    Row {
                                        IconButton(onClick = { medicineToEditInPrescription = med }, modifier = Modifier.size(32.dp)) {
                                            Icon(Icons.Default.Edit, contentDescription = "Edit medicine", modifier = Modifier.size(16.dp))
                                        }
                                        IconButton(onClick = { onDeleteMedicineClick(med.id) }, modifier = Modifier.size(32.dp)) {
                                            Icon(Icons.Default.Delete, contentDescription = "Delete medicine", tint = Color(0xFFDC2626), modifier = Modifier.size(16.dp))
                                        }
                                    }
                                }
                            }

                            // Action buttons: Add medicine OR Add follow-up
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                OutlinedButton(
                                    onClick = { onAddMedicineClick(pres.id) },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(10.dp)
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    AccessibleText(text = "Add Medicine", fontSize = 11.sp)
                                }

                                if (!pres.isFollowUp) {
                                    Button(
                                        onClick = {
                                            preselectedParentPrescriptionId = pres.id
                                            showAddDialog = true
                                        },
                                        modifier = Modifier.weight(1f),
                                        shape = RoundedCornerShape(10.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0D9488))
                                    ) {
                                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        AccessibleText(text = "Add Follow-up", fontSize = 11.sp, color = Color.White)
                                    }
                                }
                            }

                            // If original prescription has follow-ups linked, show count
                            if (followUps.isNotEmpty()) {
                                Spacer(modifier = Modifier.height(6.dp))
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = Color(0xFFF0FDF4),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    AccessibleText(
                                        text = "✓ ${followUps.size} Follow-up visit(s) linked to this original prescription",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = Color(0xFF15803D),
                                        modifier = Modifier.padding(8.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Add Prescription Dialog with Autofill & Patient Approval
    if (showAddDialog) {
        val context = LocalContext.current
        val coroutineScope = rememberCoroutineScope()
        var doctorName by remember { mutableStateOf("") }
        var clinic by remember { mutableStateOf("") }
        var disease by remember { mutableStateOf("") }
        var startDate by remember { mutableStateOf(SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())) }
        var endDate by remember { mutableStateOf("") }
        var advice by remember { mutableStateOf("") }
        var notes by remember { mutableStateOf("") }
        var isFollowUp by remember { mutableStateOf(preselectedParentPrescriptionId != null) }
        var parentPrescriptionId by remember { mutableStateOf(preselectedParentPrescriptionId) }
        var simulatedImageUri by remember { mutableStateOf<String?>(null) }
        var uploadedImageUri by remember { mutableStateOf<String?>(null) }
        var isAutofilled by remember { mutableStateOf(false) }
        var isReadingPrescription by remember { mutableStateOf(false) }
        var extractionMessage by remember { mutableStateOf<String?>(null) }
        var editingMedIndex by remember { mutableStateOf<Int?>(null) }
        var showAddMedInlineDialog by remember { mutableStateOf(false) }
        var selectedProfileId by remember { mutableStateOf(activeProfileId ?: profiles.firstOrNull()?.id ?: 1L) }

        // Autofilled medicines list that patient can review & edit
        val autofilledMeds = remember { mutableStateListOf<AutofillMedInfo>() }

        val processExtractedPrescription: (ExtractedPrescription) -> Unit = { extracted ->
            doctorName = extracted.doctorName
            clinic = extracted.clinicOrHospital
            disease = extracted.diseaseOrDiagnosis
            startDate = extracted.startDate
            endDate = extracted.endDate ?: ""
            advice = extracted.dischargeAdvice
            notes = extracted.notes
            autofilledMeds.clear()
            autofilledMeds.addAll(extracted.medicines)
            isAutofilled = true
            isReadingPrescription = false
            extractionMessage = extracted.statusMessage
        }

        // Real Photo Picker launcher
        val photoPickerLauncher = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickVisualMedia()
        ) { uri ->
            if (uri != null) {
                val saved = ImageStorageHelper.saveImageToInternalStorage(context, uri, "prescription")
                uploadedImageUri = saved
                simulatedImageUri = null
                isReadingPrescription = true
                extractionMessage = "Scanning uploaded prescription with Gemini AI..."

                coroutineScope.launch {
                    val extracted = PrescriptionReaderService.readPrescriptionImage(context, Uri.parse(saved))
                    processExtractedPrescription(extracted)
                }
            }
        }

        // Quick sample prescription loader
        val loadSamplePrescription: (String) -> Unit = { sampleType ->
            isReadingPrescription = true
            extractionMessage = "Reading prescription details & reminder schedule..."
            simulatedImageUri = "android.resource://com.example/drawable/ic_distinct_medicine_alarm"
            uploadedImageUri = null

            coroutineScope.launch {
                val extracted = PrescriptionReaderService.fallbackSmartExtraction(hasCustomImage = false, sampleType = sampleType)
                processExtractedPrescription(extracted)
            }
        }

        // Re-read current attached image
        val reReadCurrentImage: () -> Unit = {
            val activeUri = uploadedImageUri ?: simulatedImageUri
            if (activeUri != null) {
                isReadingPrescription = true
                extractionMessage = "Analyzing prescription with Gemini AI..."
                coroutineScope.launch {
                    val extracted = PrescriptionReaderService.readPrescriptionImage(context, Uri.parse(activeUri))
                    processExtractedPrescription(extracted)
                }
            }
        }

        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(
                    text = if (isFollowUp) "Add Follow-up Prescription" else "Upload & Read Prescription",
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
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Profile Selection (Fix: asks which profile reminder to be set in)
                    if (profiles.isNotEmpty()) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Person, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    AccessibleText(
                                        text = "Set Reminders For Patient Profile:",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                                Spacer(modifier = Modifier.height(3.dp))
                                AccessibleText(
                                    text = "Select who this prescription & reminder schedule belongs to:",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .horizontalScroll(rememberScrollState()),
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    profiles.forEach { profile ->
                                        FilterChip(
                                            selected = selectedProfileId == profile.id,
                                            onClick = { selectedProfileId = profile.id },
                                            label = { Text("👤 ${profile.name} (${profile.age}y)") },
                                            colors = FilterChipDefaults.filterChipColors(
                                                selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                                selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                            )
                                        )
                                    }
                                }
                            }
                        }
                    }

                    // Upload / Scan Prescription Card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            // Action Button: Pick Photo from device
                            Button(
                                onClick = {
                                    photoPickerLauncher.launch(
                                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                    )
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier.fillMaxWidth().testTag("btn_pick_prescription_photo")
                            ) {
                                Icon(Icons.Default.PhotoCamera, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                AccessibleText(
                                    text = if (uploadedImageUri != null) "Change Prescription Photo" else "Upload Prescription Photo",
                                    fontSize = 13.sp,
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            // Sample prescription quick-test chips
                            AccessibleText(
                                text = "Or test with instant clinical presets:",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color(0xFF4B5563)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                FilterChip(
                                    selected = false,
                                    onClick = { loadSamplePrescription("TAPER") },
                                    label = { Text("📉 Tapering Rx (17th Sept)", fontSize = 11.sp, fontWeight = FontWeight.Bold) },
                                    colors = FilterChipDefaults.filterChipColors(
                                        containerColor = Color(0xFFFEF3C7),
                                        labelColor = Color(0xFF92400E)
                                    )
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadSamplePrescription("CARDIO") },
                                    label = { Text("🫀 Cardiology Rx", fontSize = 11.sp) }
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadSamplePrescription("DIABETES") },
                                    label = { Text("🩸 Diabetes Rx", fontSize = 11.sp) }
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadSamplePrescription("INFECTION") },
                                    label = { Text("💊 Infection Rx", fontSize = 11.sp) }
                                )
                            }

                            // If an image is selected, show preview thumbnail & actions
                            val activeImage = uploadedImageUri ?: simulatedImageUri
                            if (activeImage != null) {
                                Spacer(modifier = Modifier.height(10.dp))
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp),
                                    colors = CardDefaults.cardColors(containerColor = Color.White)
                                ) {
                                    Column(modifier = Modifier.padding(8.dp)) {
                                        AsyncImage(
                                            model = activeImage,
                                            contentDescription = "Uploaded Prescription",
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .height(140.dp)
                                                .clip(RoundedCornerShape(6.dp)),
                                            contentScale = ContentScale.Crop
                                        )
                                        Spacer(modifier = Modifier.height(6.dp))
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF16A34A), modifier = Modifier.size(16.dp))
                                                Spacer(modifier = Modifier.width(4.dp))
                                                AccessibleText(text = "Photo Attached", fontSize = 12.sp, color = Color(0xFF16A34A), fontWeight = FontWeight.Bold)
                                            }
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                IconButton(
                                                    onClick = reReadCurrentImage,
                                                    modifier = Modifier.size(32.dp)
                                                ) {
                                                    Icon(Icons.Default.Refresh, contentDescription = "Re-read with AI", tint = Color(0xFF2563EB), modifier = Modifier.size(18.dp))
                                                }
                                                IconButton(
                                                    onClick = {
                                                        uploadedImageUri = null
                                                        simulatedImageUri = null
                                                    },
                                                    modifier = Modifier.size(32.dp)
                                                ) {
                                                    Icon(Icons.Default.Clear, contentDescription = "Remove Photo", tint = Color.Gray, modifier = Modifier.size(18.dp))
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Reading in Progress Banner
                    if (isReadingPrescription) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF3C7)),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    strokeWidth = 2.5.dp,
                                    color = Color(0xFFD97706)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    AccessibleText(
                                        text = "Reading Prescription...",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF92400E)
                                    )
                                    AccessibleText(
                                        text = extractionMessage ?: "Extracting medicines and schedule times",
                                        fontSize = 11.sp,
                                        color = Color(0xFFB45309)
                                    )
                                }
                            }
                        }
                    } else if (extractionMessage != null) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFECFDF5),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF059669), modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                AccessibleText(
                                    text = extractionMessage ?: "",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color(0xFF065F46)
                                )
                            }
                        }
                    }

                    // Follow-up Prescription Linkage
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = isFollowUp,
                            onCheckedChange = { isFollowUp = it }
                        )
                        AccessibleText(
                            text = "Link to existing prescription (Follow-up)",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }

                    if (isFollowUp && prescriptions.isNotEmpty()) {
                        AccessibleText(text = "Select Original Prescription:", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        prescriptions.filter { !it.isFollowUp }.forEach { p ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(
                                        if (parentPrescriptionId == p.id) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                                    )
                                    .clickable { parentPrescriptionId = p.id }
                                    .padding(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                AccessibleText(
                                    text = "${p.doctorName} • ${p.diseaseOrDiagnosis} (${com.example.util.DateUtils.formatDisplayDate(p.startDate)})",
                                    fontSize = 12.sp,
                                    fontWeight = if (parentPrescriptionId == p.id) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        }
                    }

                    // Doctor & Clinic Fields
                    OutlinedTextField(
                        value = doctorName,
                        onValueChange = { doctorName = it },
                        label = { Text("Doctor Name") },
                        modifier = Modifier.fillMaxWidth().testTag("input_pres_doctor"),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = clinic,
                        onValueChange = { clinic = it },
                        label = { Text("Hospital / Clinic Name") },
                        modifier = Modifier.fillMaxWidth().testTag("input_pres_clinic"),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = disease,
                        onValueChange = { disease = it },
                        label = { Text("Disease / Diagnosis") },
                        modifier = Modifier.fillMaxWidth().testTag("input_pres_diagnosis"),
                        singleLine = true
                    )
                    CalendarDatePickerField(
                        value = startDate,
                        onValueChange = { startDate = it },
                        label = "Start Date (Calendar)",
                        tag = "input_pres_start_date",
                        modifier = Modifier.fillMaxWidth()
                    )
                    CalendarDatePickerField(
                        value = endDate,
                        onValueChange = { endDate = it },
                        label = "End Date (Calendar)",
                        placeholder = "Blank if ongoing",
                        tag = "input_pres_end_date",
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = advice,
                        onValueChange = { advice = it },
                        label = { Text("Discharge & Lifestyle Advice") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = notes,
                        onValueChange = { notes = it },
                        label = { Text("Doctor's Notes & Follow-up Advice") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Extracted Medicines & Reminder Schedule Section
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color(0xFFF8FAFC))
                            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
                            .padding(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                AccessibleText(
                                    text = "Medication Reminders (${autofilledMeds.size})",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF0F172A)
                                )
                                AccessibleText(
                                    text = "Reminders & alarms will trigger at these exact times",
                                    fontSize = 11.sp,
                                    color = Color(0xFF64748B)
                                )
                            }
                            Button(
                                onClick = { showAddMedInlineDialog = true },
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                AccessibleText(text = "Add Med", fontSize = 12.sp, color = Color.White)
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        if (autofilledMeds.isEmpty()) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 14.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                AccessibleText(
                                    text = "No medicines detected yet. Upload a prescription photo above or tap a preset to auto-fill.",
                                    fontSize = 12.sp,
                                    color = Color.Gray
                                )
                            }
                        } else {
                            autofilledMeds.forEachIndexed { index, med ->
                                Card(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp),
                                    shape = RoundedCornerShape(10.dp),
                                    colors = CardDefaults.cardColors(containerColor = Color.White),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE2E8F0))
                                ) {
                                    Column(modifier = Modifier.padding(10.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(
                                                    Icons.Default.Medication,
                                                    contentDescription = null,
                                                    tint = Color(0xFF2563EB),
                                                    modifier = Modifier.size(20.dp)
                                                )
                                                Spacer(modifier = Modifier.width(8.dp))
                                                AccessibleText(
                                                    text = med.name,
                                                    fontSize = 14.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = Color(0xFF1E293B)
                                                )
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Surface(
                                                    shape = RoundedCornerShape(6.dp),
                                                    color = Color(0xFFEFF6FF)
                                                ) {
                                                    AccessibleText(
                                                        text = "${med.dosage} • ${med.form}",
                                                        fontSize = 11.sp,
                                                        fontWeight = FontWeight.SemiBold,
                                                        color = Color(0xFF1D4ED8),
                                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                    )
                                                }
                                            }

                                            Row {
                                                IconButton(
                                                    onClick = { editingMedIndex = index },
                                                    modifier = Modifier.size(28.dp)
                                                ) {
                                                    Icon(Icons.Default.Edit, contentDescription = "Edit Reminder", tint = Color(0xFF2563EB), modifier = Modifier.size(16.dp))
                                                }
                                                IconButton(
                                                    onClick = { autofilledMeds.removeAt(index) },
                                                    modifier = Modifier.size(28.dp)
                                                ) {
                                                    Icon(Icons.Default.Delete, contentDescription = "Remove", tint = Color(0xFFDC2626), modifier = Modifier.size(16.dp))
                                                }
                                            }
                                        }

                                        Spacer(modifier = Modifier.height(4.dp))
                                        AccessibleText(
                                            text = "Instructions: ${med.instructions}",
                                            fontSize = 12.sp,
                                            color = Color(0xFF475569)
                                        )

                                        Spacer(modifier = Modifier.height(6.dp))
                                        // Reminder Times Display
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Icon(Icons.Default.Alarm, contentDescription = null, tint = Color(0xFFD97706), modifier = Modifier.size(14.dp))
                                            AccessibleText(text = "Initial Alarms:", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF92400E))
                                            med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }.forEach { t ->
                                                Surface(
                                                    shape = RoundedCornerShape(12.dp),
                                                    color = Color(0xFFFEF3C7)
                                                ) {
                                                    AccessibleText(
                                                        text = "⏰ $t",
                                                        fontSize = 11.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color(0xFFB45309),
                                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                                    )
                                                }
                                            }
                                        }

                                        // Tapering Section
                                        if (med.hasTapering) {
                                            Spacer(modifier = Modifier.height(6.dp))
                                            Surface(
                                                shape = RoundedCornerShape(8.dp),
                                                color = Color(0xFFFFFBEB),
                                                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFDE68A)),
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                Column(modifier = Modifier.padding(8.dp)) {
                                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                                        Icon(Icons.Default.Schedule, contentDescription = null, tint = Color(0xFFB45309), modifier = Modifier.size(14.dp))
                                                        Spacer(modifier = Modifier.width(4.dp))
                                                        Text(
                                                            text = "📉 Tapers From: ${med.taperStartDate.ifBlank { com.example.util.DateUtils.getToday() }}",
                                                            fontSize = 11.sp,
                                                            fontWeight = FontWeight.Bold,
                                                            color = Color(0xFF92400E)
                                                        )
                                                    }
                                                    Text(
                                                        text = "• Tapered Dose: ${med.taperDosage.ifBlank { "1 Tablet" }} • Time: ${med.taperScheduledTimes.ifBlank { "08:00" }}",
                                                        fontSize = 11.sp,
                                                        fontWeight = FontWeight.SemiBold,
                                                        color = Color(0xFFB45309)
                                                    )
                                                    if (med.taperInstructions.isNotBlank()) {
                                                        Text(
                                                            text = "• Note: ${med.taperInstructions}",
                                                            fontSize = 11.sp,
                                                            color = Color(0xFF78350F)
                                                        )
                                                    }
                                                }
                                            }
                                        } else {
                                            Spacer(modifier = Modifier.height(4.dp))
                                            OutlinedButton(
                                                onClick = {
                                                    val today = com.example.util.DateUtils.getToday()
                                                    autofilledMeds[index] = med.copy(
                                                        hasTapering = true,
                                                        taperStartDate = today,
                                                        taperDosage = if (med.dosage.contains("2")) "1 Tablet" else "Reduced Dose",
                                                        taperTimesPerDay = 1,
                                                        taperScheduledTimes = "08:00",
                                                        taperInstructions = "Taper down dose from today ($today) as per prescription"
                                                    )
                                                },
                                                shape = RoundedCornerShape(8.dp),
                                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                                modifier = Modifier.testTag("btn_quick_taper_${index}")
                                            ) {
                                                Text("📉 Taper Down From Today (${com.example.util.DateUtils.getToday()})", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val finalDoctor = if (doctorName.isNotBlank()) doctorName.trim() else "Consulting Physician"
                        val finalClinic = if (clinic.isNotBlank()) clinic.trim() else "Healthcare Clinic"
                        val finalDisease = if (disease.isNotBlank()) disease.trim() else "General Prescription"
                        val finalImage = uploadedImageUri ?: simulatedImageUri

                        onApproveAndSavePrescription(
                            finalDoctor,
                            finalClinic,
                            finalDisease,
                            startDate.trim(),
                            endDate.trim().takeIf { it.isNotBlank() },
                            advice.trim(),
                            finalImage,
                            notes.trim(),
                            isFollowUp,
                            if (isFollowUp) parentPrescriptionId else null,
                            autofilledMeds.toList(),
                            selectedProfileId
                        )
                        showAddDialog = false
                    },
                    modifier = Modifier.testTag("btn_approve_prescription")
                ) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Save Prescription & Set Reminders")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showAddDialog = false }) { Text("Cancel") }
            }
        )

        // Inline dialog for editing a single medication reminder
        editingMedIndex?.let { idx ->
            if (idx in autofilledMeds.indices) {
                val med = autofilledMeds[idx]
                var editName by remember(idx) { mutableStateOf(med.name) }
                var editDosage by remember(idx) { mutableStateOf(med.dosage) }
                var editForm by remember(idx) { mutableStateOf(med.form) }
                var editInstructions by remember(idx) { mutableStateOf(med.instructions) }
                var editTimesList by remember(idx) {
                    val parsed = med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                    mutableStateOf(if (parsed.isEmpty()) listOf("08:00") else parsed)
                }
                var editHasTapering by remember(idx) { mutableStateOf(med.hasTapering) }
                var editTaperStartDate by remember(idx) { mutableStateOf(med.taperStartDate.ifBlank { com.example.util.DateUtils.getToday() }) }
                var editTaperDosage by remember(idx) { mutableStateOf(med.taperDosage.ifBlank { "1 Tablet" }) }
                var editTaperInstructions by remember(idx) { mutableStateOf(med.taperInstructions.ifBlank { "Taper down dose from today as per prescription" }) }
                var editTaperTimesList by remember(idx) {
                    val parsed = med.taperScheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                    mutableStateOf(if (parsed.isEmpty()) listOf("08:00") else parsed)
                }

                AlertDialog(
                    onDismissRequest = { editingMedIndex = null },
                    title = { AccessibleText("Edit Medication Reminder & Times", fontSize = 16.sp, fontWeight = FontWeight.Bold) },
                    text = {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.verticalScroll(rememberScrollState())
                        ) {
                            OutlinedTextField(
                                value = editName,
                                onValueChange = { editName = it },
                                label = { Text("Medicine Name") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth()
                            )
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = editDosage,
                                    onValueChange = { editDosage = it },
                                    label = { Text("Initial Dosage") },
                                    modifier = Modifier.weight(1f),
                                    singleLine = true
                                )
                                OutlinedTextField(
                                    value = editForm,
                                    onValueChange = { editForm = it },
                                    label = { Text("Form") },
                                    modifier = Modifier.weight(1f),
                                    singleLine = true
                                )
                            }
                            OutlinedTextField(
                                value = editInstructions,
                                onValueChange = { editInstructions = it },
                                label = { Text("Initial Instructions") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            TimeSlotEditor(
                                times = editTimesList,
                                onTimesChanged = { editTimesList = it },
                                label = "Initial Reminder Intake Times",
                                medicineName = editName,
                                dosage = editDosage,
                                instructions = editInstructions
                            )

                            // Tapering section
                            Spacer(modifier = Modifier.height(4.dp))
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(10.dp),
                                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFBEB)),
                                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFDE68A))
                            ) {
                                Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Checkbox(
                                            checked = editHasTapering,
                                            onCheckedChange = { editHasTapering = it }
                                        )
                                        Column {
                                            AccessibleText(
                                                text = "Enable Dose Tapering Schedule 📉",
                                                fontSize = 13.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = Color(0xFF92400E)
                                            )
                                            AccessibleText(
                                                text = "Automatically steps down dose & schedule starting from chosen date",
                                                fontSize = 11.sp,
                                                color = Color(0xFFB45309)
                                            )
                                        }
                                    }

                                    if (editHasTapering) {
                                        CalendarDatePickerField(
                                            value = editTaperStartDate,
                                            onValueChange = { editTaperStartDate = it },
                                            label = "Taper Start Date",
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                        OutlinedTextField(
                                            value = editTaperDosage,
                                            onValueChange = { editTaperDosage = it },
                                            label = { Text("Tapered Dosage") },
                                            placeholder = { Text("e.g. 1 Tablet, 8 mg") },
                                            singleLine = true,
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                        OutlinedTextField(
                                            value = editTaperInstructions,
                                            onValueChange = { editTaperInstructions = it },
                                            label = { Text("Tapered Instructions") },
                                            placeholder = { Text("e.g. After breakfast") },
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                        TimeSlotEditor(
                                            times = editTaperTimesList,
                                            onTimesChanged = { editTaperTimesList = it },
                                            label = "Tapered Intake Times",
                                            medicineName = editName,
                                            dosage = editTaperDosage,
                                            instructions = editTaperInstructions
                                        )
                                    }
                                }
                            }
                        }
                    },
                    confirmButton = {
                        Button(onClick = {
                            val formattedTimes = if (editTimesList.isEmpty()) "08:00" else editTimesList.joinToString(", ")
                            val formattedTaperTimes = if (editTaperTimesList.isEmpty()) "08:00" else editTaperTimesList.joinToString(", ")
                            autofilledMeds[idx] = AutofillMedInfo(
                                name = editName.trim().ifEmpty { med.name },
                                dosage = editDosage.trim().ifEmpty { med.dosage },
                                form = editForm.trim().ifEmpty { med.form },
                                instructions = editInstructions.trim().ifEmpty { med.instructions },
                                timesPerDay = editTimesList.size.coerceAtLeast(1),
                                scheduledTimes = formattedTimes,
                                hasTapering = editHasTapering,
                                taperStartDate = editTaperStartDate.trim(),
                                taperDosage = editTaperDosage.trim(),
                                taperTimesPerDay = editTaperTimesList.size.coerceAtLeast(1),
                                taperScheduledTimes = formattedTaperTimes,
                                taperInstructions = editTaperInstructions.trim(),
                                taperEndDate = med.taperEndDate
                            )
                            editingMedIndex = null
                        }) {
                            Text("Update")
                        }
                    },
                    dismissButton = {
                        OutlinedButton(onClick = { editingMedIndex = null }) { Text("Cancel") }
                    }
                )
            }
        }

        // Inline dialog for manually adding a medication reminder to this prescription
        if (showAddMedInlineDialog) {
            var newName by remember { mutableStateOf("") }
            var newDosage by remember { mutableStateOf("1 Tab") }
            var newForm by remember { mutableStateOf("Tablet") }
            var newInstructions by remember { mutableStateOf("After food") }
            var newTimesList by remember { mutableStateOf(listOf("08:00")) }

            AlertDialog(
                onDismissRequest = { showAddMedInlineDialog = false },
                title = { AccessibleText("Add Medication Reminder", fontSize = 16.sp, fontWeight = FontWeight.Bold) },
                text = {
                    Column(
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.verticalScroll(rememberScrollState())
                    ) {
                        OutlinedTextField(
                            value = newName,
                            onValueChange = { newName = it },
                            label = { Text("Medicine Name") },
                            placeholder = { Text("e.g. Metformin") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = newDosage,
                                onValueChange = { newDosage = it },
                                label = { Text("Dosage") },
                                modifier = Modifier.weight(1f),
                                singleLine = true
                            )
                            OutlinedTextField(
                                value = newForm,
                                onValueChange = { newForm = it },
                                label = { Text("Form") },
                                modifier = Modifier.weight(1f),
                                singleLine = true
                            )
                        }
                        OutlinedTextField(
                            value = newInstructions,
                            onValueChange = { newInstructions = it },
                            label = { Text("Instructions") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        TimeSlotEditor(
                            times = newTimesList,
                            onTimesChanged = { newTimesList = it },
                            label = "Reminder Intake Times",
                            medicineName = newName,
                            dosage = newDosage,
                            instructions = newInstructions
                        )
                    }
                },
                confirmButton = {
                    Button(onClick = {
                        if (newName.isNotBlank()) {
                            val formattedTimes = if (newTimesList.isEmpty()) "08:00" else newTimesList.joinToString(", ")
                            autofilledMeds.add(
                                AutofillMedInfo(
                                    name = newName.trim(),
                                    dosage = newDosage.trim().ifEmpty { "1 Dose" },
                                    form = newForm.trim().ifEmpty { "Tablet" },
                                    instructions = newInstructions.trim().ifEmpty { "After meals" },
                                    timesPerDay = newTimesList.size.coerceAtLeast(1),
                                    scheduledTimes = formattedTimes
                                )
                            )
                        }
                        showAddMedInlineDialog = false
                    }) {
                        Text("Add")
                    }
                },
                dismissButton = {
                    OutlinedButton(onClick = { showAddMedInlineDialog = false }) { Text("Cancel") }
                }
            )
        }
    }

    // Edit Prescription Dialog
    prescriptionToEdit?.let { pres ->
        val context = LocalContext.current
        var editDoctor by remember(pres.id) { mutableStateOf(pres.doctorName) }
        var editClinic by remember(pres.id) { mutableStateOf(pres.clinicOrHospital) }
        var editDisease by remember(pres.id) { mutableStateOf(pres.diseaseOrDiagnosis) }
        var editStart by remember(pres.id) { mutableStateOf(com.example.util.DateUtils.formatDisplayDate(pres.startDate)) }
        var editEnd by remember(pres.id) { mutableStateOf(com.example.util.DateUtils.formatDisplayDate(pres.endDate ?: "")) }
        var editAdvice by remember(pres.id) { mutableStateOf(pres.dischargeAdvice) }
        var editNotes by remember(pres.id) { mutableStateOf(pres.notes) }
        var editImageUri by remember(pres.id) { mutableStateOf(pres.imageUri) }

        val editPhotoPickerLauncher = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickVisualMedia()
        ) { uri ->
            if (uri != null) {
                editImageUri = ImageStorageHelper.saveImageToInternalStorage(context, uri, "prescription")
            }
        }

        AlertDialog(
            onDismissRequest = { prescriptionToEdit = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(
                    text = "Edit Prescription Details",
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
                    // Image preview & change button
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            AccessibleText(
                                text = "Prescription Photo",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF1D4ED8)
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            if (!editImageUri.isNullOrEmpty()) {
                                AsyncImage(
                                    model = editImageUri,
                                    contentDescription = "Prescription Photo",
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(130.dp)
                                        .clip(RoundedCornerShape(8.dp)),
                                    contentScale = ContentScale.Crop
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    onClick = {
                                        editPhotoPickerLauncher.launch(
                                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                        )
                                    },
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Icon(Icons.Default.PhotoCamera, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    AccessibleText(
                                        text = if (editImageUri.isNullOrEmpty()) "Upload Photo" else "Change Photo",
                                        fontSize = 12.sp,
                                        color = Color.White
                                    )
                                }
                                if (!editImageUri.isNullOrEmpty()) {
                                    OutlinedButton(
                                        onClick = { editImageUri = null },
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        AccessibleText(text = "Remove Photo", fontSize = 12.sp, color = Color(0xFFDC2626))
                                    }
                                }
                            }
                        }
                    }

                    OutlinedTextField(
                        value = editDoctor,
                        onValueChange = { editDoctor = it },
                        label = { Text("Doctor Name") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = editClinic,
                        onValueChange = { editClinic = it },
                        label = { Text("Clinic / Hospital") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = editDisease,
                        onValueChange = { editDisease = it },
                        label = { Text("Disease / Diagnosis") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    CalendarDatePickerField(
                        value = editStart,
                        onValueChange = { editStart = it },
                        label = "Start Date (Calendar)",
                        tag = "input_edit_pres_start_date",
                        modifier = Modifier.fillMaxWidth()
                    )
                    CalendarDatePickerField(
                        value = editEnd,
                        onValueChange = { editEnd = it },
                        label = "End Date (Calendar)",
                        placeholder = "Blank if ongoing",
                        tag = "input_edit_pres_end_date",
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = editAdvice,
                        onValueChange = { editAdvice = it },
                        label = { Text("Discharge & Lifestyle Advice") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = editNotes,
                        onValueChange = { editNotes = it },
                        label = { Text("Doctor's Notes") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onUpdatePrescription(
                            pres.copy(
                                doctorName = editDoctor.trim().ifEmpty { "Doctor" },
                                clinicOrHospital = editClinic.trim().ifEmpty { "Clinic" },
                                diseaseOrDiagnosis = editDisease.trim().ifEmpty { "Diagnosis" },
                                startDate = editStart.trim(),
                                endDate = editEnd.trim().takeIf { it.isNotBlank() },
                                dischargeAdvice = editAdvice.trim(),
                                notes = editNotes.trim(),
                                imageUri = editImageUri
                            )
                        )
                        prescriptionToEdit = null
                    }
                ) {
                    Text("Save Changes")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { prescriptionToEdit = null }) { Text("Cancel") }
            }
        )
    }

    // Inline Edit Medicine Dialog for Prescriptions screen
    medicineToEditInPrescription?.let { med ->
        var editName by remember(med.id) { mutableStateOf(med.name) }
        var editDosage by remember(med.id) { mutableStateOf(med.dosage) }
        var editForm by remember(med.id) { mutableStateOf(med.form) }
        var editInstructions by remember(med.id) { mutableStateOf(med.instructions) }
        var editTimesList by remember(med.id) {
            val parsed = med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            mutableStateOf(if (parsed.isEmpty()) listOf("08:00") else parsed)
        }
        var editProfileId by remember(med.id) { mutableStateOf(med.profileId) }

        AlertDialog(
            onDismissRequest = { medicineToEditInPrescription = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = { AccessibleText("Edit Medicine & Reminder Times", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    if (profiles.isNotEmpty()) {
                        AccessibleText(text = "Patient Profile:", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            profiles.forEach { profile ->
                                FilterChip(
                                    selected = editProfileId == profile.id,
                                    onClick = { editProfileId = profile.id },
                                    label = { Text("👤 ${profile.name}") },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                )
                            }
                        }
                    }

                    OutlinedTextField(
                        value = editName,
                        onValueChange = { editName = it },
                        label = { Text("Medicine Name") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = editDosage,
                            onValueChange = { editDosage = it },
                            label = { Text("Dosage") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = editForm,
                            onValueChange = { editForm = it },
                            label = { Text("Form") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                    }

                    OutlinedTextField(
                        value = editInstructions,
                        onValueChange = { editInstructions = it },
                        label = { Text("Instructions") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    TimeSlotEditor(
                        times = editTimesList,
                        onTimesChanged = { editTimesList = it },
                        label = "Reminder Times (Tap to set clock, add, or remove)",
                        medicineName = editName,
                        dosage = editDosage,
                        instructions = editInstructions
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val formattedTimes = if (editTimesList.isEmpty()) "08:00" else editTimesList.joinToString(", ")
                        val updated = med.copy(
                            name = editName.trim().ifEmpty { med.name },
                            dosage = editDosage.trim().ifEmpty { med.dosage },
                            form = editForm.trim().ifEmpty { med.form },
                            instructions = editInstructions.trim().ifEmpty { med.instructions },
                            scheduledTimes = formattedTimes,
                            timesPerDay = editTimesList.size.coerceAtLeast(1),
                            profileId = editProfileId
                        )
                        onUpdateMedicine(updated)
                        medicineToEditInPrescription = null
                    }
                ) {
                    Text("Save Changes")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { medicineToEditInPrescription = null }) { Text("Cancel") }
            }
        )
    }

    // Full screen image viewer dialog
    fullScreenImageUri?.let { uri ->
        AlertDialog(
            onDismissRequest = { fullScreenImageUri = null },
            confirmButton = {
                Button(onClick = { fullScreenImageUri = null }) { Text("Close") }
            },
            text = {
                AsyncImage(
                    model = uri,
                    contentDescription = "Prescription Full Size",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(300.dp)
                        .clip(RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Fit
                )
            }
        )
    }
}
