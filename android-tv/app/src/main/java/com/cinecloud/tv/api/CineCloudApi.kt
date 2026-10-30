package com.cinecloud.tv.api

import com.cinecloud.tv.model.*
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface CineCloudService {
    @GET("api/movies/categories")
    suspend fun getCategories(
        @Header("Authorization") token: String? = null
    ): Response<CategoriesResponse>

    @GET("api/movies")
    suspend fun getMovies(
        @Query("query") query: String? = null,
        @Query("genre") genre: String? = null,
        @Query("sort") sort: String? = "recent"
    ): Response<Map<String, Any>>

    @POST("api/progress/{movieId}")
    suspend fun updateProgress(
        @Path("movieId") movieId: Long,
        @Header("Authorization") token: String?,
        @Body request: ProgressUpdateRequest
    ): Response<Map<String, Any>>
}

object CineCloudClient {
    private var baseUrl: String = "http://10.0.2.2:8080/" // Default Android Emulator to host loopback
    private var authToken: String? = null
    private var service: CineCloudService? = null

    fun setServerUrl(url: String) {
        var cleanUrl = url.trim()
        if (!cleanUrl.endsWith("/")) {
            cleanUrl += "/"
        }
        baseUrl = cleanUrl
        service = null
    }

    fun setAuthToken(token: String?) {
        authToken = token
    }

    fun getAuthToken(): String? = authToken
    fun getBaseUrl(): String = baseUrl

    fun getService(): CineCloudService {
        if (service == null) {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            service = retrofit.create(CineCloudService::class.java)
        }
        return service!!
    }
}
