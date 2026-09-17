"""Deterministic frame capture out of headless Edge, over the DevTools protocol.

Screenshotting an animation by wall clock gives you whatever the machine managed to
paint — jitter, dropped motion, a countdown that skips a number. Instead the page runs on
*virtual* time: the clock is frozen, advanced by exactly one frame, the frame is grabbed,
and only then advanced again. Date.now(), setTimeout, and CSS animations all move with it,
so the result is frame-exact however slow the capture happens to be.
"""
import base64, io, json, os, shutil, subprocess, threading, time
import urllib.request
import websocket

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_INST = 0
_INST_LOCK = threading.Lock()


class Browser:
    def __init__(self, profile_dir, width=1920, height=1080):
        # Port 0 lets Edge pick, and it writes the real one into DevToolsActivePort in the
        # profile. Choosing a "free" port from Python first is a race — the probe socket
        # has to be closed before Edge can bind it, and on Windows it often still cannot.
        # A profile directory can only be held by one Edge at a time, and a lingering
        # process from an earlier run makes the next launch exit instantly with no error
        # anywhere except a missing port file. Give every instance its own directory.
        # the counter is bumped under a lock: parallel workers that both read the old
        # value land in the same directory, and the second Edge then dies on the lock
        global _INST
        with _INST_LOCK:
            _INST += 1
            n = _INST
        profile_dir = os.path.join(profile_dir, "inst_%d_%d" % (os.getpid(), n))
        shutil.rmtree(profile_dir, ignore_errors=True)
        os.makedirs(profile_dir, exist_ok=True)
        self.profile_dir = profile_dir
        portfile = os.path.join(profile_dir, "DevToolsActivePort")

        self.proc = subprocess.Popen(
            [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1",
             "--window-size=%d,%d" % (width, height),
             "--remote-debugging-port=0",
             # the websocket handshake is origin-checked and refuses our own loopback
             # origin with a 403 without this
             "--remote-allow-origins=*",
             "--user-data-dir=" + profile_dir,
             "--no-first-run", "--no-default-browser-check",
             # without these Edge opens a sync-confirmation page as its FIRST target and
             # the capture attaches to that instead of the stage
             "--disable-sync", "--disable-background-networking",
             "--disable-features=Translate,MediaRouter",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self.port = None
        for _ in range(400):
            if os.path.exists(portfile):
                try:
                    first = io.open(portfile, encoding="utf-8").read().splitlines()
                    if first and first[0].strip().isdigit():
                        self.port = int(first[0].strip())
                        break
                except OSError:
                    pass
            time.sleep(0.05)
        if self.port is None:
            raise RuntimeError("Edge never wrote DevToolsActivePort")

        self.ws = None
        self._events = []
        self._id = 0
        # explicit no-proxy opener: a system proxy makes urllib try to reach 127.0.0.1
        # through it, and the attach then times out with nothing to show for it
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        last = None
        for _ in range(200):
            try:
                raw = opener.open(
                    "http://127.0.0.1:%d/json/list" % self.port, timeout=2).read()
                tabs = [t for t in json.loads(raw)
                        if t.get("type") == "page"
                        and not t.get("url", "").startswith("edge://")]
                if tabs:
                    self.ws = websocket.create_connection(
                        tabs[0]["webSocketDebuggerUrl"], timeout=300,
                        max_size=64 * 1024 * 1024)
                    break
            except Exception as e:
                last = e
            time.sleep(0.15)
        if not self.ws:
            raise RuntimeError("could not attach on port %d (%s)" % (self.port, last))

        # Page.enable is needed for lifecycle; Runtime.enable only adds console chatter
        self.send("Page.enable")
        # --window-size sizes the WINDOW, and the chrome comes out of it: asking for
        # 1920x1080 yielded a 1896x988 viewport, i.e. a 1.92:1 film instead of 16:9.
        # Override the metrics so the viewport is exactly the frame we want to ship.
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=height,
                  deviceScaleFactor=1, mobile=False)

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})
            # Events must be kept, not dropped. virtualTimeBudgetExpired routinely arrives
            # before the reply to the setVirtualTimePolicy call that caused it; discarding
            # it here left wait_event() blocking on an event that had already gone by,
            # until the socket timed out and the capture died mid-scene.
            if "method" in msg:
                self._events.append(msg)

    def wait_event(self, name, timeout=300):
        for i, msg in enumerate(self._events):
            if msg.get("method") == name:
                return self._events.pop(i).get("params", {})
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self.ws.recv())
            if msg.get("method") == name:
                return msg.get("params", {})
            if "method" in msg:
                self._events.append(msg)
        raise RuntimeError("timed out waiting for " + name)

    # ---- virtual time -----------------------------------------------------
    def vt(self, policy, budget=None):
        p = {"policy": policy}
        if budget is not None:
            p["budget"] = budget
        self.send("Emulation.setVirtualTimePolicy", **p)
        if budget is not None:
            self.wait_event("Emulation.virtualTimeBudgetExpired")

    def load(self, url, settle_ms=6000):
        """Open the page with the clock paused, then let it settle deterministically."""
        self.vt("pause")
        self.send("Page.navigate", url=url)
        self.vt("pauseIfNetworkFetchesPending", budget=settle_ms)

    def advance(self, ms):
        self.vt("advance", budget=ms)

    def eval(self, expr):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=False)
        return r.get("result", {}).get("value")

    def shot_jpeg(self, quality=93):
        r = self.send("Page.captureScreenshot", format="jpeg", quality=quality,
                      captureBeyondViewport=False, optimizeForSpeed=True)
        return base64.b64decode(r["data"])

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        shutil.rmtree(self.profile_dir, ignore_errors=True)
