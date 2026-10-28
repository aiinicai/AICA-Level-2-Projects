package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.credentials.CredentialManager
import com.example.data.firebase.AuthService
import com.example.ui.MoneyGardenApp
import com.example.ui.MoneyGardenViewModel
import com.example.ui.screens.SignInScreen
import com.example.ui.theme.MyApplicationTheme
import com.google.firebase.Firebase
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.auth

class MainActivity : ComponentActivity() {
    private val viewModel: MoneyGardenViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                AuthGatedApp(viewModel = viewModel)
            }
        }
    }
}

@Composable
fun AuthGatedApp(viewModel: MoneyGardenViewModel) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val credentialManager = remember { CredentialManager.create(context) }

    var currentUser by remember { mutableStateOf<FirebaseUser?>(Firebase.auth.currentUser) }
    var isCheckingAutoSignIn by remember { mutableStateOf(currentUser == null) }

    DisposableEffect(Unit) {
        val listener = FirebaseAuth.AuthStateListener { auth ->
            currentUser = auth.currentUser
            auth.currentUser?.displayName?.takeIf { it.isNotBlank() }?.let { name ->
                viewModel.updateUserDisplayName(name)
            }
        }
        Firebase.auth.addAuthStateListener(listener)
        onDispose {
            Firebase.auth.removeAuthStateListener(listener)
        }
    }

    LaunchedEffect(Unit) {
        if (currentUser == null) {
            AuthService.attemptAutoSignIn(
                context = context,
                credentialManager = credentialManager,
                onAuthSuccess = { user ->
                    currentUser = user
                    user.displayName?.takeIf { it.isNotBlank() }?.let { name ->
                        viewModel.updateUserDisplayName(name)
                    }
                    isCheckingAutoSignIn = false
                },
                onUnauthenticated = {
                    isCheckingAutoSignIn = false
                },
                scope = coroutineScope
            )
        } else {
            currentUser?.displayName?.takeIf { it.isNotBlank() }?.let { name ->
                viewModel.updateUserDisplayName(name)
            }
            isCheckingAutoSignIn = false
        }
    }

    if (isCheckingAutoSignIn) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
        }
    } else if (currentUser == null) {
        SignInScreen(
            onAuthSuccess = { user ->
                currentUser = user
                user.displayName?.takeIf { it.isNotBlank() }?.let { name ->
                    viewModel.updateUserDisplayName(name)
                }
            }
        )
    } else {
        MoneyGardenApp(
            viewModel = viewModel,
            currentUser = currentUser,
            onSignOut = {
                currentUser = null
            }
        )
    }
}
