package com.example.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mail
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.*

data class UserSession(
    val email: String,
    val displayName: String,
    val role: String,
    val authProvider: String = "Firebase Auth"
)

object AuthState {
    var currentUser by mutableStateOf<UserSession?>(
        UserSession(
            email = "james.sterling@finpilot.ai",
            displayName = "James Sterling",
            role = "Chartered Consultant",
            authProvider = "Google Sign-In"
        )
    )
}

@Composable
fun AuthModalSheet(
    onDismiss: () -> Unit,
    onLoginSuccess: (UserSession) -> Unit
) {
    var email by remember { mutableStateOf("james.sterling@finpilot.ai") }
    var password by remember { mutableStateOf("••••••••") }
    var isSignUp by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .background(LavenderAccent.copy(alpha = 0.15f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text("FP", color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = if (isSignUp) "Create FinPilot Account" else "Welcome to FinPilot AI",
                color = TextPrimary,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Personal CFO & Wealth Intelligence",
                color = TextSecondary,
                fontSize = 12.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email Address", color = TextSecondary) },
                leadingIcon = { Icon(Icons.Default.Mail, contentDescription = null, tint = LavenderAccent) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = LavenderAccent,
                    unfocusedBorderColor = DarkBorder,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary
                )
            )

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Password", color = TextSecondary) },
                leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null, tint = LavenderAccent) },
                visualTransformation = PasswordVisualTransformation(),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = LavenderAccent,
                    unfocusedBorderColor = DarkBorder,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary
                )
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Primary Auth Button
            Button(
                onClick = {
                    val session = UserSession(
                        email = email.ifEmpty { "james.sterling@finpilot.ai" },
                        displayName = email.substringBefore("@").replace(".", " ").capitalize(),
                        role = "Salaried & Investor"
                    )
                    AuthState.currentUser = session
                    onLoginSuccess(session)
                },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text(
                    text = if (isSignUp) "Create Account" else "Sign In with Email",
                    color = Color(0xFF0F1115),
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Social Sign-In buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Google
                OutlinedButton(
                    onClick = {
                        val session = UserSession(
                            email = "james.google@finpilot.ai",
                            displayName = "James Sterling",
                            role = "Chartered Consultant",
                            authProvider = "Google"
                        )
                        AuthState.currentUser = session
                        onLoginSuccess(session)
                    },
                    modifier = Modifier.weight(1f).height(44.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
                ) {
                    Text("G  Google", color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }

                // Apple
                OutlinedButton(
                    onClick = {
                        val session = UserSession(
                            email = "james.apple@finpilot.ai",
                            displayName = "James Sterling",
                            role = "Executive",
                            authProvider = "Apple"
                        )
                        AuthState.currentUser = session
                        onLoginSuccess(session)
                    },
                    modifier = Modifier.weight(1f).height(44.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
                ) {
                    Text("  Apple", color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Switch Personas (For Capstone and Evaluator testing)
            Text("Or switch test persona:", color = TextSecondary, fontSize = 11.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                listOf(
                    "Salaried" to "Salaried Tech Exec",
                    "CA/Doctor" to "Chartered Consultant",
                    "Business" to "Business Owner"
                ).forEach { (label, role) ->
                    Box(
                        modifier = Modifier
                            .background(DarkSurfaceVariant, RoundedCornerShape(8.dp))
                            .border(1.dp, DarkBorderLight, RoundedCornerShape(8.dp))
                            .clickable {
                                val session = UserSession(
                                    email = "${label.lowercase()}@finpilot.ai",
                                    displayName = "$label User",
                                    role = role
                                )
                                AuthState.currentUser = session
                                onLoginSuccess(session)
                            }
                            .padding(horizontal = 8.dp, vertical = 6.dp)
                    ) {
                        Text(label, color = BlueAccent, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = if (isSignUp) "Already have an account? Sign In" else "Don't have an account? Sign Up",
                color = LavenderAccent,
                fontSize = 12.sp,
                modifier = Modifier.clickable { isSignUp = !isSignUp }
            )
        }
    }
}
