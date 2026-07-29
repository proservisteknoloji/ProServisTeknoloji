package com.proservis.technician.ui.screen.login

import app.cash.turbine.test
import com.proservis.technician.domain.model.UserSession
import com.proservis.technician.domain.usecase.LoginUseCase
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LoginViewModelTest {

    private val loginUseCase = mockk<LoginUseCase>()
    private lateinit var viewModel: LoginViewModel
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        viewModel = LoginViewModel(loginUseCase)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `initial state is correct`() {
        val state = viewModel.uiState.value
        assertEquals("", state.email)
        assertEquals("", state.password)
        assertFalse(state.loading)
        assertNull(state.errorMessage)
        assertFalse(state.loginSuccessful)
    }

    @Test
    fun `onEmailChanged updates state`() {
        viewModel.onEmailChanged("test@proservis.com")
        assertEquals("test@proservis.com", viewModel.uiState.value.email)
    }

    @Test
    fun `onPasswordChanged updates state`() {
        viewModel.onPasswordChanged("password123")
        assertEquals("password123", viewModel.uiState.value.password)
    }

    @Test
    fun `onLogin with empty fields shows error`() = runTest {
        viewModel.onLogin()
        
        val state = viewModel.uiState.value
        assertEquals("E-posta ve sifre zorunludur.", state.errorMessage)
    }

    @Test
    fun `onLogin successful updates state`() = runTest {
        val email = "tech@proservis.com"
        val password = "correct_password"
        val userSession = mockk<UserSession>()

        coEvery { loginUseCase(email, password) } returns Result.success(userSession)

        viewModel.onEmailChanged(email)
        viewModel.onPasswordChanged(password)

        viewModel.uiState.test {
            // Initial state (emitted upon collection)
            val initialState = awaitItem()
            assertFalse(initialState.loading)
            assertEquals(email, initialState.email)

            viewModel.onLogin()
            
            // Loading state
            val loadingState = awaitItem()
            assertTrue(loadingState.loading)

            // Success state
            val successState = awaitItem()
            assertFalse(successState.loading)
            assertTrue(successState.loginSuccessful)
        }
    }

    @Test
    fun `onLogin failure with specific error code maps correctly`() = runTest {
        val email = "tech@proservis.com"
        val password = "wrong_password"

        coEvery { 
            loginUseCase(email, password) 
        } returns Result.failure(Exception("GECERSIZ_GIRIS_BILGISI"))

        viewModel.onEmailChanged(email)
        viewModel.onPasswordChanged(password)

        viewModel.onLogin()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertFalse(state.loading)
        assertEquals("E-posta veya şifre hatalı.", state.errorMessage)
    }
}
