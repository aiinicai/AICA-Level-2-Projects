package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Emergency
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import com.example.data.model.PatientProfile

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppTopBar(
    profiles: List<PatientProfile>,
    activeProfileId: Long?,
    onSelectProfile: (Long) -> Unit,
    onAddProfileClick: () -> Unit,
    onSosClick: () -> Unit,
    onTestAlarmClick: () -> Unit
) {
    var expandedProfileMenu by remember { mutableStateOf(false) }
    val currentProfile = profiles.firstOrNull { it.id == activeProfileId }
        ?: profiles.firstOrNull { it.isPrimary }
        ?: profiles.firstOrNull()

    TopAppBar(
        title = {
            Column {
                AccessibleText(
                    text = "My Medicine reminder",
                    fontSize = 19.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )

                // Patient Switcher Chip
                Box {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(20.dp))
                            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f))
                            .clickable { expandedProfileMenu = true }
                            .padding(horizontal = 8.dp, vertical = 2.dp)
                            .testTag("profile_selector_dropdown"),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Person,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(
                            text = currentProfile?.name ?: "Select Patient",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Icon(
                            imageVector = Icons.Default.ArrowDropDown,
                            contentDescription = "Switch patient",
                            tint = MaterialTheme.colorScheme.onPrimaryContainer,
                            modifier = Modifier.size(16.dp)
                        )
                    }

                    DropdownMenu(
                        expanded = expandedProfileMenu,
                        onDismissRequest = { expandedProfileMenu = false }
                    ) {
                        profiles.forEach { profile ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text(
                                            text = profile.name + if (profile.isPrimary) " (Primary)" else "",
                                            fontWeight = if (profile.id == currentProfile?.id) FontWeight.Bold else FontWeight.Normal
                                        )
                                        Text(
                                            text = "Age: ${profile.age} • ${profile.sex}",
                                            fontSize = 12.sp,
                                            color = Color.Gray
                                        )
                                    }
                                },
                                onClick = {
                                    onSelectProfile(profile.id)
                                    expandedProfileMenu = false
                                },
                                leadingIcon = {
                                    Icon(Icons.Default.Person, contentDescription = null)
                                },
                                modifier = Modifier.testTag("menu_profile_${profile.id}")
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("+ Add New Patient", fontWeight = FontWeight.Bold) },
                            onClick = {
                                expandedProfileMenu = false
                                onAddProfileClick()
                            },
                            leadingIcon = {
                                Icon(Icons.Default.Add, contentDescription = null)
                            },
                            modifier = Modifier.testTag("menu_add_profile")
                        )
                    }
                }
            }
        },
        actions = {
            // Test Alarm Quick Action Button
            IconButton(
                onClick = onTestAlarmClick,
                modifier = Modifier.testTag("btn_top_test_alarm")
            ) {
                Icon(
                    imageVector = Icons.Default.Alarm,
                    contentDescription = "Test Alarm",
                    tint = MaterialTheme.colorScheme.primary
                )
            }

            // Quick SOS Emergency Button
            Surface(
                onClick = onSosClick,
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFFDC2626),
                modifier = Modifier
                    .padding(end = 8.dp)
                    .testTag("btn_top_sos")
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Emergency,
                        contentDescription = "SOS",
                        tint = Color.White,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    AccessibleText(
                        text = "SOS",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    )
}
