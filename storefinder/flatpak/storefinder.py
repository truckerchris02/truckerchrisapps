#!/usr/bin/env python3
# Walmart Store Finder desktop. GTK4 + WebKitGTK around the same pages as the phone app.
# localStorage stays in this user's data directory, so saved stores survive a restart.
import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Gdk, GLib, WebKit

APP = "com.truckerchris.StoreFinder"
HERE = os.environ.get("STOREFINDER_DIR", "/app/share/storefinder")
VER = "1.2.0"

data_dir = os.path.join(GLib.get_user_data_dir(), "storefinder")
cache_dir = os.path.join(GLib.get_user_cache_dir(), "storefinder")
os.makedirs(data_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP)
        self.win = None

    def do_activate(self):
        if self.win:
            self.win.present()
            return
        settings = Gtk.Settings.get_default()
        if hasattr(Gtk, "InterfaceColorScheme") and settings.find_property("gtk-interface-color-scheme"):
            settings.set_property("gtk-interface-color-scheme", Gtk.InterfaceColorScheme.DARK)
        window = Gtk.ApplicationWindow(application=self, title="Walmart Store Finder v" + VER)
        window.set_default_size(480, 900)
        self.win = window
        session = WebKit.NetworkSession.new(data_dir, cache_dir)
        view = WebKit.WebView(network_session=session)
        web = view.get_settings()
        web.set_enable_javascript(True)
        web.set_allow_file_access_from_file_urls(True)
        if hasattr(web, "set_allow_universal_access_from_file_urls"):
            web.set_allow_universal_access_from_file_urls(True)
        web.set_user_agent_with_application_details("StoreFinder", VER)
        if os.environ.get("SF_DEBUG"):
            web.set_enable_write_console_messages_to_stdout(True)
        view.connect("decide-policy", self.on_policy)
        view.connect("load-changed", self.on_load)
        window.set_child(view)
        view.load_uri("file://" + HERE + "/index.html")
        window.present()

    def on_load(self, view, event):
        if not os.environ.get("SF_SMOKE"):
            return
        if event != WebKit.LoadEvent.FINISHED:
            return

        def report():
            title = view.get_title() or ""
            print("SMOKE title=" + title, flush=True)
            self.quit()
            return False

        GLib.timeout_add(1200, report)

    def on_policy(self, view, decision, decision_type):
        if decision_type not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        uri = decision.get_navigation_action().get_request().get_uri() or ""
        if uri.startswith("file://" + HERE + "/"):
            return False
        if uri.startswith("geo:"):
            query = uri.split("q=", 1)[1] if "q=" in uri else uri[4:]
            uri = "https://maps.google.com/maps?q=" + query
        if uri.startswith("http://") or uri.startswith("https://") or uri.startswith("tel:"):
            Gtk.UriLauncher.new(uri).launch(self.win, None, None, None)
            decision.ignore()
            return True
        return False


if __name__ == "__main__":
    App().run(None)
