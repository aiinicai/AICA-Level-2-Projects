package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ContactPhone
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LocalPharmacy
import androidx.compose.material.icons.filled.MedicalInformation
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Today
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class ModuleItem(
    val id: String,
    val title: String,
    val icon: ImageVector,
    val accentColor: Color
)

val APP_MODULES = listOf(
    ModuleItem("TODAY", "Today", Icons.Default.Today, Color(0xFF0284C7)),
    ModuleItem("CALENDAR", "Calendar", Icons.Default.CalendarMonth, Color(0xFF2563EB)),
    ModuleItem("VITALS", "Vitals", Icons.Default.Favorite, Color(0xFFEA580C)),
    ModuleItem("PROFILE", "Profile", Icons.Default.Person, Color(0xFF7C3AED)),
    ModuleItem("PRESCRIPTIONS", "Prescriptions", Icons.Default.Description, Color(0xFF0D9488)),
    ModuleItem("REPORTS", "Reports", Icons.Default.MedicalInformation, Color(0xFF059669)),
    ModuleItem("MEDICINES", "Medicine", Icons.Default.Medication, Color(0xFFD97706)),
    ModuleItem("CHEMIST", "Chemist", Icons.Default.LocalPharmacy, Color(0xFFE11D48)),
    ModuleItem("EMERGENCY", "Emergency", Icons.Default.ContactPhone, Color(0xFFDC2626)),
    ModuleItem("SETTINGS", "Settings", Icons.Default.Settings, Color(0xFF475569))
)

@Composable
fun HomeModuleBar(
    currentModule: String,
    onSelectModule: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 6.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f)
        ),
        shape = RoundedCornerShape(18.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(scrollState)
                .padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            APP_MODULES.forEach { item ->
                val isSelected = currentModule == item.id
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            if (isSelected) item.accentColor.copy(alpha = 0.18f)
                            else Color.Transparent
                        )
                        .clickable { onSelectModule(item.id) }
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                        .testTag("nav_module_${item.id.lowercase()}"),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(
                                if (isSelected) item.accentColor
                                else MaterialTheme.colorScheme.surface
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = item.icon,
                            contentDescription = item.title,
                            tint = if (isSelected) Color.White else item.accentColor,
                            modifier = Modifier.size(24.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    AccessibleText(
                        text = item.title,
                        fontSize = 12.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) item.accentColor else MaterialTheme.colorScheme.onSurface,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}
