package com.truckerchris.righub;
import android.content.*;import android.location.*;import android.app.*;import android.os.*;import org.json.*;import java.util.*;
public class WxChecker{
  public static final String UA="RigHub/1.6.0 (trucker.chris02@gmail.com)";
  public static SharedPreferences sp(Context c){return c.getSharedPreferences("righub_wx",0);}
  public static String http(String url)throws Exception{java.net.HttpURLConnection c=(java.net.HttpURLConnection)new java.net.URL(url).openConnection();c.setConnectTimeout(15000);c.setReadTimeout(20000);c.setRequestProperty("User-Agent",UA);c.setRequestProperty("Accept","application/geo+json, application/json");
    int code=c.getResponseCode();java.io.InputStream in=code<400?c.getInputStream():c.getErrorStream();java.io.ByteArrayOutputStream bo=new java.io.ByteArrayOutputStream();byte[] b=new byte[16384];int n;if(in!=null){while((n=in.read(b))>0)bo.write(b,0,n);in.close();}
    String s=bo.toString("UTF-8");if(code>=400)throw new Exception("HTTP "+code);return s;}
  public static boolean hasLoc(Context c){return Build.VERSION.SDK_INT<23||c.checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION)==0||c.checkSelfPermission(android.Manifest.permission.ACCESS_COARSE_LOCATION)==0;}
  public static Location last(Context c){if(!hasLoc(c))return null;LocationManager lm=(LocationManager)c.getSystemService(Context.LOCATION_SERVICE);Location best=null;
    for(String p:lm.getProviders(true)){try{Location l=lm.getLastKnownLocation(p);if(l!=null&&(best==null||l.getTime()>best.getTime()))best=l;}catch(SecurityException e){}}return best;}
  /** blocking fresh fix (call off main thread), up to timeout ms */
  public static Location fresh(Context c,long timeout){if(!hasLoc(c))return null;final LocationManager lm=(LocationManager)c.getSystemService(Context.LOCATION_SERVICE);final Location[] out={null};final Object lock=new Object();
    HandlerThread ht=new HandlerThread("loc");ht.start();
    final LocationListener li=new LocationListener(){public void onLocationChanged(Location l){synchronized(lock){if(out[0]==null||l.getAccuracy()<out[0].getAccuracy())out[0]=l;lock.notifyAll();}}
      public void onStatusChanged(String p,int s,Bundle b){}public void onProviderEnabled(String p){}public void onProviderDisabled(String p){}};
    try{for(String p:new String[]{LocationManager.GPS_PROVIDER,LocationManager.NETWORK_PROVIDER})if(lm.isProviderEnabled(p))lm.requestLocationUpdates(p,0,0,li,ht.getLooper());}catch(Exception e){}
    synchronized(lock){long end=System.currentTimeMillis()+timeout;while(out[0]==null&&System.currentTimeMillis()<end){try{lock.wait(Math.max(1,end-System.currentTimeMillis()));}catch(InterruptedException e){break;}}}
    try{lm.removeUpdates(li);}catch(Exception e){}ht.quitSafely();
    Location l=out[0];if(l==null)l=last(c);return l;}
  public static void channels(Context c){if(Build.VERSION.SDK_INT<26)return;NotificationManager nm=(NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE);
    NotificationChannel a=new NotificationChannel("alerts2","Severe weather alerts",NotificationManager.IMPORTANCE_HIGH);a.enableVibration(true);a.setVibrationPattern(new long[]{0,800,300,800,300,800});a.enableLights(true);
    a.setSound(android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_ALARM),new android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_ALARM).setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION).build());
    a.setBypassDnd(true);nm.createNotificationChannel(a);
    NotificationChannel w=new NotificationChannel("watch","Watching weather (ongoing)",NotificationManager.IMPORTANCE_MIN);w.setShowBadge(false);nm.createNotificationChannel(w);}
  static int rank(String s){if(s==null)return 0;switch(s){case "Extreme":return 4;case "Severe":return 3;case "Moderate":return 2;case "Minor":return 1;default:return 0;}}
  /** One full check; returns summary string. */
  public static synchronized String check(Context c,Location l){SharedPreferences p=sp(c);
    if(l==null)l=fresh(c,30000);if(l==null){p.edit().putString("lastErr","No location fix").apply();return "noloc";}
    double la=Math.round(l.getLatitude()*10000)/10000.0,lo=Math.round(l.getLongitude()*10000)/10000.0;
    p.edit().putString("lat",""+la).putString("lon",""+lo).putLong("locTime",l.getTime()).apply();
    try{JSONArray f=new JSONObject(http("https://api.weather.gov/alerts/active?point="+la+","+lo)).getJSONArray("features");
      int min=p.getInt("minSev",3);boolean watches=p.getBoolean("watches",true),adv=p.getBoolean("adv",false);
      Set<String> seen=new HashSet<String>(p.getStringSet("seen",new HashSet<String>()));Set<String> now=new HashSet<String>();
      NotificationManager nm=(NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE);channels(c);
      for(int i=0;i<f.length();i++){JSONObject a=f.getJSONObject(i).getJSONObject("properties");String id=a.optString("id");now.add(id);
        String ev=a.optString("event");String sev=a.optString("severity");boolean isWarn=ev.contains("Warning"),isWatch=ev.contains("Watch"),isAdv=ev.contains("Advisory")||ev.contains("Statement");
        boolean want=rank(sev)>=min&&(isWarn||(isWatch&&watches)||(isAdv&&adv)||ev.contains("Emergency"));
        if(!want&&isWatch&&watches&&rank(sev)>=2)want=true;
        if(!want||seen.contains(id))continue;
        Intent oi=new Intent(c,HubActivity.class);oi.putExtra("tab","alerts");oi.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi=PendingIntent.getActivity(c,id.hashCode(),oi,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(c,"alerts2"):new Notification.Builder(c);
        String body=a.optString("headline");String desc=a.optString("description");
        b.setSmallIcon(R.drawable.ic_stat).setContentTitle("⚠ "+ev).setContentText(body).setStyle(new Notification.BigTextStyle().bigText(body+"\n\n"+desc)).setContentIntent(pi).setAutoCancel(true).setCategory(Notification.CATEGORY_ALARM).setColor(0xFFFFCC00);
        if(Build.VERSION.SDK_INT<26){b.setPriority(Notification.PRIORITY_MAX);b.setDefaults(Notification.DEFAULT_ALL);}
        try{nm.notify(id.hashCode(),b.build());}catch(Exception e){}}
      Set<String> keep=new HashSet<String>(seen);keep.retainAll(now);for(String s:now)keep.add(s); // remember only still-active
      // mark all currently active as seen so they don't re-fire
      p.edit().putStringSet("seen",keep).putLong("lastCheck",System.currentTimeMillis()).putInt("lastCount",f.length()).remove("lastErr").apply();
      return "ok";}
    catch(Exception e){p.edit().putString("lastErr",String.valueOf(e.getMessage())).apply();return "err";}}
  public static void schedule(Context c){AlarmManager am=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);PendingIntent pi=PendingIntent.getBroadcast(c,7,new Intent(c,WxAlarmReceiver.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
    am.cancel(pi);if(sp(c).getBoolean("alarm",true))am.setInexactRepeating(AlarmManager.ELAPSED_REALTIME_WAKEUP,SystemClock.elapsedRealtime()+15*60000,AlarmManager.INTERVAL_FIFTEEN_MINUTES,pi);}
  public static void apply(Context c){Intent s=new Intent(c,WxWatchService.class);
    if(sp(c).getBoolean("watch",true)&&hasLoc(c)){try{if(Build.VERSION.SDK_INT>=26)c.startForegroundService(s);else c.startService(s);}catch(Exception e){schedule(c);}}
    else{c.stopService(s);schedule(c);}}
}
