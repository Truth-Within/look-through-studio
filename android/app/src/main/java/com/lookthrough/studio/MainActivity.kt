package com.lookthrough.studio

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toolbar

/**
 * The Android companion app: a full-screen client for the studio web UI.
 *
 * Run `python3 webapp.py --host 0.0.0.0 --port 8080` (or the desktop app with
 * `--host 0.0.0.0`) on the machine that renders videos, then point this app at
 * that machine's LAN address in Settings (e.g. 192.168.1.20 : 8080).
 * Everything the dashboard can do — start renders, watch the batch queue,
 * play back videos and shorts, download artifacts — works from the phone.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private lateinit var toolbar: Toolbar
    private var customView: View? = null
    private var customViewCallback: WebChromeClient.CustomViewCallback? = null

    private fun prefs() = getSharedPreferences("server", MODE_PRIVATE)

    private fun host(): String = prefs().getString("host", "")!!.trim().removePrefix("http://").removeSuffix("/")

    private fun baseUrl(): String {
        val port = prefs().getInt("port", 8080)
        return "http://${host()}:$port/"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        toolbar = findViewById(R.id.toolbar)
        toolbar.title = getString(R.string.app_name)
        setActionBar(toolbar)
        toolbar.inflateMenu(R.menu.main_menu)
        toolbar.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_reload -> { web.reload(); true }
                R.id.action_settings -> { startActivity(Intent(this, SettingsActivity::class.java)); true }
                R.id.action_open_browser -> {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(baseUrl()))); true
                }
                R.id.action_quit -> { finishAffinity(); true }
                else -> false
            }
        }

        web = findViewById(R.id.webview)
        val ws = web.settings
        ws.javaScriptEnabled = true
        ws.domStorageEnabled = true
        ws.mediaPlaybackRequiresUserGesture = false
        ws.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        ws.allowFileAccess = false
        ws.allowContentAccess = false

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(v: WebView, req: WebResourceRequest): Boolean {
                val u = req.url
                if (u.scheme == "studio" && u.host == "settings") {
                    startActivity(Intent(this@MainActivity, SettingsActivity::class.java))
                    return true
                }
                val baseHost = Uri.parse(baseUrl()).host
                return if (u.host == baseHost || u.host == "localhost" || u.host == "127.0.0.1") {
                    false // keep studio pages inside the app
                } else {
                    startActivity(Intent(Intent.ACTION_VIEW, u)); true
                }
            }

            override fun onReceivedError(v: WebView, req: WebResourceRequest, err: WebResourceError) {
                if (req.isForMainFrame) v.loadDataWithBaseURL(
                    "http://studio.local/", errorPage(req.url.toString(), err.description?.toString() ?: "unknown error"),
                    "text/html", "utf-8", null)
            }
        }

        // fullscreen video playback (the dashboard's <video> players)
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                customView = view
                customViewCallback = callback
                (window.decorView as ViewGroup).addView(
                    view, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT))
                web.visibility = View.GONE
            }

            override fun onHideCustomView() {
                customView?.let { (window.decorView as ViewGroup).removeView(it) }
                customView = null
                web.visibility = View.VISIBLE
                customViewCallback?.onCustomViewHidden()
                customViewCallback = null
            }
        }

        // downloads (mp4/srt/json) open in the browser / download manager
        web.setDownloadListener { url, _, _, _, _ ->
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }

        if (host().isBlank()) {
            startActivity(Intent(this, SettingsActivity::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        if (!::web.isInitialized) return
        if (host().isBlank()) {
            startActivity(Intent(this, SettingsActivity::class.java))
            return
        }
        toolbar.subtitle = baseUrl()
        val url = baseUrl()
        if (web.url != url) web.loadUrl(url)
    }

    /** Shown when the studio server can't be reached — explains the usual causes. */
    private fun errorPage(url: String, desc: String): String {
        val target = if (host().isBlank()) "(no server configured)" else baseUrl()
        return """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 body{background:#0e1420;color:#e8edf5;font-family:sans-serif;margin:0;padding:28px 22px;line-height:1.55}
 h1{color:#ff8a5c;font-size:21px;margin:0 0 6px}
 .url{background:#1a2334;border-radius:8px;padding:10px 12px;font-size:13px;word-break:break-all;color:#9fd0ff}
 .err{color:#93a1b5;font-size:13px;margin:10px 0 18px}
 ol{margin:0 0 18px;padding-left:20px;font-size:14.5px}
 li{margin-bottom:9px}
 code{background:#1a2334;padding:1px 6px;border-radius:5px;color:#ffd28a}
 a.btn{display:inline-block;background:#ff8a5c;color:#0e1420;font-weight:bold;text-decoration:none;
   padding:12px 18px;border-radius:10px;font-size:15px}
 .note{margin-top:18px;color:#93a1b5;font-size:12.5px}
</style></head><body>
<h1>Can't reach the studio</h1>
<div class="url">Tried: $url</div>
<div class="err">$desc</div>
<ol>
 <li>On the computer, run <code>./start_web.sh</code> and leave it open (it binds <code>0.0.0.0</code>, so the phone can connect).</li>
 <li>Make sure this phone and the computer are on the <b>same Wi-Fi</b>.</li>
 <li>Enter the computer's <b>LAN address</b> (e.g. <code>192.168.1.70</code>) — <b>not</b> <code>127.0.0.1</code>: on the phone, 127.0.0.1 is the phone itself. Or tap <b>Auto-discover</b> in settings.</li>
 <li>If the computer has a firewall, allow incoming connections on port <code>8080</code>.</li>
</ol>
<a class="btn" href="studio://settings">Open server settings</a>
<div class="note">Configured server: $target</div>
</body></html>
""".trimIndent()
    }

    override fun onBackPressed() {
        if (customView != null) {
            customViewCallback?.onCustomViewHidden()
            return
        }
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        if (::web.isInitialized) web.destroy()
        super.onDestroy()
    }
}
