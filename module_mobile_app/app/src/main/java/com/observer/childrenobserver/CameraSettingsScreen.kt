package com.observer.childrenobserver

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.observer.childrenobserver.ui.theme.ChildrenObserverTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CameraSettingsScreen(navController: NavController) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Cài đặt Camera", style = MaterialTheme.typography.titleLarge) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        val cameras = listOf(
            Camera("cam_phong_khach", "Camera phòng khách"),
            Camera("cam_hanh_lang", "Camera hành lang"),
            Camera("cam_bep", "Camera bếp"),
            Camera("cam_san_sau", "Camera sân sau")
        )

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Text(
                    text = "Chọn camera để cài đặt",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onBackground,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }
            items(cameras) { camera ->
                CameraSettingItem(
                    cameraName = camera.name,
                    onEditRoiClick = { navController.navigate("drawing_mode/${camera.id}") }
                )
            }
        }
    }
}

@Composable
fun CameraSettingItem(
    cameraName: String,
    onEditRoiClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = cameraName,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            Button(onClick = onEditRoiClick) {
                Text("Vẽ vùng ROI")
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun CameraSettingsScreenPreview() {
    ChildrenObserverTheme {
        CameraSettingsScreen(rememberNavController())
    }
}
