#!/usr/bin/env python3
# Rig Hub v1.6.0 desktop - GTK4 + WebKitGTK wrapper around the Rig Hub web app
# (Rig Nav, Trip Logger, Weather, Tandem Slide).
# 1.6.0 adds Tandem Slide on the same switcher bar. Each screen keeps its own view,
# so switching doesn't lose the map, a half-filled trip, or scale weights.
import os, json, base64, gi
gi.require_version('Gtk','4.0'); gi.require_version('WebKit','6.0')
from gi.repository import Gtk, Gdk, Gio, GLib, WebKit
APP='com.truckerchris.RigHub'; HERE=os.environ.get('RIGHUB_DIR','/app/share/righub'); VER='1.6.0'
# id, label, icon, page, version shown in the bar
TABS=[('home','Home','go-home-symbolic','index.html',''),
      ('nav','Rig Nav','find-location-symbolic','rignav/index.html','Rig Nav v1.5.0'),
      ('log','Trip Logger','x-office-document-symbolic','trip.html','Trip Logger v1.5.0'),
      ('wx','Weather','weather-storm-symbolic','weather.html','Weather (NWS)'),
      ('slide','Tandem Slide','object-flip-horizontal-symbolic','tandem/index.html','Tandem Slide v1.0')]
PAGE={t[3]:t[0] for t in TABS}
data=os.path.join(GLib.get_user_data_dir(),'righub'); cache=os.path.join(GLib.get_user_cache_dir(),'righub'); os.makedirs(data,exist_ok=True)
LAST=os.path.join(data,'last-tab')
# Blob downloads (CSV export / JSON backup) are sent to Python, which shows a Save dialog.
HOOK=r"""(function(){if(window.__tlPatched)return;window.__tlPatched=true;var orig=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){var href=this.getAttribute('href')||'',dl=this.getAttribute('download'),self=this;
if(dl&&href.indexOf('blob:')===0){fetch(href).then(function(r){return r.blob();}).then(function(b){var rd=new FileReader();
rd.onloadend=function(){window.webkit.messageHandlers.tl.postMessage(JSON.stringify({name:dl,b64:(''+rd.result).split(',')[1]||''}));};rd.readAsDataURL(b);})
.catch(function(){orig.call(self);});return;}return orig.call(this);};})();"""
PAGECSS=":root{color-scheme:dark} p.ver,.ver{font-size:15px !important}"
GTKCSS="""
.rh-bar{background:#14110e;border-bottom:2px solid #3a3228;padding:10px 12px;}
button.rh-tab{font-size:19px;font-weight:700;padding:10px 20px;min-height:34px;border-radius:12px;background:#231e18;color:#e8dccb;border:1px solid #3a3228;box-shadow:none;}
button.rh-tab:hover{background:#2f281f;}
button.rh-tab.on{background:#e07f2e;color:#1b1208;border-color:#e07f2e;}
button.rh-tab image{-gtk-icon-size:22px;}
.rh-ver{font-size:17px;font-weight:700;color:#f4efe6;}
.rh-sub{font-size:14px;color:#c4b6a2;}
"""
class A(Gtk.Application):
    def __init__(s): super().__init__(application_id=APP)
    def do_activate(s):
        if getattr(s,'win',None): s.win.present(); return
        gs=Gtk.Settings.get_default()
        if hasattr(Gtk,'InterfaceColorScheme') and gs.find_property('gtk-interface-color-scheme'): gs.set_property('gtk-interface-color-scheme',Gtk.InterfaceColorScheme.DARK)
        else: gs.set_property('gtk-application-prefer-dark-theme',True)
        cp=Gtk.CssProvider()
        try: cp.load_from_string(GTKCSS)
        except Exception: cp.load_from_data(GTKCSS,-1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),cp,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        w=Gtk.ApplicationWindow(application=s,title='Rig Hub v'+VER); w.set_default_size(1100,980); s.win=w
        s.session=WebKit.NetworkSession.new(data,cache); s.views={}; s.btns={}; s.cur=None
        bar=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10); bar.add_css_class('rh-bar')
        tabs=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10,homogeneous=True); tabs.set_hexpand(True)
        for tid,label,icon,page,_ in TABS:
            b=Gtk.Button(); b.add_css_class('rh-tab'); b.set_tooltip_text(label)
            bx=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8,halign=Gtk.Align.CENTER)
            bx.append(Gtk.Image.new_from_icon_name(icon)); bx.append(Gtk.Label(label=label)); b.set_child(bx)
            b.connect('clicked',lambda _b,t=tid: s.show(t)); tabs.append(b); s.btns[tid]=b
        bar.append(tabs)
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0,valign=Gtk.Align.CENTER)
        s.verl=Gtk.Label(label='Rig Hub v'+VER,xalign=1); s.verl.add_css_class('rh-ver')
        s.subl=Gtk.Label(label='',xalign=1); s.subl.add_css_class('rh-sub')
        vb.append(s.verl); vb.append(s.subl); bar.append(vb)
        s.stack=Gtk.Stack(); s.stack.set_vexpand(True); s.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL); root.append(bar); root.append(s.stack)
        w.set_child(root)
        start=os.environ.get('RIGHUB_TAB')
        if not start:
            try: start=open(LAST).read().strip()
            except Exception: start='home'
        if start not in s.btns: start='home'
        s.show(start); w.present()
    def view(s,tid):
        if tid in s.views: return s.views[tid]
        ucm=WebKit.UserContentManager()
        ucm.add_script(WebKit.UserScript.new(HOOK,WebKit.UserContentInjectedFrames.TOP_FRAME,WebKit.UserScriptInjectionTime.END,None,None))
        ucm.add_style_sheet(WebKit.UserStyleSheet.new(PAGECSS,WebKit.UserContentInjectedFrames.TOP_FRAME,WebKit.UserStyleLevel.USER,None,None))
        ucm.register_script_message_handler('tl',None); ucm.connect('script-message-received::tl',s.on_save)
        v=WebKit.WebView(network_session=s.session,user_content_manager=ucm)
        st=v.get_settings(); st.set_enable_javascript(True); st.set_allow_file_access_from_file_urls(True)
        if os.environ.get('RIGHUB_DEBUG'): st.set_enable_write_console_messages_to_stdout(True)
        st.set_user_agent_with_application_details('RigHub',VER)
        v.connect('permission-request',s.on_perm); v.connect('decide-policy',s.on_policy)
        v._tid=tid; s.views[tid]=v; s.stack.add_named(v,tid)
        page=[t[3] for t in TABS if t[0]==tid][0]
        v.load_uri('file://'+HERE+'/'+page)
        return v
    def show(s,tid):
        s.view(tid); s.stack.set_visible_child_name(tid); s.cur=tid
        for k,b in s.btns.items():
            if k==tid: b.add_css_class('on')
            else: b.remove_css_class('on')
        t=[x for x in TABS if x[0]==tid][0]
        s.subl.set_text(t[4]); s.subl.set_visible(bool(t[4]))
        s.win.set_title('Rig Hub v'+VER+(' — '+t[1] if tid!='home' else ''))
        try: open(LAST,'w').write(tid)
        except Exception: pass
    def on_perm(s,v,req):
        # Allow location (Rig Nav position and GPS shift miles when this computer has a location source).
        if isinstance(req,WebKit.GeolocationPermissionRequest): req.allow(); return True
        return False
    def on_policy(s,v,dec,typ):
        if typ in (WebKit.PolicyDecisionType.NAVIGATION_ACTION,WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            uri=dec.get_navigation_action().get_request().get_uri()
            if uri.startswith('http://') or uri.startswith('https://'):
                # Open outside links in the normal browser.
                Gtk.UriLauncher.new(uri).launch(s.win,None,None,None); dec.ignore(); return True
            pre='file://'+HERE+'/'
            if uri.startswith(pre):
                rel=uri[len(pre):].split('#')[0].split('?')[0] or 'index.html'
                if rel.endswith('/'): rel+='index.html'
                tid=PAGE.get(rel)
                # A link to another screen (home cards, "Rig Hub home") switches the tab instead of replacing this view.
                if tid and tid!=getattr(v,'_tid',None):
                    dec.ignore(); GLib.idle_add(lambda: (s.show(tid), False)[1]); return True
        return False
    def on_save(s,m,val):
        try: o=json.loads(val.to_string()); raw=base64.b64decode(o['b64'])
        except Exception: return
        d=Gtk.FileDialog(title='Save '+o['name'],initial_name=o['name'])
        dl=GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if dl and os.path.isdir(dl): d.set_initial_folder(Gio.File.new_for_path(dl))
        def done(dd,r):
            try: f=dd.save_finish(r)
            except GLib.Error: return
            if f: f.replace_contents(raw,None,False,Gio.FileCreateFlags.REPLACE_DESTINATION,None)
        d.save(s.win,None,done)
A().run(None)
