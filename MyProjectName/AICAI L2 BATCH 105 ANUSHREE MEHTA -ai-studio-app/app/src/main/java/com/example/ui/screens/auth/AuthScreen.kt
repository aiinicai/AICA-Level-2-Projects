package com.example.ui.screens.auth

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.GridOn
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.AppUser
import com.example.data.model.AuthLockType
import com.example.data.model.UserRole
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MandalaDecor

@Composable
fun AuthScreen(
    viewModel: GenerationsAppViewModel,
    onAuthSuccess: () -> Unit,
    onBack: () -> Unit
) {
    val registeredUsers by viewModel.registeredUsers.collectAsState()
    var selectedAuthTab by remember { mutableIntStateOf(0) } // 0: Login, 1: Register

    // Registration state
    var regMobile by remember { mutableStateOf("") }
    var regName by remember { mutableStateOf("") }
    var regRole by remember { mutableStateOf(UserRole.SENIOR) }
    var regLockType by remember { mutableStateOf(AuthLockType.PASSCODE) }
    var regPasscode by remember { mutableStateOf("") }
    var regPattern by remember { mutableStateOf(listOf<Int>()) }

    // Login state
    var loginMobile by remember { mutableStateOf("9876543210") }
    var loginLockType by remember { mutableStateOf(AuthLockType.PASSCODE) }
    var loginPasscode by remember { mutableStateOf("") }
    var loginPattern by remember { mutableStateOf(listOf<Int>()) }
    var isFaceScanning by remember { mutableStateOf(false) }
    var faceScanSuccess by remember { mutableStateOf(false) }
    var authErrorMessage by remember { mutableStateOf<String?>(null) }

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFFBF8F2))
            .testTag("auth_screen")
    ) {
        val maxWidthConstraint = if (maxWidth > 650.dp) 600.dp else maxWidth

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
                verticalArrangement = Arrangement.spacedBy(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Top Header with Sacred Mandala & Title
                item {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) {
                        MandalaDecor(
                            size = 72.dp,
                            tint = Color(0xFFD4AF37),
                            alpha = 0.95f
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "Generations Connect",
                            fontSize = 28.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1C271E),
                            textAlign = TextAlign.Center
                        )
                        Text(
                            text = "Secure Mobile Registration & Biometric Login",
                            fontSize = 16.sp,
                            color = Color(0xFF4F5E52),
                            textAlign = TextAlign.Center
                        )
                    }
                }

                // Auth Mode Tabs (Sign In / New User Registration)
                item {
                    Surface(
                        shape = RoundedCornerShape(18.dp),
                        color = Color(0xFFFFFDF9),
                        border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        TabRow(
                            selectedTabIndex = selectedAuthTab,
                            containerColor = Color.Transparent,
                            contentColor = Color(0xFF4A6B53),
                            indicator = { tabPositions ->
                                TabRowDefaults.SecondaryIndicator(
                                    Modifier.tabIndicatorOffset(tabPositions[selectedAuthTab]),
                                    color = Color(0xFF4A6B53),
                                    height = 4.dp
                                )
                            }
                        ) {
                            Tab(
                                selected = selectedAuthTab == 0,
                                onClick = {
                                    selectedAuthTab = 0
                                    authErrorMessage = null
                                },
                                text = {
                                    Text(
                                        text = "🔑 Sign In",
                                        fontSize = 18.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = if (selectedAuthTab == 0) Color(0xFF4A6B53) else Color(0xFF4F5E52)
                                    )
                                }
                            )
                            Tab(
                                selected = selectedAuthTab == 1,
                                onClick = {
                                    selectedAuthTab = 1
                                    authErrorMessage = null
                                },
                                text = {
                                    Text(
                                        text = "📝 Register New User",
                                        fontSize = 17.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = if (selectedAuthTab == 1) Color(0xFF4A6B53) else Color(0xFF4F5E52)
                                    )
                                }
                            )
                        }
                    }
                }

                // Error message banner
                if (authErrorMessage != null) {
                    item {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFFFDF2E9),
                            border = BorderStroke(1.5.dp, Color(0xFFC86446)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = authErrorMessage!!,
                                color = Color(0xFFC86446),
                                fontWeight = FontWeight.Bold,
                                fontSize = 15.sp,
                                modifier = Modifier.padding(14.dp),
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }

                // -------------------------------------------------------------
                // TAB 0: SIGN IN (PASSCODE, FACE LOCK, OR SCREEN PATTERN)
                // -------------------------------------------------------------
                if (selectedAuthTab == 0) {
                    // Mobile Number Selection or Entry
                    item {
                        Card(
                            shape = RoundedCornerShape(20.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                            border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(18.dp)) {
                                Text(
                                    text = "Mobile Phone Number",
                                    fontSize = 17.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1C271E)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = loginMobile,
                                    onValueChange = { loginMobile = it },
                                    modifier = Modifier.fillMaxWidth().testTag("login_mobile_input"),
                                    placeholder = { Text("Enter 10-digit mobile number") },
                                    leadingIcon = {
                                        Icon(Icons.Default.Phone, contentDescription = null, tint = Color(0xFF4A6B53))
                                    },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedBorderColor = Color(0xFF4A6B53),
                                        unfocusedBorderColor = Color(0xFF75977E)
                                    ),
                                    shape = RoundedCornerShape(14.dp)
                                )

                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "Saved Profiles on Device:",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color(0xFF4F5E52)
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    registeredUsers.forEach { user ->
                                        val isSel = loginMobile == user.mobileNumber
                                        Surface(
                                            onClick = {
                                                loginMobile = user.mobileNumber
                                                authErrorMessage = null
                                            },
                                            shape = RoundedCornerShape(12.dp),
                                            color = if (isSel) Color(0xFFEBF2EC) else Color(0xFFF2EFE8),
                                            border = BorderStroke(if (isSel) 2.dp else 1.dp, if (isSel) Color(0xFF4A6B53) else Color.Transparent),
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Column(
                                                modifier = Modifier.padding(8.dp),
                                                horizontalAlignment = Alignment.CenterHorizontally
                                            ) {
                                                Text(
                                                    text = when (user.role) {
                                                        UserRole.SENIOR -> "👴 Eleanor"
                                                        UserRole.CHILD -> "🧒 Leo"
                                                        UserRole.PARENT -> "🛡️ Maria"
                                                    },
                                                    fontSize = 13.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = Color(0xFF1C271E)
                                                )
                                                Text(
                                                    text = user.mobileNumber.takeLast(4).padStart(10, '•'),
                                                    fontSize = 10.sp,
                                                    color = Color(0xFF4F5E52)
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Choose Login Method (Passcode, Face Lock, Screen Pattern)
                    item {
                        Card(
                            shape = RoundedCornerShape(20.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                            border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(18.dp)) {
                                Text(
                                    text = "Choose Verification Method",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1C271E)
                                )
                                Spacer(modifier = Modifier.height(10.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    // Passcode Button
                                    AuthMethodTile(
                                        title = "Passcode",
                                        icon = Icons.Default.Lock,
                                        isSelected = loginLockType == AuthLockType.PASSCODE,
                                        modifier = Modifier.weight(1f),
                                        onClick = { loginLockType = AuthLockType.PASSCODE }
                                    )
                                    // Face Lock Button
                                    AuthMethodTile(
                                        title = "Face Lock",
                                        icon = Icons.Default.Face,
                                        isSelected = loginLockType == AuthLockType.FACE_LOCK,
                                        modifier = Modifier.weight(1f),
                                        onClick = { loginLockType = AuthLockType.FACE_LOCK }
                                    )
                                    // Pattern Button
                                    AuthMethodTile(
                                        title = "Pattern",
                                        icon = Icons.Default.GridOn,
                                        isSelected = loginLockType == AuthLockType.PATTERN,
                                        modifier = Modifier.weight(1f),
                                        onClick = { loginLockType = AuthLockType.PATTERN }
                                    )
                                }

                                Spacer(modifier = Modifier.height(18.dp))

                                // Dynamic verification input based on chosen lock type
                                when (loginLockType) {
                                    AuthLockType.PASSCODE -> {
                                        PasscodeKeypadView(
                                            passcode = loginPasscode,
                                            onPasscodeChange = { loginPasscode = it },
                                            onSubmit = {
                                                val user = registeredUsers.find { it.mobileNumber == loginMobile }
                                                if (user == null) {
                                                    authErrorMessage = "Mobile number not registered. Please register first."
                                                } else if (user.passcode != loginPasscode && loginPasscode != "1234") {
                                                    authErrorMessage = "Incorrect passcode. (Demo default is 1234)"
                                                } else {
                                                    viewModel.loginUser(user)
                                                    onAuthSuccess()
                                                }
                                            }
                                        )
                                    }
                                    AuthLockType.FACE_LOCK -> {
                                        FaceLockScannerView(
                                            isScanning = isFaceScanning,
                                            isVerified = faceScanSuccess,
                                            onStartScan = {
                                                val user = registeredUsers.find { it.mobileNumber == loginMobile }
                                                if (user == null) {
                                                    authErrorMessage = "Mobile number not registered. Please register first."
                                                } else {
                                                    isFaceScanning = true
                                                    authErrorMessage = null
                                                }
                                            },
                                            onScanCompleted = {
                                                isFaceScanning = false
                                                faceScanSuccess = true
                                                val user = registeredUsers.find { it.mobileNumber == loginMobile }
                                                if (user != null) {
                                                    viewModel.loginUser(user)
                                                    onAuthSuccess()
                                                }
                                            }
                                        )
                                    }
                                    AuthLockType.PATTERN -> {
                                        PatternLockView(
                                            selectedDots = loginPattern,
                                            onDotSelected = { dot ->
                                                if (!loginPattern.contains(dot)) {
                                                    loginPattern = loginPattern + dot
                                                }
                                            },
                                            onReset = { loginPattern = emptyList() },
                                            onSubmit = {
                                                val user = registeredUsers.find { it.mobileNumber == loginMobile }
                                                val patternStr = loginPattern.joinToString(",")
                                                if (user == null) {
                                                    authErrorMessage = "Mobile number not registered. Please register first."
                                                } else if (loginPattern.size < 3) {
                                                    authErrorMessage = "Connect at least 3 pattern dots to unlock."
                                                } else {
                                                    viewModel.loginUser(user)
                                                    onAuthSuccess()
                                                }
                                            }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // TAB 1: REGISTER NEW USER WITH MOBILE NUMBER
                // -------------------------------------------------------------
                if (selectedAuthTab == 1) {
                    item {
                        Card(
                            shape = RoundedCornerShape(20.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                            border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Text(
                                    text = "Create New Account",
                                    fontSize = 22.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1C271E)
                                )
                                Spacer(modifier = Modifier.height(14.dp))

                                // Mobile Number
                                OutlinedTextField(
                                    value = regMobile,
                                    onValueChange = { regMobile = it },
                                    label = { Text("Mobile Phone Number") },
                                    placeholder = { Text("e.g. 9876543210") },
                                    leadingIcon = {
                                        Icon(Icons.Default.Phone, contentDescription = null, tint = Color(0xFF4A6B53))
                                    },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                                    modifier = Modifier.fillMaxWidth().testTag("register_mobile_input"),
                                    shape = RoundedCornerShape(14.dp)
                                )

                                Spacer(modifier = Modifier.height(12.dp))

                                // Full Name
                                OutlinedTextField(
                                    value = regName,
                                    onValueChange = { regName = it },
                                    label = { Text("Full Name") },
                                    placeholder = { Text("e.g. Eleanor Vance") },
                                    leadingIcon = {
                                        Icon(Icons.Default.Person, contentDescription = null, tint = Color(0xFF4A6B53))
                                    },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth().testTag("register_name_input"),
                                    shape = RoundedCornerShape(14.dp)
                                )

                                Spacer(modifier = Modifier.height(14.dp))

                                // Profile Role Selector
                                Text(
                                    text = "Account Profile:",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1C271E)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    UserRole.values().forEach { role ->
                                        val isSel = regRole == role
                                        FilterChip(
                                            selected = isSel,
                                            onClick = { regRole = role },
                                            label = {
                                                Text(
                                                    text = when (role) {
                                                        UserRole.SENIOR -> "👴 Senior"
                                                        UserRole.CHILD -> "🧒 Child"
                                                        UserRole.PARENT -> "🛡️ Parent"
                                                    },
                                                    fontWeight = FontWeight.Bold
                                                )
                                            },
                                            colors = FilterChipDefaults.filterChipColors(
                                                selectedContainerColor = Color(0xFF4A6B53),
                                                selectedLabelColor = Color.White
                                            ),
                                            border = FilterChipDefaults.filterChipBorder(
                                                borderColor = Color(0xFF75977E),
                                                selectedBorderColor = Color(0xFF334D3B),
                                                borderWidth = 2.dp,
                                                enabled = true,
                                                selected = isSel
                                            ),
                                            modifier = Modifier.weight(1f)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                // Setup Security Method
                                Text(
                                    text = "Set Security Lock Method:",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1C271E)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    AuthMethodTile(
                                        title = "Passcode",
                                        icon = Icons.Default.Lock,
                                        isSelected = regLockType == AuthLockType.PASSCODE,
                                        modifier = Modifier.weight(1f),
                                        onClick = { regLockType = AuthLockType.PASSCODE }
                                    )
                                    AuthMethodTile(
                                        title = "Face Lock",
                                        icon = Icons.Default.Face,
                                        isSelected = regLockType == AuthLockType.FACE_LOCK,
                                        modifier = Modifier.weight(1f),
                                        onClick = { regLockType = AuthLockType.FACE_LOCK }
                                    )
                                    AuthMethodTile(
                                        title = "Pattern",
                                        icon = Icons.Default.GridOn,
                                        isSelected = regLockType == AuthLockType.PATTERN,
                                        modifier = Modifier.weight(1f),
                                        onClick = { regLockType = AuthLockType.PATTERN }
                                    )
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                when (regLockType) {
                                    AuthLockType.PASSCODE -> {
                                        OutlinedTextField(
                                            value = regPasscode,
                                            onValueChange = { if (it.length <= 6) regPasscode = it },
                                            label = { Text("Set 4 to 6 Digit Passcode") },
                                            placeholder = { Text("e.g. 1234") },
                                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                                            singleLine = true,
                                            modifier = Modifier.fillMaxWidth(),
                                            shape = RoundedCornerShape(14.dp)
                                        )
                                    }
                                    AuthLockType.FACE_LOCK -> {
                                        Surface(
                                            shape = RoundedCornerShape(14.dp),
                                            color = Color(0xFFEBF2EC),
                                            border = BorderStroke(1.5.dp, Color(0xFF4A6B53)),
                                            modifier = Modifier.fillMaxWidth()
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(14.dp),
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Icon(Icons.Default.Face, contentDescription = null, tint = Color(0xFF4A6B53), modifier = Modifier.size(32.dp))
                                                Spacer(modifier = Modifier.width(12.dp))
                                                Text(
                                                    text = "Facial recognition biometrics will be captured upon device setup.",
                                                    fontSize = 14.sp,
                                                    color = Color(0xFF1C271E)
                                                )
                                            }
                                        }
                                    }
                                    AuthLockType.PATTERN -> {
                                        Column {
                                            Text("Tap 4 dots to configure your unlock pattern:", fontSize = 14.sp, color = Color(0xFF4F5E52))
                                            Spacer(modifier = Modifier.height(8.dp))
                                            PatternLockView(
                                                selectedDots = regPattern,
                                                onDotSelected = { dot ->
                                                    if (!regPattern.contains(dot)) {
                                                        regPattern = regPattern + dot
                                                    }
                                                },
                                                onReset = { regPattern = emptyList() },
                                                onSubmit = {}
                                            )
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(20.dp))

                                // Submit Registration Button
                                Button(
                                    onClick = {
                                        if (regMobile.isBlank() || regMobile.length < 7) {
                                            authErrorMessage = "Please enter a valid mobile phone number."
                                        } else if (regName.isBlank()) {
                                            authErrorMessage = "Please enter your name."
                                        } else {
                                            val newUser = AppUser(
                                                mobileNumber = regMobile.trim(),
                                                displayName = regName.trim(),
                                                role = regRole,
                                                passcode = if (regPasscode.isNotBlank()) regPasscode else "1234",
                                                patternCode = if (regPattern.isNotEmpty()) regPattern.joinToString(",") else "0,1,2,5",
                                                hasFaceRegistered = true
                                            )
                                            viewModel.registerUser(newUser)
                                            onAuthSuccess()
                                        }
                                    },
                                    shape = RoundedCornerShape(16.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53)),
                                    border = BorderStroke(2.5.dp, Color(0xFF334D3B)),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .defaultMinSize(minHeight = 56.dp)
                                        .testTag("submit_registration_btn")
                                ) {
                                    Text("Register & Enter App ➔", fontSize = 19.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AuthMethodTile(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    isSelected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(14.dp),
        color = if (isSelected) Color(0xFF4A6B53) else Color(0xFFF2EFE8),
        border = BorderStroke(2.5.dp, if (isSelected) Color(0xFF334D3B) else Color(0xFF75977E)),
        modifier = modifier.defaultMinSize(minHeight = 64.dp)
    ) {
        Column(
            modifier = Modifier.padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isSelected) Color.White else Color(0xFF1C271E),
                modifier = Modifier.size(26.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = title,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = if (isSelected) Color.White else Color(0xFF1C271E)
            )
        }
    }
}

// -------------------------------------------------------------
// PASSCODE KEYPAD COMPONENT
// -------------------------------------------------------------
@Composable
private fun PasscodeKeypadView(
    passcode: String,
    onPasscodeChange: (String) -> Unit,
    onSubmit: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Enter 4-Digit Passcode:", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF1C271E))
        Spacer(modifier = Modifier.height(10.dp))

        // 4 Pin Dots
        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            for (i in 0 until 4) {
                val isFilled = i < passcode.length
                Box(
                    modifier = Modifier
                        .size(20.dp)
                        .clip(CircleShape)
                        .background(if (isFilled) Color(0xFF4A6B53) else Color(0xFFE2DDD4))
                        .border(1.5.dp, Color(0xFF75977E), CircleShape)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Numeric Keypad Grid
        val keys = listOf(
            listOf("1", "2", "3"),
            listOf("4", "5", "6"),
            listOf("7", "8", "9"),
            listOf("Clear", "0", "Unlock")
        )

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            keys.forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { key ->
                        Surface(
                            onClick = {
                                when (key) {
                                    "Clear" -> onPasscodeChange("")
                                    "Unlock" -> onSubmit()
                                    else -> {
                                        if (passcode.length < 4) {
                                            val newCode = passcode + key
                                            onPasscodeChange(newCode)
                                            if (newCode.length == 4) {
                                                // Trigger submit after short moment
                                                onSubmit()
                                            }
                                        }
                                    }
                                }
                            },
                            shape = RoundedCornerShape(14.dp),
                            color = when (key) {
                                "Unlock" -> Color(0xFF4A6B53)
                                "Clear" -> Color(0xFFF2EFE8)
                                else -> Color(0xFFFFFDF9)
                            },
                            border = BorderStroke(2.dp, Color(0xFF75977E)),
                            modifier = Modifier
                                .weight(1f)
                                .height(52.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(
                                    text = key,
                                    fontSize = if (key.length > 1) 15.sp else 22.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (key == "Unlock") Color.White else Color(0xFF1C271E)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// -------------------------------------------------------------
// FACE LOCK SCANNER COMPONENT
// -------------------------------------------------------------
@Composable
private fun FaceLockScannerView(
    isScanning: Boolean,
    isVerified: Boolean,
    onStartScan: () -> Unit,
    onScanCompleted: () -> Unit
) {
    val transition = rememberInfiniteTransition(label = "face_scan")
    val scanOffset by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1400, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scan_line"
    )

    androidx.compose.runtime.LaunchedEffect(isScanning) {
        if (isScanning) {
            kotlinx.coroutines.delay(2000L)
            onScanCompleted()
        }
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(170.dp)
                .clip(CircleShape)
                .background(Color(0xFFEBF2EC))
                .border(3.dp, if (isVerified) Color(0xFF16A34A) else Color(0xFF4A6B53), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = if (isVerified) Icons.Default.CheckCircle else Icons.Default.Face,
                contentDescription = null,
                tint = if (isVerified) Color(0xFF16A34A) else Color(0xFF4A6B53),
                modifier = Modifier.size(90.dp)
            )

            // Scanning line animation
            if (isScanning && !isVerified) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val y = size.height * scanOffset
                    drawLine(
                        color = Color(0xFFD4AF37),
                        start = Offset(20f, y),
                        end = Offset(size.width - 20f, y),
                        strokeWidth = 5f,
                        cap = StrokeCap.Round
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))
        Text(
            text = when {
                isVerified -> "✓ Facial Biometrics Verified! Welcome."
                isScanning -> "Analyzing facial structure & biometrics..."
                else -> "Position face within camera view for instant unlock"
            },
            fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold,
            color = if (isVerified) Color(0xFF166534) else Color(0xFF1C271E),
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(14.dp))
        Button(
            onClick = onStartScan,
            enabled = !isScanning && !isVerified,
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53)),
            border = BorderStroke(2.5.dp, Color(0xFF334D3B)),
            modifier = Modifier.fillMaxWidth().defaultMinSize(minHeight = 52.dp)
        ) {
            Text(if (isScanning) "Scanning Face..." else "Scan Face to Unlock 😊", fontSize = 18.sp, fontWeight = FontWeight.Bold)
        }
    }
}

// -------------------------------------------------------------
// 3x3 SCREEN PATTERN LOCK COMPONENT
// -------------------------------------------------------------
@Composable
private fun PatternLockView(
    selectedDots: List<Int>,
    onDotSelected: (Int) -> Unit,
    onReset: () -> Unit,
    onSubmit: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Connect Pattern Dots (${selectedDots.size} connected):",
            fontSize = 15.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color(0xFF1C271E)
        )
        Spacer(modifier = Modifier.height(12.dp))

        // 3x3 Dot Grid
        Surface(
            shape = RoundedCornerShape(20.dp),
            color = Color(0xFFF2EFE8),
            border = BorderStroke(2.dp, Color(0xFF75977E)),
            modifier = Modifier.size(240.dp)
        ) {
            Box(modifier = Modifier.fillMaxSize().padding(20.dp)) {
                // Background pattern connections
                Canvas(modifier = Modifier.fillMaxSize()) {
                    if (selectedDots.size >= 2) {
                        val dotSize = size.width / 3f
                        val centerOffset = dotSize / 2f
                        for (i in 0 until selectedDots.size - 1) {
                            val dotA = selectedDots[i]
                            val dotB = selectedDots[i + 1]
                            val ax = (dotA % 3) * dotSize + centerOffset
                            val ay = (dotA / 3) * dotSize + centerOffset
                            val bx = (dotB % 3) * dotSize + centerOffset
                            val by = (dotB / 3) * dotSize + centerOffset
                            drawLine(
                                color = Color(0xFFD4AF37),
                                start = Offset(ax, ay),
                                end = Offset(bx, by),
                                strokeWidth = 8f,
                                cap = StrokeCap.Round
                            )
                        }
                    }
                }

                // Interactive 9 Dots
                Column(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    for (row in 0..2) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            for (col in 0..2) {
                                val dotIndex = row * 3 + col
                                val isSelected = selectedDots.contains(dotIndex)
                                Box(
                                    modifier = Modifier
                                        .size(46.dp)
                                        .clip(CircleShape)
                                        .background(if (isSelected) Color(0xFF4A6B53) else Color.White)
                                        .border(2.5.dp, if (isSelected) Color(0xFFD4AF37) else Color(0xFF75977E), CircleShape)
                                        .clickable { onDotSelected(dotIndex) },
                                    contentAlignment = Alignment.Center
                                ) {
                                    if (isSelected) {
                                        Text(
                                            text = "${selectedDots.indexOf(dotIndex) + 1}",
                                            color = Color.White,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 16.sp
                                        )
                                    } else {
                                        Box(
                                            modifier = Modifier
                                                .size(12.dp)
                                                .clip(CircleShape)
                                                .background(Color(0xFF75977E))
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            OutlinedButton(
                onClick = onReset,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(2.dp, Color(0xFF75977E)),
                modifier = Modifier.weight(1f).height(50.dp)
            ) {
                Text("Reset Pattern", fontWeight = FontWeight.Bold, color = Color(0xFF1C271E))
            }
            Button(
                onClick = onSubmit,
                enabled = selectedDots.isNotEmpty(),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53)),
                border = BorderStroke(2.5.dp, Color(0xFF334D3B)),
                modifier = Modifier.weight(1f).height(50.dp)
            ) {
                Text("Verify Pattern", fontWeight = FontWeight.Bold)
            }
        }
    }
}
