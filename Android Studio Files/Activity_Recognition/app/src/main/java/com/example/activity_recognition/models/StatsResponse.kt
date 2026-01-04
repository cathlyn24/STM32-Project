package com.example.activity_recognition.models

data class StatsResponse(
    val status: String,
    val total_records: Int,
    val walking_count: Int,
    val running_count: Int,
    val idle_count: Int,
    val calibrating_count: Int? = 0
)