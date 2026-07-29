package com.proservis.technician.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.proservis.technician.data.session.SessionStore
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppNavViewModel @Inject constructor(
    private val sessionStore: SessionStore,
) : ViewModel() {

    private val _bootCompleted = MutableStateFlow(false)
    val bootCompleted: StateFlow<Boolean> = _bootCompleted.asStateFlow()

    private val _startRoute = MutableStateFlow(AppRoute.Login)
    val startRoute: StateFlow<String> = _startRoute.asStateFlow()

    private var hasCheckedFreshInstall = false

    init {
        viewModelScope.launch {
            sessionStore.sessionFlow.collect { session ->
                val authUser = com.google.firebase.auth.FirebaseAuth.getInstance().currentUser
                if (!hasCheckedFreshInstall && session == null && authUser != null) {
                    hasCheckedFreshInstall = true
                    runCatching { com.google.firebase.auth.FirebaseAuth.getInstance().signOut() }
                    _startRoute.update { AppRoute.Login }
                    _bootCompleted.update { true }
                    return@collect
                }
                hasCheckedFreshInstall = true
                _startRoute.update { if (session == null || authUser == null) AppRoute.Login else AppRoute.WorkTabs }
                _bootCompleted.update { true }
            }
        }
    }
}

