package com.example.activity_recognition.models

data class UploadResponse(
    val status: String,
    val message: String,
    val activity_detected: String? = null,
    val magnitude: Double? = null
)