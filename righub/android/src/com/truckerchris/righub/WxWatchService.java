package com.truckerchris.righub;
import android.app.*;import android.content.*;import android.os.*;import android.location.*;
public class WxWatchService extends Service{
  Handler h;HandlerThread t;LocationManager lm;Location lastLoc;long lastRun;
  LocationListener move=new LocationListener(){public void onLocationChanged(Location l){if(lastLoc==null||l.distanceTo(lastLoc)>16000||System.currentTimeMillis()-lastRun>14*60000)run(l);}
    public void onStatusChanged(String p,int s,Bundle b){}public void onProviderEnabled(String p){}public void onProviderDisabled(String p){}};
  Runnable tick=new Runnable(){public void run(){WxWatchService.this.run(null);h.postDelayed(this,15*60000);}};
  void run(Location l){lastRun=System.currentTimeMillis();WxChecker.check(this,l);Location x=WxChecker.last(this);if(x!=null)lastLoc=x;if(l!=null)lastLoc=l;}
  public IBinder onBind(Intent i){return null;}
  public int onStartCommand(Intent i,int f,int id){WxChecker.channels(this);
    Intent oi=new Intent(this,HubActivity.class);PendingIntent pi=PendingIntent.getActivity(this,1,oi,PendingIntent.FLAG_IMMUTABLE);
    Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,"watch"):new Notification.Builder(this);
    b.setSmallIcon(R.drawable.ic_stat).setContentTitle("Rig Hub Weather").setContentText("Watching weather near you").setOngoing(true).setContentIntent(pi);
    if(Build.VERSION.SDK_INT<26)b.setPriority(Notification.PRIORITY_MIN);
    try{if(Build.VERSION.SDK_INT>=29)startForeground(4242,b.build(),android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);else startForeground(4242,b.build());}
    catch(Exception e){WxChecker.schedule(this);stopSelf();return START_NOT_STICKY;}
    if(t==null){t=new HandlerThread("watch");t.start();h=new Handler(t.getLooper());lm=(LocationManager)getSystemService(LOCATION_SERVICE);
      try{for(String p:new String[]{LocationManager.NETWORK_PROVIDER,LocationManager.GPS_PROVIDER})if(lm.isProviderEnabled(p))lm.requestLocationUpdates(p,5*60000,3000,move,t.getLooper());}catch(Exception e){}
      h.post(tick);}
    return START_STICKY;}
  public void onDestroy(){try{lm.removeUpdates(move);}catch(Exception e){}if(h!=null)h.removeCallbacksAndMessages(null);if(t!=null)t.quitSafely();t=null;super.onDestroy();}
}
