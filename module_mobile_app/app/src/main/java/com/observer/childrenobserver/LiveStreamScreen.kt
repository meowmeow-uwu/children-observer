package com.observer.childrenobserver

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.observer.childrenobserver.ui.theme.ChildrenObserverTheme
import com.observer.childrenobserver.ui.theme.SkyBlue

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LiveStreamScreen(navController: NavController) {
    var expanded by remember { mutableStateOf(false) }
    val cameras = remember {
        listOf(
            Camera("cam_phong_khach", "Camera phòng khách"),
            Camera("cam_hanh_lang", "Camera hành lang"),
            Camera("cam_bep", "Camera bếp")
        )
    }
    var selectedCamera by remember { mutableStateOf(cameras[0]) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(start = 8.dp)
                    ) {
                        Text(text = selectedCamera.name)
                        IconButton(onClick = { expanded = true }) {
                            Icon(Icons.Filled.ArrowDropDown, contentDescription = "Chọn camera")
                        }
                        DropdownMenu(
                            expanded = expanded,
                            onDismissRequest = { expanded = false }
                        ) {
                            cameras.forEach { camera ->
                                DropdownMenuItem(
                                    text = { Text(camera.name) },
                                    onClick = {
                                        selectedCamera = camera
                                        expanded = false
                                        println("Streaming từ: ${camera.id}")
                                    }
                                )
                            }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background)
        ) {
            // Video Player Area
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(16f / 9f)
                    .background(Color.Black)
                    .align(Alignment.TopCenter)
            ) {
                Text(
                    "Đang truyền tải WebRTC...",
                    color = Color.White.copy(alpha = 0.5f),
                    modifier = Modifier.align(Alignment.Center)
                )

                // ROI Overlay Placeholder
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .graphicsLayer(alpha = 0.2f)
                        .background(SkyBlue)
                )
            }

            // Floating Controls
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 32.dp, start = 16.dp, end = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                FloatingActionButton(
                    onClick = { println("Mic ON") },
                    containerColor = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Filled.Mic, "Đàm thoại")
                }

                FloatingActionButton(
                    onClick = { println("Chụp ảnh") },
                    containerColor = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Filled.PhotoCamera, "Chụp ảnh")
                }

                FloatingActionButton(
                    onClick = { println("Ghi hình") },
                    containerColor = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Filled.Videocam, "Ghi hình")
                }
            }
        }
    }
}

@Preview
@Composable
fun LiveStreamPreview() {
    ChildrenObserverTheme {
        LiveStreamScreen(rememberNavController())
    }
}
