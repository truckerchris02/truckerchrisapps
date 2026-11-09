package com.truckerchris.righub;
import android.app.*;import android.content.*;import android.os.*;import android.webkit.*;import android.graphics.Color;import android.graphics.Typeface;import android.view.*;import android.widget.*;import android.location.Location;import android.net.Uri;import org.json.*;import java.lang.reflect.Method;
/** Rig Hub v1.7.0. Row 1 is Rig Nav, Trip Logger, Weather. Row 2 is Tandem Slide, Hazmat Helper, and the truck/trailer inspection. */
public class HubActivity extends MainActivity {
  static final String VER="1.7.0";
  static final int ON=0xFFF5A623, OFF=0xFF8A93A3, BAR=0xFF11161F, SEL=0xFF1A2230;
  static final int REQ_INSP_FILE=140;
  /** Same download hook the standalone inspection app injects, so Save still writes a file. */
  static final String INSP_DOWNLOAD="(function(){if (!window.AndroidBridge || typeof window.downloadBlob !== 'function') return;if (window.__inspectionDownloadOverridden) return;window.__inspectionDownloadOverridden = true;var __origDownloadBlob = window.downloadBlob;window.downloadBlob = function(blob, filename){  if (!(blob instanceof Blob)) { __origDownloadBlob(blob, filename); return; }  var reader = new FileReader();  reader.onloadend = function(){    var result = reader.result || '';    var comma = result.indexOf(',');    var b64 = comma >= 0 ? result.substring(comma + 1) : result;    window.AndroidBridge.saveFile(b64, filename, blob.type || 'application/octet-stream');  };  reader.onerror = function(){ __origDownloadBlob(blob, filename); };  reader.readAsDataURL(blob);};})();";
  private WebView w, slide, haz, insp;
  private TextView tabWx, tabNav, tabLog, tabSlide, tabHaz, tabInsp;
  private boolean wxShown=false, wxLoaded=false, slideShown=false, slideLoaded=false, hazShown=false, hazLoaded=false, inspShown=false, inspLoaded=false;
  private String pendingWxTab=null;
  private ValueCallback<Uri[]> inspFile;
  void js(final String s){runOnUiThread(new Runnable(){public void run(){if(w!=null)w.evaluateJavascript(s,null);}});}
  boolean granted(String p){return checkSelfPermission(p)==0;}
  SharedPreferences hp(){return getSharedPreferences("righub_hub",0);}
  public class Bridge{
    @JavascriptInterface public void get(final int id,final String url){new Thread(new Runnable(){public void run(){boolean ok=false;String body;
      try{body=WxChecker.http(url);ok=true;}catch(Exception e){body=String.valueOf(e.getMessage());}
      js("window.__got("+id+","+ok+","+JSONObject.quote(body)+")");}}).start();}
    @JavascriptInterface public void locate(final int id){new Thread(new Runnable(){public void run(){Location l=WxChecker.fresh(HubActivity.this,15000);
      String r=l==null?"null":"{\"lat\":"+l.getLatitude()+",\"lon\":"+l.getLongitude()+",\"acc\":"+l.getAccuracy()+",\"time\":"+l.getTime()+"}";
      js("window.__got("+id+","+(l!=null)+","+JSONObject.quote(r)+")");}}).start();}
    @JavascriptInterface public String perms(){try{JSONObject o=new JSONObject();o.put("loc",granted(android.Manifest.permission.ACCESS_FINE_LOCATION)||granted(android.Manifest.permission.ACCESS_COARSE_LOCATION));
      o.put("fine",granted(android.Manifest.permission.ACCESS_FINE_LOCATION));o.put("bg",granted("android.permission.ACCESS_BACKGROUND_LOCATION"));
      o.put("notif",Build.VERSION.SDK_INT<33||granted("android.permission.POST_NOTIFICATIONS"));
      PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);o.put("battery",pm.isIgnoringBatteryOptimizations(getPackageName()));o.put("sdk",Build.VERSION.SDK_INT);return o.toString();}catch(Exception e){return "{}";}}
    @JavascriptInterface public void ask(String what){
      if(what.equals("loc"))requestPermissions(new String[]{android.Manifest.permission.ACCESS_FINE_LOCATION,android.Manifest.permission.ACCESS_COARSE_LOCATION},101);
      else if(what.equals("bg"))requestPermissions(new String[]{"android.permission.ACCESS_BACKGROUND_LOCATION"},102);
      else if(what.equals("notif")){if(Build.VERSION.SDK_INT>=33)requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},103);}
      else if(what.equals("settings")){startActivity(new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,android.net.Uri.parse("package:"+getPackageName())));}
      else if(what.equals("battery")){try{startActivity(new Intent(android.provider.Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));}catch(Exception e){ask("settings");}}}
    @JavascriptInterface public String prefs(){SharedPreferences p=WxChecker.sp(HubActivity.this);try{JSONObject o=new JSONObject();o.put("watch",p.getBoolean("watch",true));o.put("alarm",p.getBoolean("alarm",true));
      o.put("minSev",p.getInt("minSev",3));o.put("watches",p.getBoolean("watches",true));o.put("adv",p.getBoolean("adv",false));o.put("lastCheck",p.getLong("lastCheck",0));
      o.put("lastErr",p.getString("lastErr",""));o.put("lat",p.getString("lat",""));o.put("lon",p.getString("lon",""));return o.toString();}catch(Exception e){return "{}";}}
    @JavascriptInterface public void setBool(String k,boolean v){WxChecker.sp(HubActivity.this).edit().putBoolean(k,v).apply();if(k.equals("watch")||k.equals("alarm")){WxChecker.schedule(HubActivity.this);WxChecker.apply(HubActivity.this);}}
    @JavascriptInterface public void setInt(String k,int v){WxChecker.sp(HubActivity.this).edit().putInt(k,v).apply();}
    @JavascriptInterface public void checkNow(final int id){new Thread(new Runnable(){public void run(){String r=WxChecker.check(HubActivity.this,null);js("window.__got("+id+",true,"+JSONObject.quote("\""+r+"\"")+")");}}).start();}
    @JavascriptInterface public void test(){WxChecker.channels(HubActivity.this);NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
      Notification.Builder b=new Notification.Builder(HubActivity.this,"alerts2");
      b.setSmallIcon(R.drawable.ic_stat).setContentTitle("⚠ Test alert").setContentText("This is how a severe weather alert will look and sound.").setAutoCancel(true).setColor(0xFFFFCC00);nm.notify(999,b.build());}
    @JavascriptInterface public void open(String u){try{startActivity(new Intent(Intent.ACTION_VIEW,android.net.Uri.parse(u)));}catch(Exception e){}}
  }
  /** Saves inspection downloads to the same Downloads folder the standalone inspection app uses. */
  public class InspBridge{
    @JavascriptInterface public void saveFile(String b64,String name,String mime){
      String safe=sanitize(name);
      String msg;
      try{
        byte[] raw=android.util.Base64.decode(b64==null?"":b64,0);
        ContentResolver cr=getContentResolver();
        ContentValues cv=new ContentValues();
        cv.put("_display_name",safe);
        if(mime==null||mime.isEmpty())mime="application/octet-stream";
        cv.put("mime_type",mime);
        cv.put("relative_path",Environment.DIRECTORY_DOWNLOADS);
        cv.put("is_pending",1);
        Uri uri=cr.insert(android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI,cv);
        if(uri==null)throw new IllegalStateException("MediaStore insert returned null");
        java.io.OutputStream out=cr.openOutputStream(uri);
        if(out==null)throw new IllegalStateException("Could not open output stream");
        try{out.write(raw);}finally{out.close();}
        cv.clear();cv.put("is_pending",0);cr.update(uri,cv,null,null);
        msg="Saved to Downloads: "+safe;
      }catch(Exception e){msg="Save failed: "+e.getMessage();}
      final String toast=msg;
      runOnUiThread(new Runnable(){public void run(){Toast.makeText(HubActivity.this,toast,Toast.LENGTH_LONG).show();}});
    }
    private String sanitize(String name){
      if(name==null||name.trim().isEmpty())return "inspection.bin";
      String s=name.trim().replace('/','_').replace('\\','_');
      while(s.contains(".."))s=s.replace("..","_");
      return s;
    }
  }
  private void callShow(int i){try{Method m=MainActivity.class.getDeclaredMethod("show",int.class);m.setAccessible(true);m.invoke(this,i);}catch(Exception e){}}
  private void dim(TextView t){if(t!=null){t.setTextColor(OFF);t.setBackgroundColor(BAR);}}
  private void styleTab(TextView t,float sp){t.setGravity(Gravity.CENTER);t.setTypeface(Typeface.DEFAULT_BOLD);t.setTextSize(TypedValueSp(),sp);t.setMaxLines(2);}
  private WebView makePage(String bg){
    WebView v=new WebView(this);v.setBackgroundColor(Color.parseColor(bg));v.setVisibility(View.INVISIBLE);
    WebSettings s=v.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(true);s.setTextZoom(100);s.setMediaPlaybackRequiresUserGesture(false);
    return v;
  }
  private void remember(){hp().edit().putBoolean("wx",wxShown).putBoolean("slide",slideShown).putBoolean("haz",hazShown).putBoolean("insp",inspShown).apply();}
  private void hideTools(){if(w!=null)w.setVisibility(View.INVISIBLE);if(slide!=null)slide.setVisibility(View.INVISIBLE);if(haz!=null)haz.setVisibility(View.INVISIBLE);if(insp!=null)insp.setVisibility(View.INVISIBLE);}
  @Override protected void onCreate(Bundle b){
    super.onCreate(b);
    try{
      LinearLayout root=(LinearLayout)((ViewGroup)findViewById(android.R.id.content)).getChildAt(0);
      FrameLayout frame=(FrameLayout)root.getChildAt(0); LinearLayout bar=(LinearLayout)root.getChildAt(1);
      tabNav=(TextView)bar.getChildAt(0); tabLog=(TextView)bar.getChildAt(1);
      w=new WebView(this);w.setBackgroundColor(Color.parseColor("#0A1226"));w.setVisibility(View.INVISIBLE);
      WebSettings s=w.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(true);s.setTextZoom(100);s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);s.setUserAgentString(s.getUserAgentString()+" RigHub/"+VER);
      w.addJavascriptInterface(new Bridge(),"AndroidBridge");
      w.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){String u=r.getUrl().toString();if(u.startsWith("file:///android_asset/"))return false;try{startActivity(new Intent(Intent.ACTION_VIEW,r.getUrl()));}catch(Exception e){}return true;}});
      frame.addView(w,new FrameLayout.LayoutParams(-1,-1));
      slide=makePage("#14171c");
      slide.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !r.getUrl().toString().startsWith("file:///android_asset/");}});
      frame.addView(slide,new FrameLayout.LayoutParams(-1,-1));
      haz=makePage("#14171c");
      haz.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !r.getUrl().toString().startsWith("file:///android_asset/");}});
      frame.addView(haz,new FrameLayout.LayoutParams(-1,-1));
      insp=makePage("#1a1d21");
      WebSettings is=insp.getSettings();is.setAllowFileAccessFromFileURLs(true);is.setAllowContentAccess(true);
      insp.addJavascriptInterface(new InspBridge(),"AndroidBridge");
      insp.setWebViewClient(new WebViewClient(){
        @Override public void onPageFinished(WebView v,String url){v.evaluateJavascript(INSP_DOWNLOAD,null);}
        @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){
          android.net.Uri u=r.getUrl();String sch=u.getScheme();
          if("mailto".equalsIgnoreCase(sch)){try{startActivity(Intent.createChooser(new Intent(Intent.ACTION_SENDTO,u),"Email report"));}catch(Exception e){}return true;}
          if("http".equalsIgnoreCase(sch)||"https".equalsIgnoreCase(sch)){try{startActivity(new Intent(Intent.ACTION_VIEW,u));}catch(Exception e){}return true;}
          return false;
        }
      });
      insp.setWebChromeClient(new WebChromeClient(){
        @Override public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> cb,FileChooserParams p){
          if(inspFile!=null)inspFile.onReceiveValue(null);
          inspFile=cb;
          Intent i=new Intent(Intent.ACTION_GET_CONTENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");
          try{startActivityForResult(Intent.createChooser(i,"Select inspection file"),REQ_INSP_FILE);return true;}catch(Exception e){inspFile=null;return false;}
        }
      });
      frame.addView(insp,new FrameLayout.LayoutParams(-1,-1));
      if(b!=null&&b.getBoolean("slide",false)){try{if(slide.restoreState(b)!=null)slideLoaded=true;}catch(Exception e){}}
      if(b!=null&&b.getBoolean("haz",false)){try{if(haz.restoreState(b)!=null)hazLoaded=true;}catch(Exception e){}}
      if(b!=null&&b.getBoolean("insp",false)){try{if(insp.restoreState(b)!=null)inspLoaded=true;}catch(Exception e){}}
      tabWx=new TextView(this);tabWx.setText("⛈  Weather");
      tabSlide=new TextView(this);tabSlide.setText("\u2696  Tandem");tabSlide.setContentDescription("Tandem Slide");
      tabHaz=new TextView(this);tabHaz.setText("\u2622  Hazmat");tabHaz.setContentDescription("Hazmat Helper");
      tabInsp=new TextView(this);tabInsp.setText("\u2611  Inspect");tabInsp.setContentDescription("Truck and Trailer Inspection");
      int rowH=(int)android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_DIP,52,getResources().getDisplayMetrics());
      bar.addView(tabWx,new LinearLayout.LayoutParams(0,rowH,1f));
      LinearLayout row2=new LinearLayout(this);row2.setOrientation(LinearLayout.HORIZONTAL);row2.setBackgroundColor(BAR);
      row2.addView(tabSlide,new LinearLayout.LayoutParams(0,rowH,1f));
      row2.addView(tabHaz,new LinearLayout.LayoutParams(0,rowH,1f));
      row2.addView(tabInsp,new LinearLayout.LayoutParams(0,rowH,1f));
      root.addView(row2,new LinearLayout.LayoutParams(-1,-2));
      for(TextView t:new TextView[]{tabNav,tabLog,tabWx}){ViewGroup.LayoutParams lp=t.getLayoutParams();lp.height=rowH;t.setLayoutParams(lp);styleTab(t,14f);}
      for(TextView t:new TextView[]{tabSlide,tabHaz,tabInsp})styleTab(t,14f);
      tabNav.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showOrig(0);}});
      tabLog.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showOrig(1);}});
      tabWx.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showWx(null);}});
      tabSlide.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showSlide();}});
      tabHaz.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showHaz();}});
      tabInsp.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showInsp();}});
      dim(tabWx);dim(tabSlide);dim(tabHaz);dim(tabInsp);
      WxChecker.channels(this);WxChecker.schedule(this);WxChecker.apply(this);
      String t=getIntent().getStringExtra("tab");
      boolean wasSlide=(b!=null&&b.getBoolean("slide",false))||(b==null&&hp().getBoolean("slide",false));
      boolean wasHaz=(b!=null&&b.getBoolean("haz",false))||(b==null&&hp().getBoolean("haz",false));
      boolean wasInsp=(b!=null&&b.getBoolean("insp",false))||(b==null&&hp().getBoolean("insp",false));
      boolean wasWx=(b!=null&&b.getBoolean("wx",false))||(b==null&&hp().getBoolean("wx",false));
      if(t!=null)showWx(t); else if(wasInsp)showInsp(); else if(wasHaz)showHaz(); else if(wasSlide)showSlide(); else if(wasWx)showWx(null);
    }catch(Exception e){android.util.Log.e("RigHub","tab setup failed",e);}
  }
  private int TypedValueSp(){return android.util.TypedValue.COMPLEX_UNIT_SP;}
  private void dimTools(){dim(tabWx);dim(tabSlide);dim(tabHaz);dim(tabInsp);}
  private void showOrig(int i){wxShown=false;slideShown=false;hazShown=false;inspShown=false;hideTools();dimTools();remember();callShow(i);}
  private void showOnly(WebView view){ViewGroup frame=(ViewGroup)view.getParent();for(int i=0;i<frame.getChildCount();i++){View c=frame.getChildAt(i);c.setVisibility(c==view?View.VISIBLE:View.INVISIBLE);}}
  private void showWx(String tab){
    wxShown=true;slideShown=false;hazShown=false;inspShown=false;
    showOnly(w);dim(tabNav);dim(tabLog);dimTools();tabWx.setTextColor(ON);tabWx.setBackgroundColor(SEL);remember();
    if(!wxLoaded){wxLoaded=true;w.loadUrl("file:///android_asset/weather/index.html"+(tab!=null?"#"+tab:""));}
    else if(tab!=null)js("window.show&&show('"+tab+"')");
    else js("window.__resume&&window.__resume()");
  }
  private void showSlide(){
    slideShown=true;wxShown=false;hazShown=false;inspShown=false;
    showOnly(slide);dim(tabNav);dim(tabLog);dimTools();tabSlide.setTextColor(ON);tabSlide.setBackgroundColor(SEL);remember();
    if(!slideLoaded){slideLoaded=true;slide.loadUrl("file:///android_asset/tandem/index.html");}
  }
  private void showHaz(){
    hazShown=true;wxShown=false;slideShown=false;inspShown=false;
    showOnly(haz);dim(tabNav);dim(tabLog);dimTools();tabHaz.setTextColor(ON);tabHaz.setBackgroundColor(SEL);remember();
    if(!hazLoaded){hazLoaded=true;haz.loadUrl("file:///android_asset/hazmat/index.html");}
  }
  private void showInsp(){
    inspShown=true;wxShown=false;slideShown=false;hazShown=false;
    showOnly(insp);dim(tabNav);dim(tabLog);dimTools();tabInsp.setTextColor(ON);tabInsp.setBackgroundColor(SEL);remember();
    if(!inspLoaded){inspLoaded=true;insp.loadUrl("file:///android_asset/inspection/index.html");}
  }
  private void consumeBack(final WebView view){
    view.evaluateJavascript("(window.__back&&window.__back())?'1':'0'",new ValueCallback<String>(){public void onReceiveValue(String v){if(v==null||!v.contains("1"))showOrig(0);}});
  }
  @Override protected void onSaveInstanceState(Bundle b){
    super.onSaveInstanceState(b);b.putBoolean("wx",wxShown);b.putBoolean("slide",slideShown);b.putBoolean("haz",hazShown);b.putBoolean("insp",inspShown);
    try{if(slide!=null&&slideShown)slide.saveState(b);else if(haz!=null&&hazShown)haz.saveState(b);else if(insp!=null&&inspShown)insp.saveState(b);}catch(Exception e){}
  }
  @Override protected void onNewIntent(Intent i){super.onNewIntent(i);String t=i.getStringExtra("tab");if(t!=null&&w!=null)showWx(t);}
  @Override public void onRequestPermissionsResult(int rc,String[] p,int[] g){
    if(rc>=100&&rc<200){WxChecker.apply(this);js("window.__perm&&window.__perm()");return;}
    super.onRequestPermissionsResult(rc,p,g);WxChecker.apply(this);js("window.__perm&&window.__perm()");}
  @Override protected void onActivityResult(int req,int res,Intent data){
    if(req==REQ_INSP_FILE){
      if(inspFile!=null){Uri[] u=null;if(res==-1&&data!=null&&data.getData()!=null)u=new Uri[]{data.getData()};inspFile.onReceiveValue(u);inspFile=null;}
      return;
    }
    super.onActivityResult(req,res,data);
  }
  @Override protected void onResume(){super.onResume();if(w!=null){w.onResume();if(wxShown)js("window.__resume&&window.__resume()");}if(slide!=null)slide.onResume();if(haz!=null)haz.onResume();if(insp!=null)insp.onResume();}
  @Override protected void onPause(){if(w!=null)w.onPause();if(slide!=null)slide.onPause();if(haz!=null)haz.onPause();if(insp!=null)insp.onPause();super.onPause();}
  @Override public void onBackPressed(){
    if(slideShown)consumeBack(slide);
    else if(hazShown)consumeBack(haz);
    else if(inspShown){if(insp.canGoBack())insp.goBack();else showOrig(0);}
    else if(wxShown){if(w.canGoBack())w.goBack();else showOrig(0);}
    else super.onBackPressed();
  }
}
