package com.example.ui.screens.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AirplanemodeActive
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.AlarmOff
import androidx.compose.material.icons.filled.ColorLens
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.FormatSize
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Vibration
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.AppSettingsEntity
import com.example.ui.components.AccessibleText

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: AppSettingsEntity?,
    onUpdateTheme: (String) -> Unit,
    onUpdateFontScale: (String) -> Unit,
    onToggleHighContrast: (Boolean) -> Unit,
    onToggleLockScreenNotification: (Boolean) -> Unit,
    onUpdateAlarmType: (String) -> Unit,
    onToggleVibrate: (Boolean) -> Unit,
    onToggleAirplaneRemind: (Boolean) -> Unit,
    onToggleDeactivateReminders: (Boolean, String?, String?) -> Unit,
    onTriggerTestAlarm: () -> Unit,
    onWipeData: () -> Unit
) {
    val currentSettings = settings ?: AppSettingsEntity()
    var showDeactivateDialog by remember { mutableStateOf(false) }
    var showWipeConfirm by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 14.dp),
        contentPadding = PaddingValues(bottom = 80.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(4.dp))
            AccessibleText(
                text = "App Settings",
                fontSize = 22.sp,
                fontWeight = FontWeight.ExtraBold
            )
            AccessibleText(
                text = "Customize theme, senior accessibility fonts, alarm audio, and notifications.",
                fontSize = 13.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Test Alarm Trigger Quick Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        AccessibleText(
                            text = "Test Reminder Alarm",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        AccessibleText(
                            text = "Fires a real alarm in 2 seconds to test sound, lockscreen, and vibration.",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Button(
                        onClick = onTriggerTestAlarm,
                        modifier = Modifier.testTag("btn_trigger_test_alarm"),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(Icons.Default.NotificationsActive, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(text = "Test Now", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Section 1: Appearance & Accessibility Fonts
        item {
            SettingsSectionHeader(title = "Appearance & Eyesight Accessibility", icon = Icons.Default.FormatSize)

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    // Theme Choice (Rule 9a: Option to choose theme light or dark)
                    AccessibleText(text = "Theme Preference:", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf("SYSTEM" to "System", "LIGHT" to "Light", "DARK" to "Dark").forEach { (code, label) ->
                            FilterChip(
                                selected = currentSettings.themeMode == code,
                                onClick = { onUpdateTheme(code) },
                                label = { Text(label) },
                                modifier = Modifier.weight(1f).testTag("theme_chip_${code.lowercase()}")
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Font Size (Rule 9b: Font size)
                    AccessibleText(text = "Elderly Font Size:", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf("STANDARD" to "Normal (100%)", "LARGE" to "Large (115%)", "EXTRA_LARGE" to "XL (130%)").forEach { (code, label) ->
                            FilterChip(
                                selected = currentSettings.fontScale == code,
                                onClick = { onUpdateFontScale(code) },
                                label = { Text(label) },
                                modifier = Modifier.weight(1f).testTag("font_chip_${code.lowercase()}")
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // High Contrast Accessibility for Color-blindness
                    SettingsToggleRow(
                        title = "High Contrast Mode",
                        subtitle = "High-contrast colors & black background for visually impaired & color-blind users",
                        checked = currentSettings.highContrast,
                        onCheckedChange = onToggleHighContrast,
                        tag = "toggle_high_contrast"
                    )
                }
            }
        }

        // Section 2: Notifications & Lock Screen
        item {
            SettingsSectionHeader(title = "Alarms & Lock Screen Behavior", icon = Icons.Default.Alarm)

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    // Allow Notification seen on locked screen (Rule 9c: default yes)
                    SettingsToggleRow(
                        title = "Show on Locked Screen",
                        subtitle = "Display full medicine reminder and dose options on the lock screen (Default: Yes)",
                        checked = currentSettings.allowLockScreenNotification,
                        onCheckedChange = onToggleLockScreenNotification,
                        tag = "toggle_lock_screen"
                    )

                    Divider(modifier = Modifier.padding(vertical = 10.dp))

                    // Alarm Type (Rule 9d: Alarm type use system alarms available)
                    AccessibleText(text = "Alarm Sound Type:", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("SYSTEM_ALARM" to "System Alarm", "CHIME" to "Gentle Chime", "MEDICAL_BEEP" to "Medical Beep").forEach { (code, label) ->
                            FilterChip(
                                selected = currentSettings.alarmSoundType == code,
                                onClick = { onUpdateAlarmType(code) },
                                label = { Text(label, fontSize = 11.sp) },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }

                    Divider(modifier = Modifier.padding(vertical = 10.dp))

                    // Option to Vibrate instead of sound (Rule 9e)
                    SettingsToggleRow(
                        title = "Vibrate instead of sound",
                        subtitle = "Automatically switches to Vibrate if phone is in Silent, DND, or Airplane mode",
                        checked = currentSettings.vibrateInsteadOfSound,
                        onCheckedChange = onToggleVibrate,
                        tag = "toggle_vibrate"
                    )

                    Divider(modifier = Modifier.padding(vertical = 10.dp))

                    // Remind if phone on Airplane mode (Rule 9f: default yes)
                    SettingsToggleRow(
                        title = "Remind if phone on Airplane Mode",
                        subtitle = "Alarms continue to work reliably in Airplane or zero network mode (Default: Yes)",
                        checked = currentSettings.remindOnAirplaneMode,
                        onCheckedChange = onToggleAirplaneRemind,
                        tag = "toggle_airplane_remind"
                    )
                }
            }
        }

        // Section 3: Deactivate Reminders (Vacation / Pause)
        item {
            SettingsSectionHeader(title = "Vacation / Deactivate Reminders", icon = Icons.Default.AlarmOff)

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (currentSettings.deactivateAllReminders) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.surface
                ),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    // Rule 9g: Deactivate all reminders (with start and end date where end date can be blank)
                    SettingsToggleRow(
                        title = "Deactivate All Reminders",
                        subtitle = if (currentSettings.deactivateAllReminders) {
                            val startDisplay = com.example.util.DateUtils.formatDisplayDate(currentSettings.deactivateStartDate)
                            val endDisplay = if (currentSettings.deactivateEndDate.isNullOrBlank()) "Indefinite (Blank)" else com.example.util.DateUtils.formatDisplayDate(currentSettings.deactivateEndDate)
                            "PAUSED: from ${if (startDisplay.isNotBlank()) startDisplay else "Now"} to $endDisplay"
                        } else {
                            "Pause all alarms for hospitalization, travel, or medical hiatus"
                        },
                        checked = currentSettings.deactivateAllReminders,
                        onCheckedChange = { isChecked ->
                            if (isChecked) {
                                showDeactivateDialog = true
                            } else {
                                onToggleDeactivateReminders(false, null, null)
                            }
                        },
                        tag = "toggle_deactivate_reminders"
                    )
                }
            }
        }

        // Section 4: DPDP Compliance & Wipe Data
        item {
            SettingsSectionHeader(title = "Privacy & Legal Compliance (DPDP Act)", icon = Icons.Default.Security)

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = CardDefaults.outlinedCardBorder()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    AccessibleText(
                        text = "• 100% Offline App: Works without active internet or bandwidth.\n" +
                                "• Zero Cloud Telemetry: All medical files and schedules remain strictly inside your device SQLite storage.\n" +
                                "• DPDP Act (India) compliant.",
                        fontSize = 12.sp,
                        lineHeight = 18.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedButton(
                        onClick = { showWipeConfirm = true },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFDC2626)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = null)
                        Spacer(modifier = Modifier.width(6.dp))
                        AccessibleText(text = "Erase All Local Data on Phone", color = Color(0xFFDC2626), fontSize = 13.sp)
                    }
                }
            }
        }
    }

    // Deactivate Dialog (Rule 9g: start and end date where end date can be blank)
    if (showDeactivateDialog) {
        var startDate by remember { mutableStateOf(java.text.SimpleDateFormat("dd-MM-yyyy", java.util.Locale.getDefault()).format(java.util.Date())) }
        var endDate by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showDeactivateDialog = false },
            title = { AccessibleText(text = "Deactivate All Reminders", fontSize = 18.sp, fontWeight = FontWeight.Bold) },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    AccessibleText(
                        text = "Specify date range to pause alarms. End date can be left blank for indefinite deactivation.",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    com.example.ui.components.CalendarDatePickerField(
                        value = startDate,
                        onValueChange = { startDate = it },
                        label = "Start Date (Calendar)",
                        tag = "settings_deactivate_start",
                        modifier = Modifier.fillMaxWidth()
                    )
                    com.example.ui.components.CalendarDatePickerField(
                        value = endDate,
                        onValueChange = { endDate = it },
                        label = "End Date (Calendar)",
                        placeholder = "Blank if indefinite",
                        tag = "settings_deactivate_end",
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onToggleDeactivateReminders(true, startDate.trim(), endDate.trim().takeIf { it.isNotBlank() })
                        showDeactivateDialog = false
                    }
                ) {
                    Text("Pause Reminders")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showDeactivateDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Wipe confirmation
    if (showWipeConfirm) {
        AlertDialog(
            onDismissRequest = { showWipeConfirm = false },
            title = { AccessibleText(text = "Confirm Data Wipe", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color(0xFFDC2626)) },
            text = { AccessibleText(text = "Permanently delete all patient records and medicine schedules from this phone?", fontSize = 14.sp) },
            confirmButton = {
                Button(
                    onClick = {
                        onWipeData()
                        showWipeConfirm = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626))
                ) {
                    Text("Delete Everything", color = Color.White)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showWipeConfirm = false }) { Text("Cancel") }
            }
        )
    }
}

@Composable
fun SettingsSectionHeader(title: String, icon: ImageVector) {
    Row(
        modifier = Modifier.padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(imageVector = icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
        Spacer(modifier = Modifier.width(6.dp))
        AccessibleText(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
    }
}

@Composable
fun SettingsToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    tag: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onCheckedChange(!checked) }
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
            AccessibleText(text = title, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            AccessibleText(text = subtitle, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            modifier = Modifier.testTag(tag)
        )
    }
}
