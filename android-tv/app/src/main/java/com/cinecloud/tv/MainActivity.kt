package com.cinecloud.tv

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.leanback.app.BackgroundManager
import androidx.leanback.app.BrowseSupportFragment
import androidx.leanback.widget.*
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.bumptech.glide.request.target.CustomTarget
import com.bumptech.glide.request.transition.Transition
import com.cinecloud.tv.api.CineCloudClient
import com.cinecloud.tv.model.Movie
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : FragmentActivity() {

    private lateinit var backgroundManager: BackgroundManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        backgroundManager = BackgroundManager.getInstance(this).apply {
            attach(window)
        }

        // Restore saved server URL & Token
        val prefs = getSharedPreferences("cinecloud_prefs", Context.MODE_PRIVATE)
        val savedServer = prefs.getString("server_url", "http://10.0.2.2:8080/") ?: "http://10.0.2.2:8080/"
        val savedToken = prefs.getString("auth_token", null)
        CineCloudClient.setServerUrl(savedServer)
        CineCloudClient.setAuthToken(savedToken)

        if (savedInstanceState == null) {
            val fragment = MainBrowseFragment()
            supportFragmentManager.beginTransaction()
                .replace(R.id.main_browse_fragment, fragment)
                .commit()
        }
    }
}

class MainBrowseFragment : BrowseSupportFragment() {

    private lateinit var rowsAdapter: ArrayObjectAdapter

    override fun onActivityCreated(savedInstanceState: Bundle?) {
        super.onActivityCreated(savedInstanceState)

        setupUIElements()
        setupEventListeners()
        loadCategories()
    }

    private fun setupUIElements() {
        title = "CineCloud 🎬"
        headersState = HEADERS_ENABLED
        isHeadersTransitionOnBackEnabled = true
        brandColor = ContextCompat.getColor(requireContext(), R.color.brand_primary)
        searchAffordanceColor = ContextCompat.getColor(requireContext(), R.color.accent_cyan)
    }

    private fun setupEventListeners() {
        setOnSearchClickedListener {
            showServerConfigDialog()
        }

        onItemViewClickedListener = OnItemViewClickedListener { _, item, _, _ ->
            if (item is Movie) {
                val intent = Intent(requireContext(), PlaybackActivity::class.java).apply {
                    putExtra(PlaybackActivity.EXTRA_MOVIE, item)
                }
                startActivity(intent)
            }
        }

        onItemViewSelectedListener = OnItemViewSelectedListener { _, item, _, _ ->
            if (item is Movie && !item.backdropUrl.isNullOrEmpty()) {
                updateBackground(item.backdropUrl)
            }
        }
    }

    private fun updateBackground(uri: String) {
        val bgManager = BackgroundManager.getInstance(requireActivity())
        Glide.with(requireContext())
            .load(uri)
            .centerCrop()
            .into(object : CustomTarget<Drawable>() {
                override fun onResourceReady(resource: Drawable, transition: Transition<in Drawable>?) {
                    bgManager.drawable = resource
                }
                override fun onLoadCleared(placeholder: Drawable?) {}
            })
    }

    fun loadCategories() {
        val cardPresenter = MovieCardPresenter()
        rowsAdapter = ArrayObjectAdapter(ListRowPresenter())

        lifecycleScope.launch {
            try {
                val token = CineCloudClient.getAuthToken()
                val authHeader = if (token != null) "Bearer $token" else null
                val response = withContext(Dispatchers.IO) {
                    CineCloudClient.getService().getCategories(authHeader)
                }

                if (response.isSuccessful && response.body() != null) {
                    val catData = response.body()!!

                    // 1. Continue Watching
                    catData.continueWatching?.let { movies ->
                        if (movies.isNotEmpty()) {
                            val listRowAdapter = ArrayObjectAdapter(cardPresenter).apply {
                                addAll(0, movies)
                            }
                            val header = HeaderItem(0, "Continue Watching")
                            rowsAdapter.add(ListRow(header, listRowAdapter))
                        }
                    }

                    // 2. Featured
                    catData.featured?.let { movies ->
                        if (movies.isNotEmpty()) {
                            val listRowAdapter = ArrayObjectAdapter(cardPresenter).apply {
                                addAll(0, movies)
                            }
                            val header = HeaderItem(1, "Featured Spotlights")
                            rowsAdapter.add(ListRow(header, listRowAdapter))
                        }
                    }

                    // 3. Category Sections
                    catData.sections?.forEachIndexed { index, section ->
                        if (section.movies.isNotEmpty()) {
                            val listRowAdapter = ArrayObjectAdapter(cardPresenter).apply {
                                addAll(0, section.movies)
                            }
                            val header = HeaderItem((index + 2).toLong(), section.title)
                            rowsAdapter.add(ListRow(header, listRowAdapter))
                        }
                    }

                    adapter = rowsAdapter
                }
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Connect error: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun showServerConfigDialog() {
        val input = EditText(requireContext()).apply {
            setText(CineCloudClient.getBaseUrl())
        }

        AlertDialog.Builder(requireContext())
            .setTitle("CineCloud Server URL")
            .setMessage("Enter the IP / domain of your CineCloud streaming server:")
            .setView(input)
            .setPositiveButton("Connect") { _, _ ->
                val newUrl = input.text.toString()
                CineCloudClient.setServerUrl(newUrl)
                val prefs = requireContext().getSharedPreferences("cinecloud_prefs", Context.MODE_PRIVATE)
                prefs.edit().putString("server_url", newUrl).apply()
                loadCategories()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}

class MovieCardPresenter : Presenter() {
    override fun onCreateViewHolder(parent: ViewGroup): ViewHolder {
        val cardView = ImageCardView(parent.context).apply {
            isFocusable = true
            isFocusableInTouchMode = true
            setBackgroundColor(Color.parseColor("#121826"))
            setMainImageDimensions(310, 460)
        }
        return ViewHolder(cardView)
    }

    override fun onBindViewHolder(viewHolder: ViewHolder, item: Any) {
        val movie = item as Movie
        val cardView = viewHolder.view as ImageCardView

        cardView.titleText = movie.title
        cardView.contentText = "${movie.releaseYear} • ${movie.resolution ?: "1080p"} • ★ ${movie.rating}"

        Glide.with(viewHolder.view.context)
            .load(movie.posterUrl)
            .centerCrop()
            .into(cardView.mainImageView)
    }

    override fun onUnbindViewHolder(viewHolder: ViewHolder) {
        val cardView = viewHolder.view as ImageCardView
        cardView.badgeImage = null
        cardView.mainImage = null
    }
}
