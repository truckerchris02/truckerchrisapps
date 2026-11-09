package com.truckerchris.righub;
import android.content.*;
public class WxBootReceiver extends BroadcastReceiver{public void onReceive(Context c,Intent i){WxChecker.schedule(c);WxChecker.apply(c);}}
