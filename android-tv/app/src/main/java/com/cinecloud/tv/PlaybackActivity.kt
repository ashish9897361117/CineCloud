package com.cinecloud.tv

import android.net.Uri
import android.os.Bundle
import android.view.KeyEvent
import android.view.WindowManager
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.lifecycleScope
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.TrackSelectionOverride
import androidx.media3.common.Tracks
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.cinecloud.tv.api.CineCloudClient
import com.cinecloud.tv.model.Movie
import com.cinecloud.tv.model.ProgressUpdateRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class PlaybackActivity : FragmentActivity() {

    companion object {
        const val EXTRA_MOVIE = "extra_movie"
    }

    private var player: ExoPlayer? = null
    private lateinit var playerView: PlayerView
    private var movie: Movie? = null
    private var progressSyncJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContentView(R.layout.activity_playback)

        playerView = findViewById(R.id.tv_player_view)
        movie = intent.getSerializableExtra(EXTRA_MOVIE) as? Movie

        initializePlayer()
    }

    private fun initializePlayer() {
        val currentMovie = movie ?: return

        player = ExoPlayer.Builder(this).build().apply {
            playerView.player = this

            // Build stream URI
            var videoUriString = currentMovie.videoPath
            if (!videoUriString.startsWith("http")) {
                videoUriString = CineCloudClient.getBaseUrl() + "api/stream/" + currentMovie.id
                val token = CineCloudClient.getAuthToken()
                if (token != null) {
                    videoUriString += "?token=$token"
                }
            }

            val mediaItemBuilder = MediaItem.Builder()
                .setUri(Uri.parse(videoUriString))

            // Attach external subtitle track if provided
            currentMovie.subtitles?.firstOrNull()?.let { sub ->
                var subUri = sub.filePath
                if (!subUri.startsWith("http")) {
                    subUri = CineCloudClient.getBaseUrl() + sub.filePath.trimStart('/')
                }
                val subtitleConfig = MediaItem.SubtitleConfiguration.Builder(Uri.parse(subUri))
                    .setMimeType(androidx.media3.common.MimeTypes.TEXT_VTT)
                    .setLanguage(sub.languageCode)
                    .setSelectionFlags(C.SELECTION_FLAG_DEFAULT)
                    .build()
                mediaItemBuilder.setSubtitleConfigurations(listOf(subtitleConfig))
            }

            setMediaItem(mediaItemBuilder.build())

            // Resume watching if saved progress exists
            val resumeSeconds = currentMovie.currentTime ?: 0.0
            if (resumeSeconds > 15) {
                seekTo((resumeSeconds * 1000).toLong())
            }

            prepare()
            playWhenReady = true

            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(playbackState: Int) {
                    if (playbackState == Player.STATE_ENDED) {
                        saveProgress(isCompleted = true)
                    }
                }
            })
        }

        startProgressSync()
    }

    private fun startProgressSync() {
        progressSyncJob?.cancel()
        progressSyncJob = lifecycleScope.launch {
            while (isActive) {
                delay(10_000) // sync every 10s
                saveProgress(isCompleted = false)
            }
        }
    }

    private fun saveProgress(isCompleted: Boolean) {
        val p = player ?: return
        val currentMovie = movie ?: return
        val token = CineCloudClient.getAuthToken() ?: return
        val durationSec = p.duration / 1000.0
        val currentSec = p.currentPosition / 1000.0

        if (durationSec <= 0) return

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                CineCloudClient.getService().updateProgress(
                    movieId = currentMovie.id,
                    token = "Bearer $token",
                    request = ProgressUpdateRequest(
                        currentTime = currentSec,
                        duration = durationSec,
                        isCompleted = isCompleted
                    )
                )
            } catch (e: Exception) {
                // Background sync ignore
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        val p = player ?: return super.onKeyDown(keyCode, event)

        return when (keyCode) {
            KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE -> {
                if (p.isPlaying) p.pause() else p.play()
                true
            }
            KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.KEYCODE_MEDIA_REWIND -> {
                p.seekTo(Math.max(0, p.currentPosition - 10_000))
                true
            }
            KeyEvent.KEYCODE_DPAD_RIGHT, KeyEvent.KEYCODE_MEDIA_FAST_FORWARD -> {
                p.seekTo(Math.min(p.duration, p.currentPosition + 10_000))
                true
            }
            KeyEvent.KEYCODE_BACK -> {
                saveProgress(isCompleted = false)
                finish()
                true
            }
            else -> super.onKeyDown(keyCode, event)
        }
    }

    override fun onStop() {
        super.onStop()
        saveProgress(isCompleted = false)
        progressSyncJob?.cancel()
        player?.release()
        player = null
    }
}
