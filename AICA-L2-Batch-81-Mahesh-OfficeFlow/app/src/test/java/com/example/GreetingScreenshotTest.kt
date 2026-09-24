package com.example

import android.content.Context
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
import androidx.test.core.app.ApplicationProvider
import com.example.ui.OfficeApp
import com.example.ui.theme.MyApplicationTheme
import com.github.takahirom.roborazzi.RobolectricDeviceQualifiers
import com.github.takahirom.roborazzi.captureRoboImage
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = RobolectricDeviceQualifiers.Pixel8, sdk = [36])
class GreetingScreenshotTest {

  @get:Rule val composeTestRule = createComposeRule()

  @Before
  fun initializeFirebase() {
    // Robolectric does not run the Firebase initialization provider, so the repository's
    // Firestore handle would fail to construct. Firestore serves from its local cache here,
    // so the rendered screen never depends on the network.
    val context = ApplicationProvider.getApplicationContext<Context>()
    if (FirebaseApp.getApps(context).isEmpty()) {
      FirebaseApp.initializeApp(
        context,
        FirebaseOptions.Builder()
          .setProjectId("office-flow-integration")
          .setApplicationId("1:272282085767:android:01ac56a4315f87eaf90b22")
          .setApiKey("AIzaSyBQxMe57oSTZkYFS_EyEbVTBe296yR0-cg")
          .build()
      )
    }
  }

  @Test
  fun greeting_screenshot() {
    composeTestRule.setContent { MyApplicationTheme { OfficeApp() } }

    composeTestRule.onRoot().captureRoboImage(filePath = "src/test/screenshots/greeting.png")
  }
}
