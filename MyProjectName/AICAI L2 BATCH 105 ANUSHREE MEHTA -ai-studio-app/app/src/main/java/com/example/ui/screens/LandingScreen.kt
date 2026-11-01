package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.HealthAndSafety
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.UserRole
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.ReadAloudButton

@Composable
fun LandingScreen(
    viewModel: GenerationsAppViewModel,
    onRoleSelected: (UserRole) -> Unit,
    onOpenOnboarding: () -> Unit,
    onOpenWebVersion: () -> Unit = {},
    onOpenAuth: () -> Unit = {}
) {
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    val welcomeText = "Welcome to Generations Connect. Connect isolated seniors with young storytellers through shared stories, memory games, and daily health routines. Please choose your profile or sign in with your mobile number."

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .testTag("landing_screen")
    ) {
        val maxWidthConstraint = if (maxWidth > 680.dp) 640.dp else maxWidth

        Column(
            modifier = Modifier
                .fillMaxSize()
                .widthIn(max = maxWidthConstraint)
                .align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Welcoming Header & Brand Emblem
                item {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(top = 12.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(88.dp)
                                .clip(CircleShape)
                                .background(
                                    Brush.linearGradient(
                                        listOf(Color(0xFF4A6B53), Color(0xFF75977E), Color(0xFFD4AF37))
                                    )
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Favorite,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(48.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        Text(
                            text = "Generations Connect",
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onBackground
                        )

                        Spacer(modifier = Modifier.height(6.dp))

                        Text(
                            text = "Connecting hearts, sharing stories, supporting daily routines",
                            fontSize = 19.sp,
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Voice Read Aloud Button
                item {
                    ReadAloudButton(
                        textToSpeak = welcomeText,
                        onSpeak = { viewModel.speakAloud(it) },
                        onStop = { viewModel.stopSpeaking() },
                        isSpeaking = isSpeaking,
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                // Mobile Number Registration & Login Card
                item {
                    Card(
                        shape = RoundedCornerShape(22.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                        border = androidx.compose.foundation.BorderStroke(2.5.dp, Color(0xFFD4AF37)),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onOpenAuth() }
                            .testTag("open_auth_screen_btn")
                    ) {
                        Row(
                            modifier = Modifier.padding(18.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                modifier = Modifier.weight(1f),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(50.dp)
                                        .clip(CircleShape)
                                        .background(Color(0xFFFEF3C7)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Security,
                                        contentDescription = null,
                                        tint = Color(0xFF78350F),
                                        modifier = Modifier.size(28.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(14.dp))
                                Column {
                                    Text(
                                        text = "Mobile Login & Register",
                                        fontSize = 19.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF1C271E)
                                    )
                                    Text(
                                        text = "Passcode • Face Lock • Screen Pattern",
                                        fontSize = 14.sp,
                                        color = Color(0xFF4F5E52)
                                    )
                                }
                            }
                            Button(
                                onClick = onOpenAuth,
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53))
                            ) {
                                Text("Sign In", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                item {
                    Text(
                        text = "Or Quick-Select Profile to Enter:",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 4.dp)
                    )
                }

                // 1. SENIOR PROFILE CARD (64dp button target, 20sp+ text)
                item {
                    ProfileSelectCard(
                        roleTitle = "SENIOR PROFILE",
                        roleName = "Eleanor Vance (Age 73)",
                        description = "High contrast, large 20sp+ text, voice read-aloud, medicine schedule & shared stories",
                        accentColor = Color(0xFF14535C),
                        containerColor = Color(0xFFE0F2F1),
                        icon = Icons.Default.Visibility,
                        testTag = "select_senior_profile",
                        onClick = { onRoleSelected(UserRole.SENIOR) }
                    )
                }

                // 2. CHILD PROFILE CARD
                item {
                    ProfileSelectCard(
                        roleTitle = "CHILD PROFILE",
                        roleName = "Leo Martinez (Age 8)",
                        description = "Playful & colorful with points, level stars, trophy badges & daily missions",
                        accentColor = Color(0xFF7C3AED),
                        containerColor = Color(0xFFEDE9FE),
                        icon = Icons.Default.ChildCare,
                        testTag = "select_child_profile",
                        onClick = { onRoleSelected(UserRole.CHILD) }
                    )
                }

                // 3. PARENT SAFETY PROFILE CARD
                item {
                    ProfileSelectCard(
                        roleTitle = "PARENT PROFILE",
                        roleName = "Guardian Dashboard",
                        description = "Safety management, screen time monitoring & buddy connection approvals",
                        accentColor = Color(0xFF1E40AF),
                        containerColor = Color(0xFFDBEAFE),
                        icon = Icons.Default.Security,
                        testTag = "select_parent_profile",
                        onClick = { onRoleSelected(UserRole.PARENT) }
                    )
                }

                // Onboarding & Help trigger
                item {
                    OutlinedButton(
                        onClick = onOpenOnboarding,
                        shape = RoundedCornerShape(18.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .defaultMinSize(minHeight = 56.dp)
                            .testTag("open_onboarding_btn")
                    ) {
                        Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "How Generations Connect Works",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                item {
                    Button(
                        onClick = onOpenWebVersion,
                        shape = RoundedCornerShape(18.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF1E293B),
                            contentColor = Color.White
                        ),
                        modifier = Modifier
                            .fillMaxWidth()
                            .defaultMinSize(minHeight = 56.dp)
                            .testTag("open_web_pwa_btn")
                    ) {
                        Text(
                            text = "🌐 Open Responsive Web (PWA) Version",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ProfileSelectCard(
    roleTitle: String,
    roleName: String,
    description: String,
    accentColor: Color,
    containerColor: Color,
    icon: ImageVector,
    testTag: String,
    onClick: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = containerColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag(testTag)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(
                    modifier = Modifier
                        .size(54.dp)
                        .clip(CircleShape)
                        .background(accentColor),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(32.dp)
                    )
                }

                Spacer(modifier = Modifier.width(14.dp))

                Column {
                    Text(
                        text = roleTitle,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = accentColor,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = roleName,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = description,
                fontSize = 18.sp,
                lineHeight = 26.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onClick,
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = 64.dp),
                shape = RoundedCornerShape(18.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = accentColor,
                    contentColor = Color.White
                )
            ) {
                Text(
                    text = "Enter as ${roleTitle.replace(" PROFILE", "")}",
                    fontSize = 19.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
