/**
 * CineCloud Main Application Controller
 * Handles Discovery, Library, Search, Authentication, Modals, and TV Pairing
 */

class CineApp {
  constructor() {
    this.currentUser = null;
    this.cachedCategories = null;
    this.searchDebounceTimer = null;

    // DOM Elements
    this.homeView = document.getElementById("homeView");
    this.libraryView = document.getElementById("libraryView");
    this.adminView = document.getElementById("adminView");
    this.downloadView = document.getElementById("downloadView");
    this.railsContainer = document.getElementById("railsContainer");
    this.searchInput = document.getElementById("searchInput");
    this.genreFilter = document.getElementById("genreFilter");
    this.sortFilter = document.getElementById("sortFilter");
    this.libraryGrid = document.getElementById("libraryGrid");
    this.tvModeBtn = document.getElementById("tvModeBtn");
    this.authActions = document.getElementById("authActions");
    this.movieModal = document.getElementById("movieModal");
    this.closeModalBtn = document.getElementById("closeModalBtn");
    this.authModal = document.getElementById("authModal");
    this.closeAuthModalBtn = document.getElementById("closeAuthModalBtn");
    this.authForm = document.getElementById("authForm");
    this.tvPairModal = document.getElementById("tvPairModal");
    this.closeTvPairBtn = document.getElementById("closeTvPairBtn");
    this.toastNotice = document.getElementById("toastNotice");

    this.init();
  }

  async init() {
    this.bindEvents();
    await this.checkAuth();
    await this.loadCategories();
    this.handleRouting();

    // Check if URL specifies #tv mode
    if (window.location.hash.includes("tv")) {
      window.tvNav.enableTvMode();
    }
  }

  bindEvents() {
    // Hash Routing
    window.addEventListener("hashchange", () => this.handleRouting());

    // Header scroll background effect
    window.addEventListener("scroll", () => {
      const header = document.getElementById("mainHeader");
      if (window.scrollY > 40) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    });

    // TV Mode Toggle
    this.tvModeBtn.addEventListener("click", () => {
      window.tvNav.toggleTvMode();
    });

    // Search Input
    this.searchInput.addEventListener("input", (e) => {
      clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        const query = e.target.value.trim();
        if (query) {
          window.location.hash = "#library";
          this.loadLibrary(query);
        } else {
          this.loadLibrary("");
        }
      }, 300);
    });

    // Filter selects
    this.genreFilter.addEventListener("change", () => this.loadLibrary(this.searchInput.value));
    this.sortFilter.addEventListener("change", () => this.loadLibrary(this.searchInput.value));

    // Modals Close
    this.closeModalBtn.addEventListener("click", () => this.movieModal.classList.remove("open"));
    this.movieModal.addEventListener("click", (e) => {
      if (e.target === this.movieModal) this.movieModal.classList.remove("open");
    });

    this.closeAuthModalBtn.addEventListener("click", () => this.authModal.classList.remove("open"));
    this.authModal.addEventListener("click", (e) => {
      if (e.target === this.authModal) this.authModal.classList.remove("open");
    });

    this.closeTvPairBtn.addEventListener("click", () => this.tvPairModal.classList.remove("open"));

    // Auth Form Submit
    this.authForm.addEventListener("submit", (e) => this.handleAuthSubmit(e));
  }

  handleRouting() {
    const hash = window.location.hash || "#home";
    const navLinks = document.querySelectorAll(".nav-link");
    navLinks.forEach(link => {
      link.classList.toggle("active", link.getAttribute("href") === hash);
    });

    this.homeView.style.display = "none";
    this.libraryView.style.display = "none";
    this.adminView.style.display = "none";
    if (this.downloadView) this.downloadView.style.display = "none";

    if (hash === "#library") {
      this.libraryView.style.display = "block";
      this.loadLibrary(this.searchInput.value);
    } else if (hash === "#admin") {
      this.adminView.style.display = "block";
      window.cineAdmin.loadAdminMovies();
    } else if (hash === "#download") {
      if (this.downloadView) this.downloadView.style.display = "block";
    } else if (hash === "#continue-watching") {
      this.homeView.style.display = "block";
      const cwSection = document.getElementById("rail-continue-watching");
      if (cwSection) {
        cwSection.scrollIntoView({ behavior: "smooth" });
      }
    } else {
      // Home
      this.homeView.style.display = "block";
    }
  }

  async checkAuth() {
    const token = localStorage.getItem("cinecloud_token");
    if (!token) {
      this.renderLoggedOut();
      return;
    }

    try {
      const res = await fetch("/api/auth/me", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        this.currentUser = data.user;
        this.renderLoggedIn();
      } else {
        localStorage.removeItem("cinecloud_token");
        this.renderLoggedOut();
      }
    } catch (e) {
      this.renderLoggedOut();
    }
  }

  renderLoggedIn() {
    const user = this.currentUser;
    this.authActions.innerHTML = `
      <div style="display: flex; align-items: center; gap: 1rem;">
        <span class="pill-badge" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); border-color: rgba(6, 182, 212, 0.3);">
          👤 ${user.username} (${user.role.toUpperCase()})
        </span>
        <button id="logoutBtn" class="btn btn-secondary tv-nav-item" style="padding: 0.4rem 0.9rem; font-size: 0.8rem;" tabindex="0">Logout</button>
      </div>
    `;

    document.getElementById("logoutBtn").addEventListener("click", () => {
      localStorage.removeItem("cinecloud_token");
      this.currentUser = null;
      this.renderLoggedOut();
      this.showToast("Signed out");
      this.loadCategories();
    });
  }

  renderLoggedOut() {
    this.authActions.innerHTML = `
      <button id="loginBtn" class="btn btn-primary tv-nav-item" tabindex="0">Sign In</button>
    `;
    document.getElementById("loginBtn").addEventListener("click", () => {
      document.getElementById("authErrorMsg").style.display = "none";
      this.authModal.classList.add("open");
    });
  }

  async handleAuthSubmit(e) {
    e.preventDefault();
    const username = document.getElementById("authUsernameInput").value;
    const password = document.getElementById("authPasswordInput").value;
    const errorEl = document.getElementById("authErrorMsg");
    errorEl.style.display = "none";

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();

      if (res.ok && data.token) {
        localStorage.setItem("cinecloud_token", data.token);
        this.currentUser = data.user;
        this.authModal.classList.remove("open");
        this.renderLoggedIn();
        this.showToast(`Welcome back, ${data.user.username}!`);
        this.loadCategories();
      } else {
        errorEl.textContent = data.message || "Invalid username or password";
        errorEl.style.display = "block";
      }
    } catch (err) {
      errorEl.textContent = "Server connection error";
      errorEl.style.display = "block";
    }
  }

  async loadCategories() {
    const token = localStorage.getItem("cinecloud_token");
    const headers = token ? { "Authorization": `Bearer ${token}` } : {};

    try {
      const res = await fetch("/api/movies/categories", { headers });
      const data = await res.json();
      this.cachedCategories = data;

      // Populate Spotlight Hero
      if (data.featured && data.featured.length > 0) {
        this.renderHero(data.featured[0]);
      }

      // Populate Genre Filter Options
      this.genreFilter.innerHTML = `<option value="">All Genres</option>`;
      (data.genres || []).forEach(g => {
        this.genreFilter.innerHTML += `<option value="${g}">${g}</option>`;
      });

      // Render Rails
      this.renderRails(data);
    } catch (e) {
      console.error("Error loading categories", e);
    }
  }

  renderHero(movie) {
    const hero = document.getElementById("heroSpotlight");
    if (movie.backdrop_url) {
      hero.style.backgroundImage = `url('${movie.backdrop_url}')`;
    }
    document.getElementById("heroTitle").textContent = movie.title;
    document.getElementById("heroRating").textContent = movie.rating;
    document.getElementById("heroQuality").textContent = movie.resolution || "4K Ultra HD";
    document.getElementById("heroYear").textContent = movie.release_year;
    document.getElementById("heroDuration").textContent = `${Math.floor(movie.duration / 3600)}h ${Math.floor((movie.duration % 3600) / 60)}m`;
    document.getElementById("heroGenre").textContent = movie.genre;
    document.getElementById("heroSynopsis").textContent = movie.description;

    document.getElementById("heroPlayBtn").onclick = () => window.cinePlayer.loadMovie(movie);
    document.getElementById("heroDetailsBtn").onclick = () => this.openMovieModal(movie.id);
  }

  renderRails(data) {
    this.railsContainer.innerHTML = "";

    // 1. Continue Watching (if items exist)
    if (data.continue_watching && data.continue_watching.length > 0) {
      this.createRail("rail-continue-watching", "Continue Watching", data.continue_watching, true);
    }

    // 2. Curated Sections
    (data.sections || []).forEach(sec => {
      if (sec.movies && sec.movies.length > 0) {
        this.createRail(`rail-${sec.id}`, sec.title, sec.movies, false);
      }
    });
  }

  createRail(id, title, movies, isContinueWatching = false) {
    const section = document.createElement("section");
    section.className = "rail-section";
    section.id = id;

    section.innerHTML = `
      <div class="rail-header">
        <h2 class="rail-title">${title}</h2>
      </div>
      <div class="rail-carousel-wrap">
        <button class="rail-nav-btn prev" title="Scroll Left">‹</button>
        <div class="rail-carousel" id="${id}-carousel"></div>
        <button class="rail-nav-btn next" title="Scroll Right">›</button>
      </div>
    `;

    const carousel = section.querySelector(".rail-carousel");

    movies.forEach(movie => {
      const card = this.createMovieCard(movie, isContinueWatching);
      carousel.appendChild(card);
    });

    // Rail scroll buttons
    const prevBtn = section.querySelector(".rail-nav-btn.prev");
    const nextBtn = section.querySelector(".rail-nav-btn.next");
    prevBtn.addEventListener("click", () => carousel.scrollBy({ left: -450, behavior: "smooth" }));
    nextBtn.addEventListener("click", () => carousel.scrollBy({ left: 450, behavior: "smooth" }));

    this.railsContainer.appendChild(section);
  }

  createMovieCard(movie, isContinueWatching = false) {
    const card = document.createElement("div");
    card.className = "movie-card tv-nav-item";
    card.tabIndex = 0;

    let progressHtml = "";
    if (isContinueWatching && movie.current_time && movie.progress_duration) {
      const pct = Math.min(100, Math.round((movie.current_time / movie.progress_duration) * 100));
      progressHtml = `
        <div class="progress-bar-container">
          <div class="progress-bar-fill" style="width: ${pct}%"></div>
        </div>
      `;
    }

    card.innerHTML = `
      <img class="movie-poster" src="${movie.poster_url || '/assets/default-poster.jpg'}" alt="${movie.title}" loading="lazy">
      <div class="movie-card-overlay">
        <div class="movie-card-title">${movie.title}</div>
        <div class="movie-card-sub">
          <span>${movie.release_year} • ${movie.resolution || '1080p'}</span>
          <span class="card-rating">★ ${movie.rating}</span>
        </div>
      </div>
      ${progressHtml}
    `;

    card.addEventListener("click", () => this.openMovieModal(movie.id));
    return card;
  }

  async openMovieModal(movieId) {
    const token = localStorage.getItem("cinecloud_token");
    const headers = token ? { "Authorization": `Bearer ${token}` } : {};

    try {
      const res = await fetch(`/api/movies/${movieId}`, { headers });
      const data = await res.json();
      const movie = data.movie;

      document.getElementById("modalHero").style.backgroundImage = `url('${movie.backdrop_url || movie.poster_url}')`;
      document.getElementById("modalPoster").src = movie.poster_url || "";
      document.getElementById("modalTitle").textContent = movie.title;
      document.getElementById("modalRating").textContent = movie.rating;
      document.getElementById("modalResolution").textContent = movie.resolution || "4K Ultra HD";
      document.getElementById("modalYear").textContent = movie.release_year;
      document.getElementById("modalDuration").textContent = `${Math.floor(movie.duration / 3600)}h ${Math.floor((movie.duration % 3600) / 60)}m`;
      document.getElementById("modalGenre").textContent = movie.genre;
      document.getElementById("modalDesc").textContent = movie.description;

      // Resume badge
      const resumeBadge = document.getElementById("modalResumeBadge");
      const playBtnText = document.getElementById("modalPlayBtnText");
      if (movie.watch_progress && !movie.watch_progress.is_completed && movie.watch_progress.current_time > 15) {
        resumeBadge.style.display = "block";
        resumeBadge.textContent = `Resume from ${window.cinePlayer.formatTime(movie.watch_progress.current_time)}`;
        playBtnText.textContent = "Resume Movie";
      } else {
        resumeBadge.style.display = "none";
        playBtnText.textContent = "Play Movie";
      }

      // Play button action
      document.getElementById("modalPlayBtn").onclick = () => {
        this.movieModal.classList.remove("open");
        window.cinePlayer.loadMovie(movie);
      };

      // Subtitles & Audio Chips
      const tracksContainer = document.getElementById("modalTracks");
      tracksContainer.innerHTML = "";
      (movie.subtitles || []).forEach(sub => {
        tracksContainer.innerHTML += `<div class="track-chip">💬 Sub: ${sub.label}</div>`;
      });
      (movie.audio_tracks || []).forEach(aud => {
        tracksContainer.innerHTML += `<div class="track-chip">🔊 Audio: ${aud.label}</div>`;
      });

      this.movieModal.classList.add("open");

      // Auto-focus play button for TV remote
      if (window.tvNav && window.tvNav.isTvMode) {
        setTimeout(() => window.tvNav.setFocus(document.getElementById("modalPlayBtn")), 300);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async loadLibrary(query = "") {
    const genre = this.genreFilter.value;
    const sort = this.sortFilter.value;

    let url = `/api/movies?limit=50&sort=${sort}`;
    if (query) url += `&query=${encodeURIComponent(query)}`;
    if (genre) url += `&genre=${encodeURIComponent(genre)}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      this.libraryGrid.innerHTML = "";

      if (!data.movies || data.movies.length === 0) {
        this.libraryGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 4rem;">No movies matched your search criteria.</div>`;
        return;
      }

      data.movies.forEach(movie => {
        const card = this.createMovieCard(movie, false);
        this.libraryGrid.appendChild(card);
      });
    } catch (e) {
      console.error(e);
    }
  }

  showToast(message) {
    const msgEl = document.getElementById("toastMessage");
    msgEl.textContent = message;
    this.toastNotice.classList.add("show");
    setTimeout(() => {
      this.toastNotice.classList.remove("show");
    }, 3500);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.cineApp = new CineApp();
});
