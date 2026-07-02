package com.jarvis.remote

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var errorView: LinearLayout
    private lateinit var errorText: TextView
    private var mainLoadFailed = false

    private val prefs by lazy { getSharedPreferences("jarvis", MODE_PRIVATE) }
    private var serverUrl: String
        get() = prefs.getString("url", "") ?: ""
        set(v) { prefs.edit().putString("url", v).apply() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = FrameLayout(this)

        webView = WebView(this)
        setupWebView()
        root.addView(webView)

        errorView = buildErrorView()
        errorView.visibility = View.GONE
        root.addView(errorView)

        setContentView(root)

        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 1)
        }

        if (serverUrl.isEmpty()) showUrlDialog(first = true) else webView.loadUrl(serverUrl)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        }
        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread { request.grant(request.resources) }
            }
        }
        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                mainLoadFailed = false
                errorView.visibility = View.GONE
            }
            override fun onReceivedError(view: WebView, req: WebResourceRequest, err: WebResourceError) {
                if (req.isForMainFrame) {
                    mainLoadFailed = true
                    errorText.text = "Can't reach server\n${req.url}\n\n${err.description}"
                    errorView.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun buildErrorView(): LinearLayout {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.BLACK)
            setPadding(48, 48, 48, 48)
        }
        errorText = TextView(this).apply {
            setTextColor(Color.WHITE)
            textSize = 16f
            gravity = Gravity.CENTER
        }
        layout.addView(errorText)
        layout.addView(Button(this).apply {
            text = "Retry"
            setOnClickListener { webView.loadUrl(serverUrl) }
        })
        layout.addView(Button(this).apply {
            text = "Change server"
            setOnClickListener { showUrlDialog(first = false) }
        })
        return layout
    }

    private fun showUrlDialog(first: Boolean) {
        val input = EditText(this).apply {
            setText(if (serverUrl.isEmpty()) "http://192.168.1.5:3001" else serverUrl)
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("Jarvis server URL")
            .setView(input)
            .setCancelable(!first)
            .setPositiveButton("Connect") { _, _ ->
                var url = input.text.toString().trim()
                if (!url.startsWith("http")) url = "http://$url"
                serverUrl = url
                webView.loadUrl(url)
            }
        if (!first) dialog.setNegativeButton("Cancel", null)
        dialog.show()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        when {
            webView.canGoBack() && !mainLoadFailed -> webView.goBack()
            else -> AlertDialog.Builder(this)
                .setItems(arrayOf("Change server", "Exit")) { _, which ->
                    if (which == 0) showUrlDialog(first = false) else finish()
                }
                .show()
        }
    }
}
