/* GPS shift miles for the browser. Counts only while this page is open. */
(function () {
  var KEY = "righub-web-miles-v1";
  var st;
  try { st = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { st = null; }
  if (!st || typeof st !== "object") st = { tracking: false, paused: false, sessionMeters: 0, gps: "", days: {} };
  st.days = st.days || {};
  var watch = null, last = null, wake = null;
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {}
    try { if (window.onMileState) window.onMileState(); } catch (e) {}
  }
  function dayKey(d) {
    function z(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear() + "-" + z(d.getMonth() + 1) + "-" + z(d.getDate());
  }
  function meters(a, b) {
    var R = 6371000, p1 = a.lat * Math.PI / 180, p2 = b.lat * Math.PI / 180;
    var dp = (b.lat - a.lat) * Math.PI / 180, dl = (b.lng - a.lng) * Math.PI / 180;
    var x = Math.sin(dp / 2) * Math.sin(dp / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  }
  function onPos(p) {
    st.gps = "on";
    var here = { lat: p.coords.latitude, lng: p.coords.longitude, t: p.timestamp || Date.now() };
    if (!st.paused && last) {
      var d = meters(last, here);
      var dt = (here.t - last.t) / 1000;
      if (d > 12 && d < 400 && dt > 0 && d / dt < 45) {
        st.sessionMeters += d;
        var k = dayKey(new Date());
        st.days[k] = (parseFloat(st.days[k]) || 0) + d;
      }
    }
    last = here;
    save();
  }
  function onErr(e) {
    st.gps = e && e.code === 1 ? "denied" : "off";
    save();
  }
  function armWatch() {
    if (watch != null || !navigator.geolocation) return;
    watch = navigator.geolocation.watchPosition(onPos, onErr, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
  }
  window.MileBridge = {
    status: function () { return JSON.stringify(st); },
    start: function () {
      if (!navigator.geolocation) { st.gps = "off"; st.tracking = false; save(); return; }
      st.tracking = true;
      st.paused = false;
      st.sessionMeters = 0;
      st.gps = "searching";
      last = null;
      save();
      if (navigator.wakeLock && navigator.wakeLock.request) {
        navigator.wakeLock.request("screen").then(function (w) { wake = w; }).catch(function () {});
      }
      armWatch();
    },
    stop: function () {
      st.tracking = false;
      st.paused = false;
      if (watch != null && navigator.geolocation) navigator.geolocation.clearWatch(watch);
      watch = null;
      last = null;
      if (wake) { try { wake.release(); } catch (e) {} wake = null; }
      save();
    },
    pause: function () { st.paused = true; last = null; save(); },
    resume: function () { st.paused = false; last = null; save(); if (st.tracking) armWatch(); },
    importDays: function (json) {
      var d = {};
      try { d = JSON.parse(json) || {}; } catch (e) { return; }
      Object.keys(d).forEach(function (k) {
        var n = parseFloat(d[k]) || 0;
        if (n > (parseFloat(st.days[k]) || 0)) st.days[k] = n;
      });
      save();
    }
  };
  if (st.tracking) armWatch();
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden && st.tracking && !st.paused && navigator.wakeLock && navigator.wakeLock.request) {
      navigator.wakeLock.request("screen").then(function (w) { wake = w; }).catch(function () {});
    }
  });
})();
