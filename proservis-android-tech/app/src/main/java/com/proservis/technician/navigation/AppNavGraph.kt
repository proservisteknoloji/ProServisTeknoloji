package com.proservis.technician.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.proservis.technician.ui.screen.login.LoginRoute
import com.proservis.technician.ui.screen.complete.CompleteServiceRoute
import com.proservis.technician.ui.screen.verify.SerialVerifyRoute
import com.proservis.technician.ui.screen.work.WorkTabsRoute

@Composable
fun AppNavGraph(
    navViewModel: AppNavViewModel = hiltViewModel(),
    notificationTarget: AppNotificationTarget? = null,
    onNotificationHandled: () -> Unit = {},
) {
    val navController = rememberNavController()
    val startRoute by navViewModel.startRoute.collectAsState()
    val bootCompleted by navViewModel.bootCompleted.collectAsState()
    var pendingNotification by remember { mutableStateOf<AppNotificationTarget?>(null) }
    var activeNotification by remember { mutableStateOf<AppNotificationTarget?>(null) }

    if (!bootCompleted) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LaunchedEffect(notificationTarget) {
        if (notificationTarget != null) {
            pendingNotification = notificationTarget
        }
    }

    NavHost(
        navController = navController,
        startDestination = startRoute,
    ) {
        composable(AppRoute.Login) {
            LoginRoute(
                onLoginSuccess = {
                    navController.navigate(AppRoute.WorkTabs) {
                        popUpTo(AppRoute.Login) { inclusive = true }
                    }
                },
            )
        }
        composable(AppRoute.WorkTabs) {
            WorkTabsRoute(
                notificationTarget = activeNotification,
                onNotificationConsumed = {
                    activeNotification = null
                    onNotificationHandled()
                },
                onNavigateSerialVerify = { serviceId ->
                    navController.navigate(AppRoute.serialVerify(serviceId))
                },
                onNavigateCompleteService = { serviceId ->
                    navController.navigate(AppRoute.completeService(serviceId))
                },
            )
        }
        composable(
            route = AppRoute.SerialVerify,
            arguments = listOf(navArgument("serviceId") { type = NavType.StringType }),
        ) {
            SerialVerifyRoute(
                onSuccess = { serviceId ->
                    navController.navigate(AppRoute.completeService(serviceId)) {
                        popUpTo(AppRoute.SerialVerify) { inclusive = true }
                    }
                },
                onBack = { navController.popBackStack() },
            )
        }
        composable(
            route = AppRoute.CompleteService,
            arguments = listOf(navArgument("serviceId") { type = NavType.StringType }),
        ) {
            CompleteServiceRoute(
                onSuccess = { navController.popBackStack() },
                onBack = { navController.popBackStack() },
            )
        }
    }

    LaunchedEffect(pendingNotification, startRoute, bootCompleted) {
        val target = pendingNotification ?: return@LaunchedEffect
        if (!bootCompleted) return@LaunchedEffect
        if (startRoute == AppRoute.Login) return@LaunchedEffect

        activeNotification = target
        navController.navigate(AppRoute.WorkTabs) {
            popUpTo(AppRoute.WorkTabs) { inclusive = false }
            launchSingleTop = true
        }
        pendingNotification = null
    }
}
