package com.example.activity_recognition

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.activity_recognition.network.ApiService
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {

    private lateinit var apiService: ApiService
    private val handler = Handler(Looper.getMainLooper())
    private val updateInterval = 2000L // 2 seconds

    // UI Elements
    private lateinit var tvActivity: TextView
    private lateinit var tvActivityIcon: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvTimestamp: TextView
    private lateinit var tvTotalCount: TextView
    private lateinit var tvWalkingCount: TextView
    private lateinit var tvRunningCount: TextView
    private lateinit var tvIdleCount: TextView
    private lateinit var btnViewHistory: Button
    private lateinit var activityContainer: LinearLayout

    // Activity icons and colors
    private val activityIcons = mapOf(
        "Walking" to "🚶",
        "Running" to "🏃",
        "Idle" to "🧍",
        "Waiting for data..." to "⏳"
    )

    private val activityColors = mapOf(
        "Walking" to Color.parseColor("#4CAF50"),
        "Running" to Color.parseColor("#FF5722"),
        "Idle" to Color.parseColor("#9E9E9E"),
        "Waiting for data..." to Color.parseColor("#667eea")
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize views
        initViews()

        // Initialize API service
        apiService = ApiService.getInstance(this)

        // Set up button listeners
        btnViewHistory.setOnClickListener {
            val intent = Intent(this, HistoryActivity::class.java)
            startActivity(intent)
        }

        // Start auto-update
        startAutoUpdate()
    }

    private fun initViews() {
        tvActivity = findViewById(R.id.tvActivity)
        tvActivityIcon = findViewById(R.id.tvActivityIcon)
        tvConfidence = findViewById(R.id.tvConfidence)
        tvTimestamp = findViewById(R.id.tvTimestamp)
        tvTotalCount = findViewById(R.id.tvTotalCount)
        tvWalkingCount = findViewById(R.id.tvWalkingCount)
        tvRunningCount = findViewById(R.id.tvRunningCount)
        tvIdleCount = findViewById(R.id.tvIdleCount)
        btnViewHistory = findViewById(R.id.btnViewHistory)
        activityContainer = findViewById(R.id.activityContainer)
    }

    private fun startAutoUpdate() {
        val updateRunnable = object : Runnable {
            override fun run() {
                updateRealtimeData()
                updateStatsData()
                handler.postDelayed(this, updateInterval)
            }
        }
        handler.post(updateRunnable)
    }

    private fun updateRealtimeData() {
        apiService.getRealtimePrediction(
            onSuccess = { response ->
                runOnUiThread {
                    // Update activity
                    tvActivity.text = response.activity
                    tvActivityIcon.text = activityIcons[response.activity] ?: "❓"
                    tvConfidence.text = "Confidence: ${String.format("%.1f", response.confidence * 100)}%"

                    // Update background color
                    activityContainer.setBackgroundColor(
                        activityColors[response.activity] ?: Color.parseColor("#667eea")
                    )

                    // Format timestamp
                    try {
                        val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                        val outputFormat = SimpleDateFormat("MMM dd, HH:mm:ss", Locale.getDefault())
                        val date = inputFormat.parse(response.timestamp.substring(0, 19))
                        tvTimestamp.text = "Updated: ${outputFormat.format(date!!)}"
                    } catch (e: Exception) {
                        tvTimestamp.text = "Updated: ${response.timestamp}"
                    }
                }
            },
            onError = { error ->
                runOnUiThread {
                    Toast.makeText(this, "Error: $error", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    private fun updateStatsData() {
        apiService.getStats(
            onSuccess = { response ->
                runOnUiThread {
                    tvTotalCount.text = response.total_records.toString()
                    tvWalkingCount.text = response.walking_count.toString()
                    tvRunningCount.text = response.running_count.toString()
                    tvIdleCount.text = response.idle_count.toString()
                }
            },
            onError = { error ->
                // Silently fail for stats
            }
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
        apiService.cancelAll()
    }
}