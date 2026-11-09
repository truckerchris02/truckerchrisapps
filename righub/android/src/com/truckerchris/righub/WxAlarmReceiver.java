package com.truckerchris.righub;
import android.content.*;
public class WxAlarmReceiver extends BroadcastReceiver{public void onReceive(final Context c,Intent i){final PendingResult r=goAsync();
  new Thread(new Runnable(){public void run(){try{WxChecker.check(c,WxChecker.fresh(c,20000));}finally{r.finish();}}}).start();}}
