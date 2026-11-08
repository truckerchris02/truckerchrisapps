/* High Mile Tandem Slide v1.0 - calculator engine, ported line-for-line from Chris's Python calculate_tandem_shift(). */
(function(root){
var LEGAL_STEER=12000,LEGAL_DRIVES=34000,LEGAL_TANDEMS=34000,LEGAL_GROSS=80000;
function fmt(n){var s=String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g,',');return (n<0?'-':'')+s;}
function parseWeight(v){var s=String(v==null?'':v).trim().replace(/,/g,'');if(!/^[+-]?\d+$/.test(s))return null;return parseInt(s,10);}
function parseSpacing(v){var s=String(v==null?'':v).trim();return (s==='4'||s==='6')?parseInt(s,10):4;}
/* Returns {gross, status, items:[{kind,text}], plan:{...}|null, lines:[python-equivalent text lines]} */
function calc(steer,drives,tandems,spacing){
  spacing=spacing===6?6:(spacing===4?4:spacing);
  var gross=steer+drives+tandems,r={gross:gross,steer:steer,drives:drives,tandems:tandems,spacing:spacing,alerts:[],plan:null,returnToShipper:false,compliant:false},L=[];
  L.push('','='.repeat(50),' \u2696\ufe0f  CAT SCALE AUDIT & TANDEM SLIDE ANALYSIS','='.repeat(50));
  L.push('Current Weights: Steer: '+fmt(steer)+' lbs | Drives: '+fmt(drives)+' lbs | Tandems: '+fmt(tandems)+' lbs');
  L.push('Gross Vehicle Weight: '+fmt(gross)+' lbs');
  if(gross>LEGAL_GROSS){var og=gross-LEGAL_GROSS;r.returnToShipper=true;r.overGross=og;
    r.alerts.push({kind:'bad',text:'OVERWEIGHT VIOLATION: Gross is over legal limit by '+fmt(og)+' lbs!'});
    r.alerts.push({kind:'bad',text:'You cannot balance this out with a tandem slide. Return to shipper for rework.'});
    L.push('','\u26a0\ufe0f  OVERWEIGHT VIOLATION: Gross is over legal limit by '+fmt(og)+' lbs!','   You cannot balance this out with a tandem slide. Return to shipper for rework.');
    r.lines=L;return r;}
  var dOver=drives-LEGAL_DRIVES,tOver=tandems-LEGAL_TANDEMS;
  if(dOver<=0&&tOver<=0&&steer<=LEGAL_STEER){r.compliant=true;r.alerts.push({kind:'ok',text:'All axle groups and gross weight are legally compliant!'});L.push('','\u2705 All axle groups and gross weight are legally compliant!');}
  else{
    if(dOver>0){r.alerts.push({kind:'bad',text:'Drives are OVER legal limit by '+fmt(dOver)+' lbs.'});L.push('','\u26a0\ufe0f  Drives are OVER legal limit by '+fmt(dOver)+' lbs.');}
    if(tOver>0){r.alerts.push({kind:'bad',text:'Tandems are OVER legal limit by '+fmt(tOver)+' lbs.'});L.push('','\u26a0\ufe0f  Tandems are OVER legal limit by '+fmt(tOver)+' lbs.');}
    if(steer>LEGAL_STEER){var so='Steer axle is over standard 12,000 lbs by '+fmt(steer-LEGAL_STEER)+' lbs (check tire ratings).';r.alerts.push({kind:'warn',text:so});L.push('','\u26a0\ufe0f  '+so);}
  }
  var diff=drives-tandems,transfer=Math.floor(Math.abs(diff)/2),lph=(spacing===6)?450:300,holes=Math.ceil(transfer/lph),p={diff:diff,transfer:transfer,lbsPerHole:lph,holes:holes};
  L.push('','--- Adjustment Plan ---');
  if(diff>0){p.dir='FORWARD';p.target='Shift ~'+fmt(transfer)+' lbs off the drives onto the tandems.';p.action='Slide trailer tandems FORWARD (toward the cab) approx '+holes+' hole(s).';
    p.newDrives=drives-holes*lph;p.newTandems=tandems+holes*lph;
    L.push('\u2022 Target Transfer: '+p.target,'\u2022 Action: Slide trailer tandems **FORWARD** (toward the cab) approx '+holes+' hole(s).');}
  else if(diff<0){p.dir='BACK';p.target='Shift ~'+fmt(transfer)+' lbs off the tandems onto the drives.';p.action='Slide trailer tandems BACK (toward the rear doors) approx '+holes+' hole(s).';
    p.newDrives=drives+holes*lph;p.newTandems=tandems-holes*lph;
    L.push('\u2022 Target Transfer: '+p.target,'\u2022 Action: Slide trailer tandems **BACK** (toward the rear doors) approx '+holes+' hole(s).');}
  else{p.dir='NONE';p.action='Drives and tandems are already evenly balanced.';L.push('\u2022 Drives and tandems are already evenly balanced.');}
  if(p.dir!=='NONE'){p.expected='Drives: ~'+fmt(p.newDrives)+' lbs | Tandems: ~'+fmt(p.newTandems)+' lbs';L.push('\u2022 Expected Result: '+p.expected);}
  p.note='Calculated using standard '+spacing+'" pin spacing at ~'+lph+' lbs/hole. Always re-scale after pinning.';
  L.push('','('+p.note+')','='.repeat(50),'');
  r.plan=p;r.lines=L;return r;
}
var api={calc:calc,parseWeight:parseWeight,parseSpacing:parseSpacing,fmt:fmt,LIMITS:{steer:LEGAL_STEER,drives:LEGAL_DRIVES,tandems:LEGAL_TANDEMS,gross:LEGAL_GROSS},VERSION:'1.0'};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.TS=api;
})(this);
