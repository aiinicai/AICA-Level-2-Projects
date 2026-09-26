package com.example.ui.screens.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PrivacyTip
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Shield
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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.window.DialogProperties
import com.example.data.model.PatientProfile
import com.example.ui.components.AccessibleText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun ProfileScreen(
    profiles: List<PatientProfile>,
    activeProfileId: Long?,
    onSelectProfile: (Long) -> Unit,
    onAddProfile: (name: String, age: Int, sex: String) -> Unit,
    onUpdateProfile: (PatientProfile) -> Unit,
    onDeleteProfile: (Long) -> Unit,
    onWipeAllData: () -> Unit
) {
    var showAddDialog by remember { mutableStateOf(false) }
    var profileToEdit by remember { mutableStateOf<PatientProfile?>(null) }
    var showWipeConfirm by remember { mutableStateOf(false) }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_add_profile")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Patient Profile")
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
                    text = "Patient Profiles",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                AccessibleText(
                    text = "Manage schedules and prescriptions for multiple family members.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            items(profiles, key = { it.id }) { profile ->
                val isActive = profile.id == activeProfileId || (activeProfileId == null && profile.isPrimary)

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(
                            width = if (isActive) 2.dp else 1.dp,
                            color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                            shape = RoundedCornerShape(18.dp)
                        )
                        .testTag("profile_card_${profile.id}"),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isActive) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)
                        else MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(46.dp)
                                        .clip(CircleShape)
                                        .background(MaterialTheme.colorScheme.primary),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Person,
                                        contentDescription = null,
                                        tint = Color.White,
                                        modifier = Modifier.size(28.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    AccessibleText(
                                        text = profile.name,
                                        fontSize = 19.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                    AccessibleText(
                                        text = "Age: ${profile.age} years • Sex: ${profile.sex}",
                                        fontSize = 14.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }

                            if (profile.isPrimary) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = MaterialTheme.colorScheme.primary
                                ) {
                                    AccessibleText(
                                        text = "PRIMARY",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.White,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Button(
                                onClick = { onSelectProfile(profile.id) },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isActive) Color(0xFF047857) else MaterialTheme.colorScheme.primary
                                ),
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier.testTag("btn_select_profile_${profile.id}")
                            ) {
                                if (isActive) {
                                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    AccessibleText(text = "Active Profile", color = Color.White, fontSize = 13.sp)
                                } else {
                                    AccessibleText(text = "Switch To Profile", color = Color.White, fontSize = 13.sp)
                                }
                            }

                            Row {
                                IconButton(onClick = { profileToEdit = profile }) {
                                    Icon(Icons.Default.Edit, contentDescription = "Edit Profile")
                                }
                                if (profiles.size > 1) {
                                    IconButton(onClick = { onDeleteProfile(profile.id) }) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete Profile", tint = Color(0xFFDC2626))
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // DPDP Act Compliance Card (placed below all listed profiles)
            item {
                Spacer(modifier = Modifier.height(6.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4)),
                    border = CardDefaults.outlinedCardBorder().copy(brush = androidx.compose.ui.graphics.SolidColor(Color(0xFF86EFAC)))
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Shield,
                                contentDescription = null,
                                tint = Color(0xFF15803D),
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            AccessibleText(
                                text = "DPDP Act (India) Privacy Guarantee",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF166534)
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        AccessibleText(
                            text = "• 100% Local On-Device Storage: No cloud uploads, telemetry, or third-party trackers.\n" +
                                    "• Data Minimization: Only Patient Name, Age & Sex collected.\n" +
                                    "• Right to Erasure: You have the legal right to erase all health data at any time.",
                            fontSize = 12.sp,
                            lineHeight = 18.sp,
                            color = Color(0xFF14532D)
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFE2E8F0)
                        ) {
                            AccessibleText(
                                text = "Testing Phase: No login required. Future Google Auth ready.",
                                fontSize = 11.sp,
                                color = Color(0xFF334155),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }

            // Legal DPDP Wipe all user data
            item {
                Spacer(modifier = Modifier.height(4.dp))
                OutlinedButton(
                    onClick = { showWipeConfirm = true },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("btn_wipe_all_data"),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFDC2626)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Delete, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    AccessibleText(
                        text = "DPDP Right to Erasure: Wipe All Data on Phone",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFFDC2626)
                    )
                }
            }
        }
    }

    // Add Profile Dialog
    if (showAddDialog) {
        var name by remember { mutableStateOf("") }
        var ageStr by remember { mutableStateOf("") }
        var sex by remember { mutableStateOf("Male") }

        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(text = "Add Patient Profile", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Patient Full Name") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("input_profile_name"),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = ageStr,
                        onValueChange = { ageStr = it.filter { c -> c.isDigit() } },
                        label = { Text("Age (in years)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("input_profile_age"),
                        singleLine = true
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf("Male", "Female", "Other").forEach { option ->
                            OutlinedButton(
                                onClick = { sex = option },
                                modifier = Modifier.weight(1f),
                                colors = ButtonDefaults.outlinedButtonColors(
                                    containerColor = if (sex == option) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                                )
                            ) {
                                Text(option, fontSize = 12.sp)
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val age = ageStr.toIntOrNull() ?: 60
                        if (name.isNotBlank()) {
                            onAddProfile(name, age, sex)
                            showAddDialog = false
                        }
                    },
                    modifier = Modifier.testTag("btn_save_profile")
                ) {
                    Text("Save Profile")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showAddDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Edit Profile Dialog
    profileToEdit?.let { profile ->
        var name by remember { mutableStateOf(profile.name) }
        var ageStr by remember { mutableStateOf(profile.age.toString()) }
        var sex by remember { mutableStateOf(profile.sex) }

        AlertDialog(
            onDismissRequest = { profileToEdit = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(text = "Edit Profile", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Patient Full Name") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = ageStr,
                        onValueChange = { ageStr = it.filter { c -> c.isDigit() } },
                        label = { Text("Age") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Column {
                        AccessibleText(
                            text = "Sex / Gender:",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            listOf("Male", "Female", "Other").forEach { option ->
                                OutlinedButton(
                                    onClick = { sex = option },
                                    modifier = Modifier
                                        .weight(1f)
                                        .testTag("btn_edit_sex_$option"),
                                    colors = ButtonDefaults.outlinedButtonColors(
                                        containerColor = if (sex.equals(option, ignoreCase = true))
                                            MaterialTheme.colorScheme.primaryContainer
                                        else Color.Transparent
                                    )
                                ) {
                                    Text(
                                        text = option,
                                        fontSize = 12.sp,
                                        fontWeight = if (sex.equals(option, ignoreCase = true)) FontWeight.Bold else FontWeight.Normal,
                                        color = if (sex.equals(option, ignoreCase = true))
                                            MaterialTheme.colorScheme.onPrimaryContainer
                                        else MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = {
                    onUpdateProfile(
                        profile.copy(
                            name = name.trim(),
                            age = ageStr.toIntOrNull() ?: profile.age,
                            sex = sex
                        )
                    )
                    profileToEdit = null
                }) {
                    Text("Update")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { profileToEdit = null }) { Text("Cancel") }
            }
        )
    }

    // Wipe confirmation dialog
    if (showWipeConfirm) {
        AlertDialog(
            onDismissRequest = { showWipeConfirm = false },
            title = {
                AccessibleText(
                    text = "Erase All Health Data?",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFDC2626)
                )
            },
            text = {
                AccessibleText(
                    text = "This will permanently delete all profiles, prescriptions, medicine schedules, lab reports, chemists, and emergency contacts from your phone's local storage. This action cannot be undone.",
                    fontSize = 14.sp
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        onWipeAllData()
                        showWipeConfirm = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626))
                ) {
                    Text("Yes, Wipe All Data", color = Color.White)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showWipeConfirm = false }) { Text("Cancel") }
            }
        )
    }
}
