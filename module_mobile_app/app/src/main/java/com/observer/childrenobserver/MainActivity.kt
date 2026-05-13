package com.observer.childrenobserver

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.observer.childrenobserver.ui.theme.ChildrenObserverTheme
import com.observer.childrenobserver.ui.theme.DeepNavy
import com.observer.childrenobserver.ui.theme.LightGray
import com.observer.childrenobserver.ui.theme.SkyBlue


class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChildrenObserverTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val initialRoute = intent.getStringExtra("action")?.let { action ->
                        if (action == "view_live_stream") {
                            Screen.LiveStream.route
                        } else {
                            Screen.LiveStream.route
                        }
                    } ?: Screen.LiveStream.route

                    AppNavigation(initialRoute = initialRoute)
                }
            }
        }
    }
}

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object LiveStream : Screen("live_stream", "Trực tiếp", Icons.Default.Home)
    object AlertDashboard : Screen("alert_dashboard", "Cảnh báo", Icons.Default.List)
    object CameraSettings : Screen("camera_settings", "Cài đặt", Icons.Default.Settings)
    object DrawingMode : Screen("drawing_mode/{cameraName}", "Chế độ vẽ", Icons.Default.Settings)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppNavigation(initialRoute: String = Screen.LiveStream.route) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    val screens = listOf(
        Screen.LiveStream,
        Screen.AlertDashboard,
        Screen.CameraSettings
    )

    LaunchedEffect(key1 = initialRoute) {
        if (navController.currentBackStackEntry?.destination?.route != initialRoute) {
            navController.navigate(initialRoute) {
                popUpTo(navController.graph.startDestinationId) { saveState = true }
                launchSingleTop = true
                restoreState = true
            }
        }
    }

    val showBottomBar = screens.any { it.route == currentRoute }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(containerColor = DeepNavy) {
                    screens.forEach { screen ->
                        val selected = currentRoute == screen.route
                        NavigationBarItem(
                            icon = {
                                Icon(
                                    screen.icon,
                                    contentDescription = screen.title,
                                    tint = if (selected) SkyBlue else LightGray
                                )
                            },
                            label = {
                                Text(
                                    screen.title,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (selected) SkyBlue else LightGray
                                )
                            },
                            selected = selected,
                            onClick = {
                                if (currentRoute != screen.route) {
                                    navController.navigate(screen.route) {
                                        popUpTo(navController.graph.startDestinationId) {
                                            saveState = true
                                        }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.LiveStream.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.LiveStream.route) { LiveStreamScreen(navController) }
            composable(Screen.AlertDashboard.route) { AlertDashboardScreen(navController) }
            composable(Screen.CameraSettings.route) { CameraSettingsScreen(navController) }
            composable(
                route = Screen.DrawingMode.route,
                arguments = listOf(navArgument("cameraName") { type = NavType.StringType; nullable = true })
            ) { backStackEntry ->
                val cameraName = backStackEntry.arguments?.getString("cameraName")
                DrawingModeScreen(navController, cameraName)
            }
        }
    }
}
