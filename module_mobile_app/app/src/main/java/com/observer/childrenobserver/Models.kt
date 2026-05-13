package com.observer.childrenobserver

import androidx.compose.ui.geometry.Offset

data class Camera(
    val id: String,
    val name: String
)

data class Alert(
    val id: String,
    val type: String,
    val time: String,
    val imageUrl: Int, // Resource ID tạm thời
    val isDangerous: Boolean? = null
)

data class RoiPolygon(
    val id: String,
    val points: List<Offset>
)
