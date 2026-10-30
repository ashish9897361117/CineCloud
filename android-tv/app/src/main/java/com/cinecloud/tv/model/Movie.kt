package com.cinecloud.tv.model

import com.google.gson.annotations.SerializedName
import java.io.Serializable

data class Movie(
    val id: Long,
    val title: String,
    val description: String?,
    @SerializedName("release_year") val releaseYear: Int,
    val genre: String?,
    val duration: Long,
    @SerializedName("poster_url") val posterUrl: String?,
    @SerializedName("backdrop_url") val backdropUrl: String?,
    @SerializedName("video_path") val videoPath: String,
    val resolution: String?,
    val rating: Double,
    @SerializedName("is_featured") val isFeatured: Int,
    val subtitles: List<Subtitle>?,
    @SerializedName("audio_tracks") val audioTracks: List<AudioTrack>?,
    @SerializedName("current_time") val currentTime: Double?,
    @SerializedName("progress_duration") val progressDuration: Double?
) : Serializable

data class Subtitle(
    val id: Long,
    val label: String,
    @SerializedName("language_code") val languageCode: String,
    @SerializedName("file_path") val filePath: String,
    @SerializedName("is_default") val isDefault: Int
) : Serializable

data class AudioTrack(
    val id: Long,
    val label: String,
    @SerializedName("language_code") val languageCode: String,
    @SerializedName("is_default") val isDefault: Int
) : Serializable

data class CategoriesResponse(
    val featured: List<Movie>?,
    @SerializedName("continue_watching") val continueWatching: List<Movie>?,
    val sections: List<CategorySection>?,
    val genres: List<String>?
)

data class CategorySection(
    val id: String,
    val title: String,
    val movies: List<Movie>
)

data class ProgressUpdateRequest(
    val currentTime: Double,
    val duration: Double,
    val isCompleted: Boolean
)
