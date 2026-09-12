package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Badge
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TeamMember
import com.example.data.model.UserRole
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun MemberFormDialog(
    memberToEdit: TeamMember? = null,
    onDismiss: () -> Unit,
    onSave: (name: String, role: String, userRole: UserRole, department: String, email: String, phone: String, colorHex: String, password: String) -> Unit
) {
    val isEditMode = memberToEdit != null

    var name by remember { mutableStateOf(memberToEdit?.name ?: "") }
    var role by remember { mutableStateOf(memberToEdit?.role ?: "") }
    var selectedUserRole by remember { mutableStateOf(memberToEdit?.userRole ?: UserRole.TEAM_MEMBER) }
    var department by remember { mutableStateOf(memberToEdit?.department ?: "Direct & Indirect Tax") }
    var email by remember { mutableStateOf(memberToEdit?.email ?: "") }
    var phone by remember { mutableStateOf(memberToEdit?.phone ?: "") }
    // Only relevant when creating: this becomes the new employee's initial Firebase Auth
    // password. Existing passwords live in Firebase Auth and cannot be read or set from here.
    var password by remember { mutableStateOf(if (isEditMode) "" else "office123") }
    var passwordVisible by remember { mutableStateOf(false) }
    var selectedColorHex by remember { mutableStateOf(memberToEdit?.avatarColorHex ?: "#1E40AF") }

    var roleDropdownExpanded by remember { mutableStateOf(false) }

    val presetColors = listOf(
        "#1E40AF", "#0D9488", "#D97706", "#7C3AED", "#059669", "#E11D48", "#475569", "#0284C7"
    )

    val departmentOptions = listOf(
        "Direct & Indirect Tax",
        "GST & Indirect Taxation",
        "Direct Tax & Transfer Pricing",
        "Audit & Assurance",
        "Corporate Advisory & ROC",
        "Compliance & Payroll",
        "Executive & Practice Leadership"
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("member_form_dialog"),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(
                            try {
                                Color(android.graphics.Color.parseColor(selectedColorHex))
                            } catch (_: Exception) {
                                MaterialTheme.colorScheme.primary
                            }
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = (name.ifEmpty { "U" }).take(1),
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        fontSize = 16.sp
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = if (isEditMode) "Edit Team Member Profile" else "Add New Team Member",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Configures user credentials, access role and department",
                        style = MaterialTheme.typography.bodySmall.copy(
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 11.sp
                        )
                    )
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Name
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Full Name *") },
                    placeholder = { Text("e.g. Ramesh Kumar") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("member_name_input"),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Badge, contentDescription = null) }
                )

                // Designation / Professional Role
                OutlinedTextField(
                    value = role,
                    onValueChange = { role = it },
                    label = { Text("Designation / Title *") },
                    placeholder = { Text("e.g. Senior Tax Consultant, Article Assistant") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("member_designation_input"),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Work, contentDescription = null) }
                )

                // User System Role (Admin, Manager, Team Member)
                ExposedDropdownMenuBox(
                    expanded = roleDropdownExpanded,
                    onExpandedChange = { roleDropdownExpanded = it }
                ) {
                    OutlinedTextField(
                        value = "${selectedUserRole.displayName} - ${selectedUserRole.name}",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("System Access Level & Role *") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = roleDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("member_role_dropdown")
                    )

                    ExposedDropdownMenu(
                        expanded = roleDropdownExpanded,
                        onDismissRequest = { roleDropdownExpanded = false }
                    ) {
                        UserRole.entries.forEach { userRoleOption ->
                            val roleColor = when (userRoleOption) {
                                UserRole.ADMIN -> RoseUrgent
                                UserRole.PARTNER -> SapphirePrimary
                                UserRole.MANAGER -> AmberTax
                                UserRole.TEAM_MEMBER -> EmeraldSuccess
                            }
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Surface(
                                                shape = RoundedCornerShape(4.dp),
                                                color = roleColor.copy(alpha = 0.15f)
                                            ) {
                                                Text(
                                                    text = userRoleOption.displayName,
                                                    fontWeight = FontWeight.Bold,
                                                    color = roleColor,
                                                    fontSize = 11.sp,
                                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                )
                                            }
                                        }
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(
                                            text = userRoleOption.description,
                                            fontSize = 10.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                },
                                onClick = {
                                    selectedUserRole = userRoleOption
                                    roleDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Department Options
                Text(
                    text = "Department",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    departmentOptions.forEach { dept ->
                        val isSelected = department == dept
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier.clickable { department = dept }
                        ) {
                            Text(
                                text = dept,
                                style = MaterialTheme.typography.bodySmall.copy(
                                    fontSize = 11.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                                ),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }

                // Email & Phone
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        label = { Text("Work Email (Login) *") },
                        placeholder = { Text("name@office.com") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        leadingIcon = { Icon(Icons.Default.Email, contentDescription = null, modifier = Modifier.size(16.dp)) }
                    )
                    OutlinedTextField(
                        value = phone,
                        onValueChange = { phone = it },
                        label = { Text("Mobile Phone") },
                        placeholder = { Text("+91 98765...") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(16.dp)) }
                    )
                }

                // Initial sign-in password — only when creating the account. An existing
                // member's password lives in Firebase Auth and is changed by password reset,
                // so there is nothing meaningful to show or set here when editing.
                if (!isEditMode) {
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("Initial Login Password *") },
                        placeholder = { Text("Default: office123") },
                        supportingText = { Text("Share this with them and ask them to change it after first sign-in.", fontSize = 10.sp) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        visualTransformation = if (passwordVisible) androidx.compose.ui.text.input.VisualTransformation.None else androidx.compose.ui.text.input.PasswordVisualTransformation(),
                        leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(16.dp)) },
                        trailingIcon = {
                            IconButton(onClick = { passwordVisible = !passwordVisible }) {
                                Icon(
                                    imageVector = if (passwordVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                    contentDescription = if (passwordVisible) "Hide password" else "Show password",
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    )
                }

                // Avatar Color Palette
                Text(
                    text = "Avatar Badge Color",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    presetColors.forEach { colorHex ->
                        val isSelected = selectedColorHex.equals(colorHex, ignoreCase = true)
                        val color = try {
                            Color(android.graphics.Color.parseColor(colorHex))
                        } catch (_: Exception) {
                            MaterialTheme.colorScheme.primary
                        }

                        Box(
                            modifier = Modifier
                                .size(28.dp)
                                .clip(CircleShape)
                                .background(color)
                                .border(
                                    width = if (isSelected) 2.5.dp else 0.dp,
                                    color = if (isSelected) MaterialTheme.colorScheme.onSurface else Color.Transparent,
                                    shape = CircleShape
                                )
                                .clickable { selectedColorHex = colorHex },
                            contentAlignment = Alignment.Center
                        ) {
                            if (isSelected) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = "Selected",
                                    tint = Color.White,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && role.isNotBlank()) {
                        onSave(
                            name.trim(),
                            role.trim(),
                            selectedUserRole,
                            department,
                            email.trim(),
                            phone.trim(),
                            selectedColorHex,
                            // Blank in edit mode means "keep current password"; the caller
                            // resolves that. New members fall back to the shared default.
                            if (isEditMode) password.trim() else password.trim().ifEmpty { "office123" }
                        )
                    }
                },
                enabled = name.isNotBlank() && role.isNotBlank(),
                modifier = Modifier.testTag("save_member_btn")
            ) {
                Text(if (isEditMode) "Save Changes" else "Onboard User")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
