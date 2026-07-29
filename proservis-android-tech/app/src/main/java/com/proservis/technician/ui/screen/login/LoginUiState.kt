package com.proservis.technician.ui.screen.login

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val loginSuccessful: Boolean = false,
)
