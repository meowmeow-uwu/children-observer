package com.observer.childrenobserver

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Undo
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.ClipOp
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.observer.childrenobserver.ui.theme.ChildrenObserverTheme
import com.observer.childrenobserver.ui.theme.EmergencyRed
import com.observer.childrenobserver.ui.theme.SkyBlue
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DrawingModeScreen(navController: NavController, cameraName: String?) {
    var points by remember { mutableStateOf(listOf<Offset>()) }
    val undoStack = remember { mutableStateListOf<List<Offset>>() }
    val coroutineScope = rememberCoroutineScope()

    // Trạng thái cho việc kéo điểm
    var draggingPointIndex by remember { mutableStateOf(-1) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Vẽ vùng ROI cho ${cameraName ?: "Camera"}", style = MaterialTheme.typography.titleLarge) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                ),
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Quay lại", tint = MaterialTheme.colorScheme.onPrimary)
                    }
                }
            )
        },
        bottomBar = {
            BottomAppBar(
                containerColor = MaterialTheme.colorScheme.surface
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                    horizontalArrangement = Arrangement.SpaceAround,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Nút Hoàn tác (Undo)
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                if (undoStack.isNotEmpty()) {
                                    points = undoStack.removeLast()
                                } else {
                                    points = emptyList()
                                }
                            }
                        },
                        enabled = undoStack.isNotEmpty() || points.isNotEmpty(),
                        modifier = Modifier.weight(1f).padding(horizontal = 4.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = SkyBlue)
                    ) {
                        Icon(Icons.Default.Undo, contentDescription = "Hoàn tác")
                    }

                    // Nút Xóa vùng (Clear)
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                if (points.isNotEmpty()) {
                                    undoStack.add(points.toList()) // Lưu trạng thái hiện tại trước khi xóa
                                }
                                points = emptyList()
                            }
                        },
                        enabled = points.isNotEmpty(),
                        modifier = Modifier.weight(1f).padding(horizontal = 4.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = EmergencyRed)
                    ) {
                        Icon(Icons.Default.Clear, contentDescription = "Xóa vùng")
                    }

                    // Nút Lưu (Save)
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                println("Lưu ROI cho ${cameraName ?: "Unknown Camera"}: $points")
                                // TODO: Gửi các điểm ROI đến backend hoặc lưu cục bộ
                                navController.popBackStack() // Quay lại màn hình trước đó
                            }
                        },
                        enabled = points.size >= 3, // Cần ít nhất 3 điểm để tạo đa giác hợp lệ
                        modifier = Modifier.weight(1f).padding(horizontal = 4.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.tertiary)
                    ) {
                        Icon(Icons.Default.Save, contentDescription = "Lưu")
                    }
                }
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .background(MaterialTheme.colorScheme.background)
        ) {
            // (a) Khu vực video player (placeholder)
            Box(modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f) // Tỷ lệ 16:9 cho video
                .background(Color.Black)
                .align(Alignment.Center)
            ) {
                Text(
                    "Video Player (Drawing Mode)",
                    color = Color.White.copy(alpha = 0.7f),
                    modifier = Modifier.align(Alignment.Center)
                )

                // (b) Hiển thị lưới (grid) hỗ trợ căn chỉnh
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val gridSize = 50.dp.toPx()
                    var x = 0f
                    while (x < size.width) {
                        drawLine(Color.Gray.copy(alpha = 0.3f), Offset(x, 0f), Offset(x, size.height))
                        x += gridSize
                    }
                    var y = 0f
                    while (y < size.height) {
                        drawLine(Color.Gray.copy(alpha = 0.3f), Offset(0f, y), Offset(size.width, y))
                        y += gridSize
                    }
                }
            }

            // (c) Lớp phủ Canvas để vẽ ROI và xử lý tương tác
            Canvas(modifier = Modifier
                .fillMaxSize()
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = { offset ->
                            // Thêm điểm mới khi chạm (nếu không đang kéo điểm)
                            if (draggingPointIndex == -1) {
                                undoStack.add(points.toList())
                                points = points + offset
                            }
                        }
                    )
                }
                .pointerInput(points) { // Bắt buộc recomposition và re-bind gesture khi points thay đổi
                    detectDragGestures(
                        onDragStart = { startOffset ->
                            // Tìm điểm gần nhất để kéo (vùng nhạy cảm 20dp)
                            draggingPointIndex = points.indexOfFirst { point ->
                                (point - startOffset).getDistance() < 20.dp.toPx()
                            }
                            if (draggingPointIndex != -1) {
                                undoStack.add(points.toList()) // Lưu trạng thái trước khi kéo
                            }
                        },
                        onDragEnd = { draggingPointIndex = -1 },
                        onDragCancel = { draggingPointIndex = -1 },
                        onDrag = { change, dragAmount ->
                            if (draggingPointIndex != -1) {
                                val currentPoints = points.toMutableList()
                                val currentPoint = currentPoints[draggingPointIndex]
                                currentPoints[draggingPointIndex] = currentPoint + dragAmount
                                points = currentPoints
                            }
                        }
                    )
                }
            ) {
                // Xây dựng đường dẫn (Path) của đa giác
                val roiPath = Path()
                if (points.isNotEmpty()) {
                    roiPath.moveTo(points.first().x, points.first().y)
                    points.drop(1).forEach { point ->
                        roiPath.lineTo(point.x, point.y)
                    }
                    if (points.size >= 3) {
                        roiPath.close() // Chỉ đóng Path khi có từ 3 điểm trở lên để tạo thành vùng khép kín
                    }
                }

                // Vẽ hiệu ứng làm tối vùng bên ngoài (Sử dụng clipPath)
                if (points.size >= 3) {
                    // ClipOp.Difference sẽ loại trừ phần roiPath ra khỏi vùng vẽ hiện tại
                    clipPath(path = roiPath, clipOp = ClipOp.Difference) {
                        drawRect(color = Color.Black.copy(alpha = 0.6f), style = Fill)
                    }
                } else {
                    // Nếu chưa đủ tạo vùng khép kín, chỉ phủ một lớp tối mờ nhẹ toàn màn hình
                    drawRect(color = Color.Black.copy(alpha = 0.2f), style = Fill)
                }

                // Vẽ đường viền của đa giác đang vẽ
                if (points.size >= 2) {
                    drawPath(
                        path = roiPath,
                        color = SkyBlue,
                        style = Stroke(width = 4.dp.toPx())
                    )
                }

                // Vẽ các điểm (vertices)
                points.forEachIndexed { index, point ->
                    drawCircle(color = SkyBlue, radius = 10.dp.toPx(), center = point)
                    drawCircle(color = Color.White, radius = 5.dp.toPx(), center = point)
                    // Highlight điểm đang được kéo
                    if (index == draggingPointIndex) {
                        drawCircle(
                            color = EmergencyRed,
                            radius = 12.dp.toPx(),
                            center = point,
                            style = Stroke(width = 2.dp.toPx())
                        )
                    }
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun DrawingModeScreenPreview() {
    ChildrenObserverTheme {
        DrawingModeScreen(rememberNavController(), "Camera phòng khách")
    }
}