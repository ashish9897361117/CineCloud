# CineCloud Android TV App 📺

Native Android TV application for **CineCloud**, powered by **AndroidX Leanback** and **ExoPlayer (Media3)**.

## Features
- **10-Foot UI**: Remote-friendly browsing with high-contrast D-pad focus indicators.
- **Hero & Category Rows**: Continue Watching (with progress sync), Featured Premiere, Recently Added, Action & Sci-Fi, and Drama.
- **Advanced ExoPlayer Playback**:
  - Direct HTTP byte-range and HLS adaptive streaming.
  - Remote control play/pause, fast-forward (+10s), rewind (-10s).
  - Subtitle track selector (WebVTT).
  - Multi-track audio switching.
  - Resume Watching: Automatically resumes from where you left off on phone or laptop.
  - Continuous watch progress sync back to the CineCloud server.
- **Server Discovery**: Enter your CineCloud server URL (e.g. `http://192.168.1.50:8080/` or your custom domain).

---

## How to Build the APK with Android Studio

### Prerequisites
1. [Android Studio](https://developer.android.com/studio) (Hedgehog or newer recommended).
2. Android SDK with API 34 installed.

### Steps
1. Open Android Studio.
2. Select **Open an Existing Project** and choose the `android-tv` directory from this repository.
3. Allow Gradle to sync dependencies.
4. Click **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**.
5. Once complete, locate the APK at:
   `android-tv/app/build/outputs/apk/debug/app-debug.apk`

---

## How to Install on Android TV / Fire TV Stick

### Method 1: Using ADB (Over Wi-Fi)
1. On your Android TV, enable Developer Options:
   - Go to **Settings** > **Device Preferences** > **About** > Click **Build** 7 times.
2. Go to **Settings** > **Developer Options** > Turn on **USB Debugging** & **Network Debugging**.
3. Note your TV's IP address (e.g. `192.168.1.105`).
4. From your laptop terminal, connect:
   ```bash
   adb connect 192.168.1.105:5555
   adb install -r android-tv/app/build/outputs/apk/debug/app-debug.apk
   ```

### Method 2: Using "Send Files to TV" App
1. Install **Send Files to TV** from the Google Play Store on both your phone/laptop and Android TV.
2. Transfer `app-debug.apk` to your TV.
3. Open a file manager (like **File Commander** or **FX File Explorer**) on your Android TV and click the APK to install.

---

## Alternative: Browser-Based TV Mode (Zero-Install)
If you don't wish to install an APK, you can open CineCloud in your Android TV's web browser (such as **Silk Browser**, **TV Bro**, or **JioPages TV**) at:
`http://<your-server-ip>:8080/#tv`

The built-in spatial navigation engine (`web/js/tv-nav.js`) gives you the exact same 10-foot remote control experience!
