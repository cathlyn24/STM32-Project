package com.example.activity_recognition.models

data class ActivityPrediction(
    val activity: String,
    val confidence: Double,
    val timestamp: String
)