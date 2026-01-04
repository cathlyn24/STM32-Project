package com.example.activity_recognition.models

data class RealtimeResponse(
    val status: String,
    val activity: String,
    val confidence: Double,
    val source: String? = null,
    val timestamp: String
)