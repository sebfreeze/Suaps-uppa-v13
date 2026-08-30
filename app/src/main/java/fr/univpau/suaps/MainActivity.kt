package fr.univpau.suaps

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    companion object {
        private const val APP_URL = "https://suaps-uppa-v13.onrender.com"
        private const val APP_HOST = "suaps-uppa-v13.onrender.com"
    }

    private lateinit var webView: WebView
    private lateinit var splashOverlay: View
    private var splashHidden = false
    private var readinessChecks = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Ne jamais exposer le contenu de la WebView à un débogage distant.
        WebView.setWebContentsDebuggingEnabled(false)

        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.WHITE)
        }

        webView = WebView(this).apply {
            visibility = View.INVISIBLE
            setLayerType(View.LAYER_TYPE_HARDWARE, null)
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val uri = request?.url ?: return true
                    return handleNavigation(uri)
                }

                @Suppress("DEPRECATION")
                override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                    val uri = url?.let(Uri::parse) ?: return true
                    return handleNavigation(uri)
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    if (url?.startsWith(APP_URL) == true) {
                        readinessChecks = 0
                        checkAppReady()
                    }
                }
            }
        }

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            loadsImagesAutomatically = true
            useWideViewPort = true
            loadWithOverviewMode = true

            // Durcissement : l'application ne doit charger que du contenu web HTTPS.
            allowFileAccess = false
            allowContentAccess = false
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            mediaPlaybackRequiresUserGesture = true

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                safeBrowsingEnabled = true
            }
        }

        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, false)
        }

        root.addView(
            webView,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        )

        splashOverlay = buildSplashScreen()
        root.addView(
            splashOverlay,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        )

        setContentView(root)

        if (savedInstanceState == null) {
            webView.loadUrl(APP_URL)
        } else {
            webView.restoreState(savedInstanceState)
            webView.postDelayed({ checkAppReady() }, 350)
        }

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        finish()
                    }
                }
            }
        )
    }

    private fun buildSplashScreen(): View {
        val density = resources.displayMetrics.density
        fun dp(value: Int) = (value * density).toInt()

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(28), dp(36), dp(28), dp(36))
            setBackgroundColor(Color.rgb(247, 250, 252))
        }

        val logo = ImageView(this).apply {
            setImageResource(R.drawable.logo_uppa)
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.CENTER_INSIDE
        }
        container.addView(
            logo,
            LinearLayout.LayoutParams(dp(230), dp(120)).apply {
                bottomMargin = dp(24)
                gravity = Gravity.CENTER_HORIZONTAL
            }
        )

        val title = TextView(this).apply {
            text = "SUAPS UPPA"
            textSize = 29f
            setTextColor(Color.rgb(0, 71, 119))
            setTypeface(typeface, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        container.addView(
            title,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        val subtitle = TextView(this).apply {
            text = "Le sport au cœur de votre université"
            textSize = 17f
            setTextColor(Color.rgb(55, 65, 81))
            gravity = Gravity.CENTER
        }
        container.addView(
            subtitle,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dp(8)
                bottomMargin = dp(34)
            }
        )

        val progress = ProgressBar(this).apply {
            isIndeterminate = true
        }
        container.addView(
            progress,
            LinearLayout.LayoutParams(dp(44), dp(44)).apply {
                gravity = Gravity.CENTER_HORIZONTAL
            }
        )

        val loading = TextView(this).apply {
            text = "Préparation de votre espace sportif…"
            textSize = 14f
            setTextColor(Color.rgb(75, 85, 99))
            gravity = Gravity.CENTER
        }
        container.addView(
            loading,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dp(14)
            }
        )

        val university = TextView(this).apply {
            text = "Université de Pau et des Pays de l’Adour"
            textSize = 12f
            setTextColor(Color.rgb(107, 114, 128))
            gravity = Gravity.CENTER
        }
        container.addView(
            university,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                topMargin = dp(28)
            }
        )

        return container
    }

    private fun checkAppReady() {
        if (splashHidden || webView.visibility == View.GONE) return

        webView.evaluateJavascript(
            """
            (function() {
              try {
                const app = document.querySelector('[data-testid="stAppViewContainer"]');
                if (!app) return false;
                const txt = (app.innerText || '').trim();
                const technical = /please wait|connecting|running|loading|chargement des données/i.test(txt);
                return txt.length > 70 && !technical;
              } catch (e) { return false; }
            })();
            """.trimIndent()
        ) { result ->
            val ready = result == "true"
            if (ready || readinessChecks >= 50) {
                hideSplash()
            } else {
                readinessChecks += 1
                webView.postDelayed({ checkAppReady() }, 300)
            }
        }
    }

    private fun hideSplash() {
        if (splashHidden) return
        splashHidden = true
        webView.visibility = View.VISIBLE
        webView.alpha = 0f
        webView.animate().alpha(1f).setDuration(260).start()
        splashOverlay.animate()
            .alpha(0f)
            .setDuration(220)
            .withEndAction { splashOverlay.visibility = View.GONE }
            .start()
    }

    private fun handleNavigation(uri: Uri): Boolean {
        // Le site SUAPS reste dans l'application.
        if (uri.scheme == "https" && uri.host.equals(APP_HOST, ignoreCase = true)) {
            return false
        }

        // Les services externes (ex. MySportU / HelloAsso) s'ouvrent dans le navigateur sécurisé.
        if (uri.scheme == "https") {
            return try {
                startActivity(Intent(Intent.ACTION_VIEW, uri))
                true
            } catch (_: Exception) {
                true
            }
        }

        // Bloque file://, content://, http:// et les schémas non attendus.
        return true
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        webView.stopLoading()
        webView.webChromeClient = null
        webView.webViewClient = WebViewClient()
        webView.destroy()
        super.onDestroy()
    }
}
