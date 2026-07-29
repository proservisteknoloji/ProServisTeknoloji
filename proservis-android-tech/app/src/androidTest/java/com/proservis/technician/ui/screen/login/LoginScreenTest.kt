package com.proservis.technician.ui.screen.login

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test

class LoginScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun loginScreen_showsInitialElements() {
        composeTestRule.setContent {
            LoginScreen(
                state = LoginUiState(),
                onEmailChanged = {},
                onPasswordChanged = {},
                onLogin = {}
            )
        }

        composeTestRule.onNodeWithText("Proservis Teknisyen").assertIsDisplayed()
        composeTestRule.onNodeWithText("E-posta").assertIsDisplayed()
        composeTestRule.onNodeWithText("Sifre").assertIsDisplayed()
        composeTestRule.onNodeWithText("GIRIS").assertIsDisplayed()
    }

    @Test
    fun loginScreen_showsErrorMessage_whenProvidedInState() {
        val errorMessage = "E-posta ve sifre zorunludur."
        
        composeTestRule.setContent {
            LoginScreen(
                state = LoginUiState(errorMessage = errorMessage),
                onEmailChanged = {},
                onPasswordChanged = {},
                onLogin = {}
            )
        }

        composeTestRule.onNodeWithText(errorMessage).assertIsDisplayed()
    }

    @Test
    fun loginScreen_triggersLoginCallback_whenButtonClicked() {
        var loginClicked = false
        
        composeTestRule.setContent {
            LoginScreen(
                state = LoginUiState(),
                onEmailChanged = {},
                onPasswordChanged = {},
                onLogin = { loginClicked = true }
            )
        }

        composeTestRule.onNodeWithText("GIRIS").performClick()
        
        assert(loginClicked)
    }
}
