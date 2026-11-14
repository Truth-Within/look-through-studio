package com.lookthrough.studio

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.URL
import kotlin.concurrent.thread
import org.json.JSONObject

/**
 * Server address configuration + connectivity test against /api/health +
 * one-tap UDP auto-discovery (the studio server answers probes on UDP 8081).
 */
class SettingsActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)
        setTitle(R.string.settings_title)

        val prefs = getSharedPreferences("server", MODE_PRIVATE)
        val host = findViewById<EditText>(R.id.host)
        val port = findViewById<EditText>(R.id.port)
        val status = findViewById<TextView>(R.id.status)

        host.setText(prefs.getString("host", ""))
        port.setText(prefs.getInt("port", 8080).toString())
        findViewById<TextView>(R.id.phoneIp).text = getString(R.string.this_phone, localIp())

        findViewById<Button>(R.id.save).setOnClickListener {
            val h = clean(host.text.toString())
            val p = port.text.toString().toIntOrNull() ?: 8080
            prefs.edit().putString("host", h).putInt("port", p).apply()
            Toast.makeText(this, "Saved http://$h:$p", Toast.LENGTH_SHORT).show()
            finish()
        }

        findViewById<Button>(R.id.test).setOnClickListener {
            val h = clean(host.text.toString())
            val p = port.text.toString().toIntOrNull() ?: 8080
            if (h.isBlank()) {
                status.text = getString(R.string.enter_host_first)
                return@setOnClickListener
            }
            status.text = "Testing http://$h:$p/api/health …"
            thread {
                val msg = try {
                    val c = URL("http://$h:$p/api/health").openConnection() as HttpURLConnection
                    c.connectTimeout = 4000
                    c.readTimeout = 4000
                    val body = c.inputStream.bufferedReader().readText()
                    if (c.responseCode == 200 && body.contains("\"ok\""))
                        "✓ reachable — $body"
                    else
                        "✗ HTTP ${c.responseCode}: $body"
                } catch (e: Exception) {
                    "✗ ${e.message}"
                }
                runOnUiThread { status.text = msg }
            }
        }

        findViewById<Button>(R.id.discover).setOnClickListener {
            status.text = getString(R.string.discovering)
            thread {
                val found = udpDiscover()
                runOnUiThread {
                    if (found != null) {
                        host.setText(found.first)
                        port.setText(found.second.toString())
                        status.text = getString(R.string.discover_found, found.first, found.second)
                    } else {
                        status.text = getString(R.string.discover_none)
                    }
                }
            }
        }
    }

    /** Broadcast a discovery probe on UDP 8081 and wait ~3s for a studio server. */
    private fun udpDiscover(): Pair<String, Int>? {
        val targets = mutableListOf<InetAddress>()
        try { targets.add(InetAddress.getByName("255.255.255.255")) } catch (_: Exception) {}
        localIp().split(".").takeIf { it.size == 4 }?.let { p ->
            try { targets.add(InetAddress.getByName("${p[0]}.${p[1]}.${p[2]}.255")) } catch (_: Exception) {}
        }
        DatagramSocket().use { s ->
            s.broadcast = true
            s.soTimeout = 400
            val msg = "LOOKTHROUGH_DISCOVER".toByteArray()
            for (t in targets.distinct()) {
                try { s.send(DatagramPacket(msg, msg.size, t, 8081)) } catch (_: Exception) {}
            }
            val deadline = System.currentTimeMillis() + 3000
            val buf = ByteArray(2048)
            while (System.currentTimeMillis() < deadline) {
                try {
                    val p = DatagramPacket(buf, buf.size)
                    s.receive(p)
                    val j = JSONObject(String(p.data, 0, p.length))
                    if (j.optString("app") == "lookthrough-studio") {
                        val port = j.optInt("port", 8080)
                        val ips = j.optJSONArray("ips") ?: continue
                        val mySubnet = localIp().split(".").take(3).joinToString(".")
                        var fallback: String? = null
                        for (i in 0 until ips.length()) {
                            val ip = ips.getString(i)
                            if (!Regex("^\\d+\\.\\d+\\.\\d+\\.\\d+$").matches(ip) || ip.startsWith("127.")) continue
                            if (ip.startsWith("$mySubnet.")) return ip to port  // same subnet as this phone
                            if (fallback == null) fallback = ip
                        }
                        if (fallback != null) return fallback to port
                    }
                } catch (_: Exception) { /* timeout / bad packet: keep listening */ }
            }
        }
        return null
    }

    private fun clean(s: String) = s.trim().removePrefix("http://").removePrefix("https://").removeSuffix("/")

    private fun localIp(): String {
        try {
            val en = NetworkInterface.getNetworkInterfaces()
            while (en.hasMoreElements()) {
                val addrs = en.nextElement().inetAddresses
                while (addrs.hasMoreElements()) {
                    val a = addrs.nextElement()
                    val ha = a.hostAddress
                    if (!a.isLoopbackAddress && ha != null && !ha.contains(":")) return ha
                }
            }
        } catch (_: Exception) {
        }
        return "unknown"
    }
}
