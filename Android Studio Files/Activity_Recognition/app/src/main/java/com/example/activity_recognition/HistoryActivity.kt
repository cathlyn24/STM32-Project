package com.example.activity_recognition

import androidx.core.graphics.toColorInt
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.example.activity_recognition.models.ActivityPrediction
import com.example.activity_recognition.network.ApiService
import java.text.SimpleDateFormat
import java.util.*

class HistoryActivity : AppCompatActivity() {

    private lateinit var apiService: ApiService
    private lateinit var recyclerView: RecyclerView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var adapter: HistoryAdapter
    private var currentHours = 24

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history)

        // Enable back button
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Activity History"

        apiService = ApiService.getInstance(this)

        // Initialize views
        recyclerView = findViewById(R.id.recyclerHistory)
        swipeRefresh = findViewById(R.id.swipeRefresh)

        // Set up RecyclerView
        adapter = HistoryAdapter()
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter

        // Set up swipe refresh
        swipeRefresh.setOnRefreshListener {
            loadHistory(currentHours)
        }

        // Set up filter buttons
        findViewById<Button>(R.id.btn1Hour).setOnClickListener { loadHistory(1) }
        findViewById<Button>(R.id.btn6Hours).setOnClickListener { loadHistory(6) }
        findViewById<Button>(R.id.btn24Hours).setOnClickListener { loadHistory(24) }
        findViewById<Button>(R.id.btn1Week).setOnClickListener { loadHistory(168) }

        // Load initial data
        loadHistory(24)
    }

    private fun loadHistory(hours: Int) {
        currentHours = hours
        swipeRefresh.isRefreshing = true

        apiService.getHistory(
            hours = hours,
            limit = 100,
            onSuccess = { response ->
                runOnUiThread {
                    adapter.updateData(response.records)
                    swipeRefresh.isRefreshing = false

                    if (response.records.isEmpty()) {
                        Toast.makeText(this, "No records found", Toast.LENGTH_SHORT).show()
                    }
                }
            },
            onError = { error ->
                runOnUiThread {
                    Toast.makeText(this, "Error: $error", Toast.LENGTH_SHORT).show()
                    swipeRefresh.isRefreshing = false
                }
            }
        )
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    override fun onDestroy() {
        super.onDestroy()
        apiService.cancelAll()
    }
}

// Adapter for RecyclerView
class HistoryAdapter : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

    private var records: List<ActivityPrediction> = emptyList()

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvActivity: TextView = view.findViewById(R.id.tvItemActivity)
        val tvConfidence: TextView = view.findViewById(R.id.tvItemConfidence)
        val tvTimestamp: TextView = view.findViewById(R.id.tvItemTimestamp)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val record = records[position]

        holder.tvActivity.text = record.activity

        // Format confidence percentage
        val confidenceValue = String.format(Locale.getDefault(), "%.1f", record.confidence * 100)
        holder.tvConfidence.text = holder.itemView.context.getString(
            R.string.confidence_percentage,
            confidenceValue
        )

        // Format timestamp
        try {
            val inputFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            val outputFormat = SimpleDateFormat("MMM dd, HH:mm:ss", Locale.getDefault())
            val date = inputFormat.parse(record.timestamp.take(19))
            holder.tvTimestamp.text = outputFormat.format(date!!)
        } catch (_: Exception) {
            // If parsing fails, display original timestamp
            holder.tvTimestamp.text = record.timestamp
        }

        // Set color based on activity
        val color = when (record.activity) {
            "Walking" -> "#4CAF50".toColorInt()
            "Running" -> "#FF5722".toColorInt()
            "Idle" -> "#9E9E9E".toColorInt()
            else -> "#667eea".toColorInt()
        }
        holder.tvActivity.setTextColor(color)
        holder.tvConfidence.setTextColor(color)
    }

    override fun getItemCount() = records.size

    fun updateData(newRecords: List<ActivityPrediction>) {
        records = newRecords
        notifyDataSetChanged()
    }
}