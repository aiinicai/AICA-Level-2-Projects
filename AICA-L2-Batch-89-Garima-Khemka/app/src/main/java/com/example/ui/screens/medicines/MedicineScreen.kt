package com.example.ui.screens.medicines

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
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
import androidx.compose.runtime.mutableIntStateOf
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.service.PrescriptionReaderService
import com.example.ui.components.AccessibleText
import com.example.ui.components.TimeSlotEditor
import com.example.ui.viewmodel.AutofillMedInfo
import com.example.util.ImageStorageHelper
import kotlinx.coroutines.launch

@Composable
fun MedicineScreen(
    medicines: List<Medicine>,
    profiles: List<PatientProfile> = emptyList(),
    activeProfileId: Long? = null,
    onAddMedicine: (
        name: String,
        dosage: String,
        form: String,
        instructions: String,
        timesPerDay: Int,
        scheduledTimes: String,
        stockQuantity: Int,
        lowStockDays: Int,
        diseaseName: String,
        imageUri: String?,
        targetProfileId: Long?
    ) -> Unit,
    onUpdateMedicine: (Medicine) -> Unit,
    onDeleteMedicine: (Long) -> Unit,
    onUpdateStock: (medicineId: Long, newStock: Int) -> Unit,
    onTaperMedicine: (Long) -> Unit = {}
) {
    var showAddDialog by remember { mutableStateOf(false) }
    var medicineToEdit by remember { mutableStateOf<Medicine?>(null) }
    var medicineForStockEdit by remember { mutableStateOf<Medicine?>(null) }

    // Profile-wise filter state (Default to activeProfileId or null for All)
    var selectedProfileFilterId by remember(activeProfileId) { mutableStateOf<Long?>(activeProfileId) }

    // Filter medicines according to selected profile filter
    val displayedMedicines = if (selectedProfileFilterId == null) {
        medicines
    } else {
        medicines.filter { it.profileId == selectedProfileFilterId }
    }

    val lowStockCount = displayedMedicines.count { it.stockQuantity <= it.lowStockThresholdDays }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_add_medicine")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add New Medicine")
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
                    text = "Medicine Inventory",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                AccessibleText(
                    text = "Manage stocks, reminder alarm times, and family member medication schedules.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Profile-Wise Filter Section
            if (profiles.isNotEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)),
                        shape = RoundedCornerShape(14.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Person, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    AccessibleText(
                                        text = "Filter by Family Profile:",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                if (selectedProfileFilterId != null) {
                                    Text(
                                        text = "Show All",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.primary,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.clickable { selectedProfileFilterId = null }
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                FilterChip(
                                    selected = selectedProfileFilterId == null,
                                    onClick = { selectedProfileFilterId = null },
                                    label = { Text("👥 All (${medicines.size})") },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                )

                                profiles.forEach { profile ->
                                    val count = medicines.count { it.profileId == profile.id }
                                    FilterChip(
                                        selected = selectedProfileFilterId == profile.id,
                                        onClick = {
                                            selectedProfileFilterId = if (selectedProfileFilterId == profile.id) null else profile.id
                                        },
                                        label = { Text("👤 ${profile.name} ($count)") },
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
            }

            // Low Stock Overview Banner
            if (lowStockCount > 0) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFFEE2E2)),
                        border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(Color(0xFFF87171))),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = null,
                                tint = Color(0xFFDC2626),
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                AccessibleText(
                                    text = "LOW STOCK ALERT: $lowStockCount Medicine(s) need refilling!",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF991B1B)
                                )
                                AccessibleText(
                                    text = "Highlighted in red below because stock is under 3 days.",
                                    fontSize = 12.sp,
                                    color = Color(0xFFB91C1C)
                                )
                            }
                        }
                    }
                }
            }

            // Empty state if filtered medicines is empty
            if (displayedMedicines.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Default.Medication, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(48.dp))
                            Spacer(modifier = Modifier.height(10.dp))
                            AccessibleText(
                                text = if (selectedProfileFilterId != null) {
                                    val profName = profiles.firstOrNull { it.id == selectedProfileFilterId }?.name ?: "this profile"
                                    "No medicines in inventory for $profName."
                                } else {
                                    "No medicines added to inventory yet."
                                },
                                fontSize = 15.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "Tap '+' below to add medicines or scan a prescription.",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            } else {
                items(displayedMedicines, key = { it.id }) { med ->
                    val isLowStock = med.stockQuantity <= med.lowStockThresholdDays
                    val profileOwner = profiles.firstOrNull { it.id == med.profileId }

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(
                                width = if (isLowStock) 2.dp else 1.dp,
                                color = if (isLowStock) Color(0xFFDC2626) else MaterialTheme.colorScheme.outlineVariant,
                                shape = RoundedCornerShape(18.dp)
                            )
                            .testTag("medicine_card_${med.id}"),
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isLowStock) Color(0xFFFFF1F2) else MaterialTheme.colorScheme.surface
                        ),
                        elevation = CardDefaults.cardElevation(2.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            // Profile Badge if available
                            if (profileOwner != null) {
                                Surface(
                                    shape = RoundedCornerShape(6.dp),
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
                                            text = "Profile: ${profileOwner.name} (${profileOwner.age}y)",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFF1D4ED8)
                                        )
                                    }
                                }
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    // Medicine Photo or Icon
                                    if (!med.imageUri.isNullOrEmpty()) {
                                        AsyncImage(
                                            model = med.imageUri,
                                            contentDescription = "Medicine Photo",
                                            modifier = Modifier
                                                .size(54.dp)
                                                .clip(RoundedCornerShape(12.dp))
                                                .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                                            contentScale = ContentScale.Crop
                                        )
                                        Spacer(modifier = Modifier.width(12.dp))
                                    } else {
                                        Box(
                                            modifier = Modifier
                                                .size(50.dp)
                                                .clip(RoundedCornerShape(12.dp))
                                                .background(
                                                    if (isLowStock) Color(0xFFFECDD3) else MaterialTheme.colorScheme.primaryContainer
                                                ),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.Medication,
                                                contentDescription = null,
                                                tint = if (isLowStock) Color(0xFFDC2626) else MaterialTheme.colorScheme.primary,
                                                modifier = Modifier.size(30.dp)
                                            )
                                        }
                                        Spacer(modifier = Modifier.width(12.dp))
                                    }

                                    Column {
                                        AccessibleText(
                                            text = med.name,
                                            fontSize = 18.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (isLowStock) Color(0xFF991B1B) else MaterialTheme.colorScheme.onSurface
                                        )
                                        AccessibleText(
                                            text = "${med.dosage} • ${med.form}",
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        if (med.diseaseName.isNotBlank()) {
                                            AccessibleText(
                                                text = "For: ${med.diseaseName}",
                                                fontSize = 12.sp,
                                                color = MaterialTheme.colorScheme.tertiary
                                            )
                                        }
                                    }
                                }

                                Row {
                                    IconButton(
                                        onClick = { medicineToEdit = med },
                                        modifier = Modifier.testTag("btn_edit_medicine_${med.id}")
                                    ) {
                                        Icon(Icons.Default.Edit, contentDescription = "Edit Medicine & Times", tint = MaterialTheme.colorScheme.primary)
                                    }
                                    IconButton(onClick = { onDeleteMedicine(med.id) }) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFDC2626))
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            // Interactive Schedule & Times
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        AccessibleText(
                                            text = "⏰ ${med.timesPerDay} times daily",
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Text(
                                            text = "Tap to edit times ✏️",
                                            fontSize = 11.sp,
                                            color = MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.SemiBold,
                                            modifier = Modifier.clickable { medicineToEdit = med }
                                        )
                                    }

                                    Spacer(modifier = Modifier.height(6.dp))

                                    // Display times as interactive pills
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .horizontalScroll(rememberScrollState()),
                                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        val timeList = med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                                        if (timeList.isEmpty()) {
                                            Text("No scheduled times", fontSize = 12.sp, color = Color.Gray)
                                        } else {
                                            timeList.forEach { timeStr ->
                                                Surface(
                                                    shape = RoundedCornerShape(14.dp),
                                                    color = Color(0xFFEFF6FF),
                                                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)),
                                                    modifier = Modifier.clickable { medicineToEdit = med }
                                                ) {
                                                    Row(
                                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                                                        verticalAlignment = Alignment.CenterVertically
                                                    ) {
                                                        Text("⏰ $timeStr", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1D4ED8))
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(6.dp))
                                    AccessibleText(
                                        text = "📋 Instructions: ${med.instructions}",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )

                                    if (med.hasTapering) {
                                        Spacer(modifier = Modifier.height(8.dp))
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
                                                        text = "📉 Tapering Active: ${med.taperDosage ?: "1 Tablet"} from ${med.taperStartDate ?: "Today"}",
                                                        fontSize = 11.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color(0xFF92400E)
                                                    )
                                                }
                                                if (!med.taperInstructions.isNullOrBlank()) {
                                                    Text(text = "• ${med.taperInstructions}", fontSize = 11.sp, color = Color(0xFF78350F))
                                                }
                                            }
                                        }
                                    } else {
                                        Spacer(modifier = Modifier.height(6.dp))
                                        OutlinedButton(
                                            onClick = { onTaperMedicine(med.id) },
                                            shape = RoundedCornerShape(8.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                            modifier = Modifier.testTag("btn_taper_med_${med.id}")
                                        ) {
                                            Text("📉 Taper Down Dose From Today (${com.example.util.DateUtils.getToday()})", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(12.dp))

                            // Stock Count & Adjustments
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        AccessibleText(
                                            text = "Stock Count: ",
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.Medium
                                        )
                                        AccessibleText(
                                            text = "${med.stockQuantity} pills",
                                            fontSize = 18.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (isLowStock) Color(0xFFDC2626) else Color(0xFF047857)
                                        )
                                    }
                                    if (isLowStock) {
                                        AccessibleText(
                                            text = "⚠️ Less than 3 days left!",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFFDC2626)
                                        )
                                    }
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    IconButton(
                                        onClick = { onUpdateStock(med.id, (med.stockQuantity - 1).coerceAtLeast(0)) },
                                        modifier = Modifier.size(36.dp)
                                    ) {
                                        Icon(Icons.Default.Remove, contentDescription = "Minus 1", modifier = Modifier.size(18.dp))
                                    }

                                    Surface(
                                        modifier = Modifier.clickable { medicineForStockEdit = med },
                                        shape = RoundedCornerShape(8.dp),
                                        color = MaterialTheme.colorScheme.primaryContainer
                                    ) {
                                        AccessibleText(
                                            text = "Edit Stock",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)
                                        )
                                    }

                                    IconButton(
                                        onClick = { onUpdateStock(med.id, med.stockQuantity + 10) },
                                        modifier = Modifier.size(36.dp)
                                    ) {
                                        Icon(Icons.Default.Add, contentDescription = "Add 10", modifier = Modifier.size(18.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Comprehensive Edit Medicine Dialog (fixes "unable to edit time")
    medicineToEdit?.let { med ->
        var editName by remember(med) { mutableStateOf(med.name) }
        var editDosage by remember(med) { mutableStateOf(med.dosage) }
        var editForm by remember(med) { mutableStateOf(med.form) }
        var editInstructions by remember(med) { mutableStateOf(med.instructions) }
        var editDisease by remember(med) { mutableStateOf(med.diseaseName) }
        var editStockStr by remember(med) { mutableStateOf(med.stockQuantity.toString()) }
        var editLowDaysStr by remember(med) { mutableStateOf(med.lowStockThresholdDays.toString()) }
        var editProfileId by remember(med) { mutableStateOf(med.profileId) }

        // Scheduled times list managed cleanly with TimeSlotEditor
        var editTimesList by remember(med) {
            val initial = med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            mutableStateOf(if (initial.isEmpty()) listOf("08:00") else initial)
        }

        AlertDialog(
            onDismissRequest = { medicineToEdit = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Edit, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.width(8.dp))
                    AccessibleText(
                        text = "Edit Medicine & Reminder Schedule",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Profile Selection
                    if (profiles.isNotEmpty()) {
                        Column {
                            AccessibleText(
                                text = "👤 Patient / Family Profile:",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF334155)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                profiles.forEach { p ->
                                    FilterChip(
                                        selected = editProfileId == p.id,
                                        onClick = { editProfileId = p.id },
                                        label = { Text("👤 ${p.name}") },
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                        )
                                    )
                                }
                            }
                        }
                    }

                    // Medicine Name
                    OutlinedTextField(
                        value = editName,
                        onValueChange = { editName = it },
                        label = { Text("Medicine Name") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    // Dosage & Form
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = editDosage,
                            onValueChange = { editDosage = it },
                            label = { Text("Dosage (e.g. 500mg)") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = editForm,
                            onValueChange = { editForm = it },
                            label = { Text("Form (e.g. Tablet)") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                    }

                    // Interactive Time Slot Editor
                    TimeSlotEditor(
                        times = editTimesList,
                        onTimesChanged = { editTimesList = it },
                        label = "Reminder Alarms & Intake Times",
                        medicineName = editName,
                        dosage = editDosage,
                        instructions = editInstructions,
                        timesPerDay = med.timesPerDay
                    )

                    // Instructions
                    OutlinedTextField(
                        value = editInstructions,
                        onValueChange = { editInstructions = it },
                        label = { Text("Instructions (e.g. After food with water)") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Diagnosis / Disease
                    OutlinedTextField(
                        value = editDisease,
                        onValueChange = { editDisease = it },
                        label = { Text("Disease / Condition (e.g. Hypertension)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    // Stock Pill Count & Low Stock Threshold
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = editStockStr,
                            onValueChange = { editStockStr = it.filter { c -> c.isDigit() } },
                            label = { Text("Pill Stock Count") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = editLowDaysStr,
                            onValueChange = { editLowDaysStr = it.filter { c -> c.isDigit() } },
                            label = { Text("Low Alert (Days)") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val timesFormatted = if (editTimesList.isEmpty()) "08:00" else editTimesList.joinToString(", ")
                        val newTimesPerDay = editTimesList.size.coerceAtLeast(1)
                        val newStock = editStockStr.toIntOrNull() ?: med.stockQuantity
                        val newLowThreshold = editLowDaysStr.toIntOrNull() ?: med.lowStockThresholdDays

                        onUpdateMedicine(
                            med.copy(
                                name = editName.trim().ifEmpty { med.name },
                                dosage = editDosage.trim().ifEmpty { med.dosage },
                                form = editForm.trim().ifEmpty { med.form },
                                instructions = editInstructions.trim().ifEmpty { med.instructions },
                                timesPerDay = newTimesPerDay,
                                scheduledTimes = timesFormatted,
                                stockQuantity = newStock,
                                lowStockThresholdDays = newLowThreshold,
                                diseaseName = editDisease.trim(),
                                profileId = editProfileId
                            )
                        )
                        medicineToEdit = null
                    }
                ) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Save Changes")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { medicineToEdit = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Add Medicine Dialog
    if (showAddDialog) {
        val context = LocalContext.current
        val coroutineScope = rememberCoroutineScope()
        var name by remember { mutableStateOf("") }
        var dosage by remember { mutableStateOf("") }
        var form by remember { mutableStateOf("Tablet") }
        var instructions by remember { mutableStateOf("Take after meals with water") }
        var timesList by remember { mutableStateOf(listOf("08:00")) }
        var stockStr by remember { mutableStateOf("15") }
        var disease by remember { mutableStateOf("") }
        var simulatedMedImageUri by remember { mutableStateOf<String?>(null) }
        var isReadingRx by remember { mutableStateOf(false) }
        var rxStatusMessage by remember { mutableStateOf<String?>(null) }
        var detectedMeds by remember { mutableStateOf<List<AutofillMedInfo>>(emptyList()) }
        var selectedProfileId by remember { mutableStateOf(selectedProfileFilterId ?: activeProfileId ?: profiles.firstOrNull()?.id ?: 1L) }

        val applyMedicationInfo: (AutofillMedInfo, String?) -> Unit = { med, condition ->
            name = med.name
            dosage = med.dosage
            form = med.form
            instructions = med.instructions
            val times = med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            timesList = if (times.isEmpty()) listOf("08:00") else times
            if (!condition.isNullOrBlank()) {
                disease = condition
            }
        }

        // Photo picker to scan a prescription image and autofill medicine details
        val prescriptionPhotoPicker = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.PickVisualMedia()
        ) { uri ->
            if (uri != null) {
                val saved = ImageStorageHelper.saveImageToInternalStorage(context, uri, "prescription")
                simulatedMedImageUri = saved
                isReadingRx = true
                rxStatusMessage = "Reading prescription with Gemini AI..."

                coroutineScope.launch {
                    val extracted = PrescriptionReaderService.readPrescriptionImage(context, Uri.parse(saved))
                    isReadingRx = false
                    detectedMeds = extracted.medicines
                    rxStatusMessage = extracted.statusMessage
                    if (extracted.medicines.isNotEmpty()) {
                        applyMedicationInfo(extracted.medicines.first(), extracted.diseaseOrDiagnosis)
                    }
                }
            }
        }

        // Quick sample loader
        val loadPresetSample: (String) -> Unit = { sampleType ->
            isReadingRx = true
            rxStatusMessage = "Loading preset prescription..."
            coroutineScope.launch {
                val extracted = PrescriptionReaderService.fallbackSmartExtraction(false, sampleType)
                isReadingRx = false
                detectedMeds = extracted.medicines
                rxStatusMessage = extracted.statusMessage
                if (extracted.medicines.isNotEmpty()) {
                    applyMedicationInfo(extracted.medicines.first(), extracted.diseaseOrDiagnosis)
                }
            }
        }

        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = { AccessibleText(text = "Add Medicine to Inventory", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Profile Selection
                    if (profiles.isNotEmpty()) {
                        Column {
                            AccessibleText(
                                text = "👤 Add for Patient Profile:",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF334155)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                profiles.forEach { p ->
                                    FilterChip(
                                        selected = selectedProfileId == p.id,
                                        onClick = { selectedProfileId = p.id },
                                        label = { Text("👤 ${p.name}") },
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                        )
                                    )
                                }
                            }
                        }
                    }

                    // Autofill with Prescription Card
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = Color(0xFF2563EB), modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                AccessibleText(
                                    text = "Scan Prescription to Auto-Fill",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1D4ED8)
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            AccessibleText(
                                text = "Upload a photo of a doctor's prescription to automatically fill medicine name, dosage, and reminder times.",
                                fontSize = 11.sp,
                                color = Color(0xFF1E40AF)
                            )
                            Spacer(modifier = Modifier.height(8.dp))

                            Button(
                                onClick = {
                                    prescriptionPhotoPicker.launch(
                                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                    )
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Icon(Icons.Default.AddPhotoAlternate, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                AccessibleText(text = "Upload Prescription Photo", fontSize = 12.sp, color = Color.White, fontWeight = FontWeight.Bold)
                            }

                            Spacer(modifier = Modifier.height(6.dp))
                            AccessibleText(text = "Or try clinical sample presets:", fontSize = 11.sp, color = Color(0xFF4B5563))
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                FilterChip(
                                    selected = false,
                                    onClick = { loadPresetSample("TAPER") },
                                    label = { Text("📉 Tapering Rx (17th Sept)", fontSize = 10.sp, fontWeight = FontWeight.Bold) },
                                    colors = FilterChipDefaults.filterChipColors(
                                        containerColor = Color(0xFFFEF3C7),
                                        labelColor = Color(0xFF92400E)
                                    )
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadPresetSample("CARDIO") },
                                    label = { Text("🫀 Cardio Rx", fontSize = 10.sp) }
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadPresetSample("DIABETES") },
                                    label = { Text("🩸 Diabetes Rx", fontSize = 10.sp) }
                                )
                                FilterChip(
                                    selected = false,
                                    onClick = { loadPresetSample("INFECTION") },
                                    label = { Text("💊 Infection Rx", fontSize = 10.sp) }
                                )
                            }
                        }
                    }

                    if (isReadingRx) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF3C7)),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp, color = Color(0xFFD97706))
                                Spacer(modifier = Modifier.width(10.dp))
                                AccessibleText(text = rxStatusMessage ?: "Reading prescription...", fontSize = 12.sp, color = Color(0xFF92400E), fontWeight = FontWeight.SemiBold)
                            }
                        }
                    } else if (rxStatusMessage != null) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFECFDF5),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF059669), modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                AccessibleText(text = rxStatusMessage ?: "", fontSize = 11.sp, color = Color(0xFF065F46), fontWeight = FontWeight.SemiBold)
                            }
                        }
                    }

                    if (detectedMeds.size > 1) {
                        AccessibleText(text = "Detected medicines from Rx (tap to switch):", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            detectedMeds.forEach { dMed ->
                                FilterChip(
                                    selected = name == dMed.name,
                                    onClick = { applyMedicationInfo(dMed, disease) },
                                    label = { Text("${dMed.name} (${dMed.dosage})", fontSize = 11.sp) }
                                )
                            }
                        }
                    }

                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Medicine Name (e.g. Telmisartan 40mg)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = dosage,
                            onValueChange = { dosage = it },
                            label = { Text("Dosage (e.g. 1 Tablet)") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = stockStr,
                            onValueChange = { stockStr = it.filter { c -> c.isDigit() } },
                            label = { Text("Stock Count") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                    }

                    // Interactive Time Slot Editor
                    TimeSlotEditor(
                        times = timesList,
                        onTimesChanged = { timesList = it },
                        label = "Reminder Alarms & Intake Times",
                        medicineName = name,
                        dosage = dosage,
                        instructions = instructions,
                        timesPerDay = timesList.size
                    )

                    OutlinedTextField(
                        value = instructions,
                        onValueChange = { instructions = it },
                        label = { Text("Instructions (e.g. Before/After meals)") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = disease,
                        onValueChange = { disease = it },
                        label = { Text("For Condition (e.g. Blood Pressure)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    if (simulatedMedImageUri != null) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF16A34A), modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            AccessibleText(text = "Prescription Photo Attached", fontSize = 12.sp, color = Color(0xFF16A34A), fontWeight = FontWeight.Bold)
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (name.isNotBlank()) {
                            val stock = stockStr.toIntOrNull() ?: 10
                            val scheduledTimesStr = if (timesList.isEmpty()) "08:00" else timesList.joinToString(", ")
                            onAddMedicine(
                                name.trim(),
                                dosage.trim().ifEmpty { "1 Tablet" },
                                form,
                                instructions.trim(),
                                timesList.size.coerceAtLeast(1),
                                scheduledTimesStr,
                                stock,
                                3,
                                disease.trim(),
                                simulatedMedImageUri,
                                selectedProfileId
                            )
                            showAddDialog = false
                        }
                    },
                    modifier = Modifier.testTag("btn_save_medicine")
                ) {
                    Text("Save Medicine")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showAddDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Edit Medicine Stock Dialog
    medicineForStockEdit?.let { med ->
        var countInput by remember { mutableStateOf(med.stockQuantity.toString()) }
        AlertDialog(
            onDismissRequest = { medicineForStockEdit = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = { AccessibleText(text = "Update Stock for ${med.name}", fontSize = 17.sp, fontWeight = FontWeight.Bold) },
            text = {
                OutlinedTextField(
                    value = countInput,
                    onValueChange = { countInput = it.filter { c -> c.isDigit() } },
                    label = { Text("New Stock Pill Count") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding(),
                    singleLine = true
                )
            },
            confirmButton = {
                Button(onClick = {
                    val newCount = countInput.toIntOrNull() ?: med.stockQuantity
                    onUpdateStock(med.id, newCount)
                    medicineForStockEdit = null
                }) {
                    Text("Update Count")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { medicineForStockEdit = null }) { Text("Cancel") }
            }
        )
    }
}
