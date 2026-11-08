package com.truckerchris.righub;
import android.app.*;import android.content.*;import android.os.*;import android.webkit.*;import android.graphics.Color;import android.graphics.Typeface;import android.view.*;import android.widget.*;import android.location.Location;import org.json.*;import java.lang.reflect.Method;
/** Rig Hub v1.6.0: Rig Nav, Trip Logger and Weather stay as they were. Tandem Slide is another tab that loads the existing calculator. */
public class HubActivity extends MainActivity {
  static final String VER="1.6.0";
  static final int ON=0xFFF5A623, OFF=0xFF8A93A3, BAR=0xFF11161F, SEL=0xFF1A2230;
  private WebView w, slide; private TextView tabWx, tabNav, tabLog, tabSlide;
  private boolean wxShown=false, wxLoaded=false, slideShown=false, slideLoaded=false; private String pendingWxTab=null;
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
  private void callShow(int i){try{Method m=MainActivity.class.getDeclaredMethod("show",int.class);m.setAccessible(true);m.invoke(this,i);}catch(Exception e){}}
  private void dim(TextView t){if(t!=null){t.setTextColor(OFF);t.setBackgroundColor(BAR);}}
  private void styleTab(TextView t){t.setGravity(Gravity.CENTER);t.setTypeface(Typeface.DEFAULT_BOLD);t.setTextSize(TypedValueSp(),12f);t.setMaxLines(2);}
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
      slide=new WebView(this);slide.setBackgroundColor(Color.parseColor("#14171c"));slide.setVisibility(View.INVISIBLE);
      WebSettings ss=slide.getSettings();ss.setJavaScriptEnabled(true);ss.setDomStorageEnabled(true);ss.setAllowFileAccess(true);ss.setTextZoom(100);ss.setMediaPlaybackRequiresUserGesture(false);
      slide.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !r.getUrl().toString().startsWith("file:///android_asset/");}});
      frame.addView(slide,new FrameLayout.LayoutParams(-1,-1));
      if(b!=null&&b.getBoolean("slide",false)){try{if(slide.restoreState(b)!=null)slideLoaded=true;}catch(Exception e){}}
      tabWx=new TextView(this);tabWx.setText("⛈  Weather");
      tabSlide=new TextView(this);tabSlide.setText("\u2696  Tandem");tabSlide.setContentDescription("Tandem Slide");
      int taller=(int)android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_DIP,56,getResources().getDisplayMetrics());
      bar.addView(tabWx,new LinearLayout.LayoutParams(0,taller,1f));
      bar.addView(tabSlide,new LinearLayout.LayoutParams(0,taller,1f));
      for(TextView t:new TextView[]{tabNav,tabLog,tabWx,tabSlide}){ViewGroup.LayoutParams lp=t.getLayoutParams();lp.height=taller;t.setLayoutParams(lp);styleTab(t);}
      tabNav.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showOrig(0);}});
      tabLog.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showOrig(1);}});
      tabWx.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showWx(null);}});
      tabSlide.setOnClickListener(new View.OnClickListener(){public void onClick(View v){showSlide();}});
      dim(tabWx);dim(tabSlide);
      WxChecker.channels(this);WxChecker.schedule(this);WxChecker.apply(this);
      String t=getIntent().getStringExtra("tab");
      boolean wasSlide=(b!=null&&b.getBoolean("slide",false))||(b==null&&hp().getBoolean("slide",false));
      boolean wasWx=(b!=null&&b.getBoolean("wx",false))||(b==null&&hp().getBoolean("wx",false));
      if(t!=null)showWx(t); else if(wasSlide)showSlide(); else if(wasWx)showWx(null);
    }catch(Exception e){android.util.Log.e("RigHub","tab setup failed",e);}
  }
  private int TypedValueSp(){return android.util.TypedValue.COMPLEX_UNIT_SP;}
  private void showOrig(int i){wxShown=false;slideShown=false;if(w!=null)w.setVisibility(View.INVISIBLE);if(slide!=null)slide.setVisibility(View.INVISIBLE);dim(tabWx);dim(tabSlide);hp().edit().putBoolean("wx",false).putBoolean("slide",false).apply();callShow(i);}
  private void showWx(String tab){
    wxShown=true;slideShown=false;
    ViewGroup frame=(ViewGroup)w.getParent();for(int i=0;i<frame.getChildCount();i++){View c=frame.getChildAt(i);c.setVisibility(c==w?View.VISIBLE:View.INVISIBLE);}
    dim(tabNav);dim(tabLog);dim(tabSlide);tabWx.setTextColor(ON);tabWx.setBackgroundColor(SEL);
    hp().edit().putBoolean("wx",true).putBoolean("slide",false).apply();
    if(!wxLoaded){wxLoaded=true;w.loadUrl("file:///android_asset/weather/index.html"+(tab!=null?"#"+tab:""));}
    else if(tab!=null)js("window.show&&show('"+tab+"')");
    else js("window.__resume&&window.__resume()");
  }
  private void showSlide(){
    slideShown=true;wxShown=false;
    ViewGroup frame=(ViewGroup)slide.getParent();for(int i=0;i<frame.getChildCount();i++){View c=frame.getChildAt(i);c.setVisibility(c==slide?View.VISIBLE:View.INVISIBLE);}
    dim(tabNav);dim(tabLog);dim(tabWx);tabSlide.setTextColor(ON);tabSlide.setBackgroundColor(SEL);
    hp().edit().putBoolean("wx",false).putBoolean("slide",true).apply();
    if(!slideLoaded){slideLoaded=true;slide.loadUrl("file:///android_asset/tandem/index.html");}
  }
  @Override protected void onSaveInstanceState(Bundle b){super.onSaveInstanceState(b);b.putBoolean("wx",wxShown);b.putBoolean("slide",slideShown);if(slide!=null&&slideShown)try{slide.saveState(b);}catch(Exception e){}}
  @Override protected void onNewIntent(Intent i){super.onNewIntent(i);String t=i.getStringExtra("tab");if(t!=null&&w!=null)showWx(t);}
  @Override public void onRequestPermissionsResult(int rc,String[] p,int[] g){
    if(rc>=100&&rc<200){WxChecker.apply(this);js("window.__perm&&window.__perm()");return;}
    super.onRequestPermissionsResult(rc,p,g);WxChecker.apply(this);js("window.__perm&&window.__perm()");}
  @Override protected void onResume(){super.onResume();if(w!=null){w.onResume();if(wxShown)js("window.__resume&&window.__resume()");}if(slide!=null)slide.onResume();}
  @Override protected void onPause(){if(w!=null)w.onPause();if(slide!=null)slide.onPause();super.onPause();}
  @Override public void onBackPressed(){
    if(slideShown){slide.evaluateJavascript("(window.__back&&window.__back())?'1':'0'",new ValueCallback<String>(){public void onReceiveValue(String v){if(v==null||!v.contains("1"))showOrig(0);}});}
    else if(wxShown){if(w.canGoBack())w.goBack();else showOrig(0);}else super.onBackPressed();}
}
