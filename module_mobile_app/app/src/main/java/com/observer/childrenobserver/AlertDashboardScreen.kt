package com.observer.childrenobserver

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.observer.childrenobserver.ui.theme.ChildrenObserverTheme
import com.observer.childrenobserver.ui.theme.DeepNavy
import com.observer.childrenobserver.ui.theme.EmergencyRed
import com.observer.childrenobserver.ui.theme.SkyBlue

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertDashboardScreen(navController: NavController) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dashboard Cảnh báo", style = MaterialTheme.typography.titleLarge) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        // Sử dụng model Alert từ Models.kt
        val sampleAlerts = listOf(
            Alert("1", "Xâm nhập", "10 phút trước", android.R.drawable.ic_menu_report_image),
            Alert("2", "Té ngã", "Hôm nay, 14:30", android.R.drawable.ic_menu_report_image),
            Alert("3", "Bạo lực", "Hôm nay, 10:00", android.R.drawable.ic_menu_report_image),
            Alert("4", "Xâm nhập", "Hôm qua, 20:15", android.R.drawable.ic_menu_report_image),
            Alert("5", "Té ngã", "22/10/2023, 10:15", android.R.drawable.ic_menu_report_image),
        )

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(sampleAlerts) { alert ->
                AlertCard(
                    alert = alert,
                    onViewVideoClick = { println("Xem video clip: ${alert.id}") },
                    onConfirmDangerousClick = { println("Xác nhận nguy hiểm: ${alert.id}") },
                    onFalseAlarmClick = { println("Báo động sai: ${alert.id}") }
                )
            }
        }
    }
}

@Composable
fun AlertCard(
    alert: Alert,
    onViewVideoClick: () -> Unit,
    onConfirmDangerousClick: () -> Unit,
    onFalseAlarmClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .border(2.dp, EmergencyRed, RoundedCornerShape(8.dp))
                ) {
                    Image(
                        painter = painterResource(id = alert.imageUrl),
                        contentDescription = "Thumbnail",
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                }

                Spacer(modifier = Modifier.width(16.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = alert.type,
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = EmergencyRed
                    )
                    Text(
                        text = alert.time,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }

                IconButton(onClick = onViewVideoClick) {
                    Icon(
                        Icons.Filled.PlayArrow,
                        contentDescription = "Xem Video",
                        tint = SkyBlue,
                        modifier = Modifier.size(36.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                Button(
                    onClick = onConfirmDangerousClick,
                    colors = ButtonDefaults.buttonColors(containerColor = EmergencyRed),
                    modifier = Modifier.weight(1f).padding(end = 8.dp)
                ) {
                    Text("Nguy hiểm", color = Color.White)
                }

                OutlinedButton(
                    onClick = onFalseAlarmClick,
                    modifier = Modifier.weight(1f).padding(start = 8.dp),
                    border = ButtonDefaults.outlinedButtonBorder.copy(brush = SolidColor(DeepNavy))
                ) {
                    Text("Báo động sai", color = DeepNavy)
                }
            }
        }
    }
}
