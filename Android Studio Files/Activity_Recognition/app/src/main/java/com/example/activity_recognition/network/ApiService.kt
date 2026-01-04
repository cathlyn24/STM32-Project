package com.example.activity_recognition.network

import android.content.Context
import com.android.volley.Request
import com.android.volley.RequestQueue
import com.android.volley.toolbox.StringRequest
import com.android.volley.toolbox.Volley
import com.example.activity_recognition.models.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class ApiService private constructor(context: Context) {

    companion object {
        private const val BASE_URL = "http://cathlynramo.pythonanywhere.com"

        @Volatile
        private var instance: ApiService? = null

        fun getInstance(context: Context): ApiService {
            return instance ?: synchronized(this) {
                instance ?: ApiService(context.applicationContext).also { instance = it }
            }
        }
    }

    private val requestQueue: RequestQueue = Volley.newRequestQueue(context.applicationContext)
    private val gson = Gson()

    /**
     * Get real-time prediction
     */
    fun getRealtimePrediction(
        onSuccess: (RealtimeResponse) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$BASE_URL/api/realtime"

        val request = StringRequest(
            Request.Method.GET, url,
            { response ->
                try {
                    val data = gson.fromJson(response, RealtimeResponse::class.java)
                    onSuccess(data)
                } catch (e: Exception) {
                    onError("Parse error: ${e.message}")
                }
            },
            { error ->
                onError("Network error: ${error.message ?: "Unknown error"}")
            }
        )

        requestQueue.add(request)
    }

    /**
     * Get activity history
     */
    fun getHistory(
        hours: Int,
        limit: Int,
        onSuccess: (HistoryResponse) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$BASE_URL/api/history?hours=$hours&limit=$limit"

        val request = StringRequest(
            Request.Method.GET, url,
            { response ->
                try {
                    val data = gson.fromJson(response, HistoryResponse::class.java)
                    onSuccess(data)
                } catch (e: Exception) {
                    onError("Parse error: ${e.message}")
                }
            },
            { error ->
                onError("Network error: ${error.message ?: "Unknown error"}")
            }
        )

        requestQueue.add(request)
    }

    /**
     * Get statistics
     */
    fun getStats(
        onSuccess: (StatsResponse) -> Unit,
        onError: (String) -> Unit
    ) {
        val url = "$BASE_URL/api/stats"

        val request = StringRequest(
            Request.Method.GET, url,
            { response ->
                try {
                    val data = gson.fromJson(response, StatsResponse::class.java)
                    onSuccess(data)
                } catch (e: Exception) {
                    onError("Parse error: ${e.message}")
                }
            },
            { error ->
                onError("Network error: ${error.message ?: "Unknown error"}")
            }
        )

        requestQueue.add(request)
    }

    /**
     * Cancel all pending requests
     */
    fun cancelAll() {
        requestQueue.cancelAll { true }
    }
}