/* Hazmat Helper engine v1.0 - rules from 49 CFR 177.848, 172.504, 172.505 (eCFR as of 2026-10-23) */
(function(G){
var SEG_KEYS=['1.1/1.2','1.3','1.4','1.5','1.6','2.1','2.2','2.3A','2.3B','3','4.1','4.2','4.3','5.1','5.2','6.1A','7','8L'];
// rows straight from the 177.848(d) table ('' = no restriction, * = Class 1 compatibility table)
var SEG_ROWS={
'1.1/1.2':['*','*','*','*','*','X','X','X','X','X','X','X','X','X','X','X','X','X'],
'1.3':    ['*','*','*','*','*','X','','X','X','X','','X','X','X','X','X','','X'],
'1.4':    ['*','*','*','*','*','O','','O','O','O','','O','','','','O','','O'],
'1.5':    ['*','*','*','*','*','X','X','X','X','X','X','X','X','X','X','X','X','X'],
'1.6':    ['*','*','*','*','*','','','','','','','','','','','','',''],
'2.1':    ['X','X','O','X','','','','X','O','','','','','','','O','O',''],
'2.2':    ['X','','','X','','','','','','','','','','','','','',''],
'2.3A':   ['X','X','O','X','','X','','','','X','X','X','X','X','X','','','X'],
'2.3B':   ['X','X','O','X','','O','','','','O','O','O','O','O','O','','','O'],
'3':      ['X','X','O','X','','','','X','O','','','','','O','','X','',''],
'4.1':    ['X','','','X','','','','X','O','','','','','','','X','','O'],
'4.2':    ['X','X','O','X','','','','X','O','','','','','','','X','','X'],
'4.3':    ['X','X','','X','','','','X','O','','','','','','','X','','O'],
'5.1':    ['X','X','','X','','','','X','O','O','','','','','','X','','O'],
'5.2':    ['X','X','','X','','','','X','O','','','','','','','X','','O'],
'6.1A':   ['X','X','O','X','','O','','','','X','X','X','X','X','X','','','X'],
'7':      ['X','','','X','','O','','','','','','','','','','','',''],
'8L':     ['X','X','O','X','','','','X','O','','O','X','O','O','O','X','','']
};
var NOTE_A_ROWS={'1.1/1.2':1,'1.5':1,'5.1':1};
// 177.848(f) Class 1 compatibility table
var CG='ABCDEFGHJKLNS'.split('');
var CG_ROWS={
A:['','X','X','X','X','X','X','X','X','X','X','X','X'],
B:['X','','X','X(4)','X','X','X','X','X','X','X','X','4/5'],
C:['X','X','','2','2','X','6','X','X','X','X','3','4/5'],
D:['X','X(4)','2','','2','X','6','X','X','X','X','3','4/5'],
E:['X','X','2','2','','X','6','X','X','X','X','3','4/5'],
F:['X','X','X','X','X','','X','X','X','X','X','X','4/5'],
G:['X','X','6','6','6','X','','X','X','X','X','X','4/5'],
H:['X','X','X','X','X','X','X','','X','X','X','X','4/5'],
J:['X','X','X','X','X','X','X','X','','X','X','X','4/5'],
K:['X','X','X','X','X','X','X','X','X','','X','X','4/5'],
L:['X','X','X','X','X','X','X','X','X','X','1','X','X'],
N:['X','X','3','3','3','X','X','X','X','X','X','','4/5'],
S:['X','4/5','4/5','4/5','4/5','4/5','4/5','4/5','4/5','4/5','X','4/5','']
};
var CG_NOTES={'1':'Group L may only ride with an identical explosive (177.848(g)(3)(i)).','2':'Any mix of groups C, D or E is treated as group E (177.848(g)(3)(ii)).','3':'Mixing C, D or E with N is treated as group D (177.848(g)(3)(iii)).','4':'See 177.835(g) when transporting detonators.','5':'Division 1.4S fireworks may not ride with Division 1.1 or 1.2 materials (177.848(g)(3)(v)).','6':'Group G articles (other than fireworks and those needing special handling) may ride with C, D, E articles if no explosive substances are on the same vehicle (177.848(g)(3)(vi)).'};

function spList(sp){return (sp||'').split(/\s*,\s*/).filter(Boolean);}
function zoneOf(e){var s=spList(e.sp);if(s.indexOf('1')>=0)return'A';if(s.indexOf('2')>=0)return'B';if(s.indexOf('3')>=0)return'C';if(s.indexOf('4')>=0)return'D';if(s.indexOf('6')>=0)return'?';return'';}
function isPIH(e){return zoneOf(e)!=='';}
function liquidGuess(e){var nb=(e.nb||'').trim();if(/^20[123]$/.test(nb))return true;if(/^21[123]$/.test(nb))return false;var n=(e.n||'').toLowerCase();
 if(/\bsolid\b/.test(n))return false;if(/\bliquid|solution\b/.test(n))return true;return null;}
function subsOf(e){var l=(e.l||'').split(/\s*,\s*/).filter(function(x){return x&&x!=='None'&&!/^see/i.test(x);});
 var prim=(e.c||'');return l.filter(function(x){return x!==prim&&x!==prim.slice(0,3);});}

// Build a load item from an HMT entry (or a bare class)
function itemFromEntry(e,opts){opts=opts||{};var liq=liquidGuess(e);
 return {name:e.n||('Class '+e.c),un:e.u||'',cls:e.c,pg:e.pg||'',subs:subsOf(e),zone:zoneOf(e),pih:isPIH(e),
  liquid:opts.liquid!=null?opts.liquid:(liq==null?true:liq),weight:+opts.weight||0,bulk:!!opts.bulk,
  yellow3:!!opts.yellow3,orgBTC:/type b/i.test(e.n||'')&&/temperature controlled/i.test(e.n||'')};}

function segKey(cls,item){cls=String(cls);
 if(/^1\.[12]/.test(cls))return'1.1/1.2';if(/^1\.3/.test(cls))return'1.3';if(/^1\.4/.test(cls))return'1.4';if(/^1\.5/.test(cls))return'1.5';if(/^1\.6/.test(cls))return'1.6';
 if(cls==='2.3'){return item.zone==='A'?'2.3A':item.zone==='B'?'2.3B':null;}
 if(cls==='6.1'){return(item.zone==='A'&&item.pg==='I'&&item.liquid)?'6.1A':null;}
 if(cls==='8')return item.liquid?'8L':null;
 if(['2.1','2.2','3','4.1','4.2','4.3','5.1','5.2','7'].indexOf(cls)>=0)return cls;return null;}
function cgOf(cls){var m=/^1\.\d([A-Z])$/.exec(cls||'');return m?m[1]:null;}
var RANK={'':0,'C':1,'O':2,'X':3};
function isAN(it){return /^UN(1942|2067)$/.test(it.un);} // ammonium nitrate / AN fertilizer (Note A)
function segPair(a,b){
 var res={level:'',notes:[]};function bump(l,n){if(RANK[l]>RANK[res.level])res.level=l;if(n&&res.notes.indexOf(n)<0)res.notes.push(n);}
 var ha=[{c:a.cls,sub:false}].concat(a.subs.map(function(s){return{c:s,sub:true};})),hb=[{c:b.cls,sub:false}].concat(b.subs.map(function(s){return{c:s,sub:true};}));
 var samePrim=String(a.cls).slice(0,3)===String(b.cls).slice(0,3);
 ha.forEach(function(x){hb.forEach(function(y){var ka=segKey(x.c,a),kb=segKey(y.c,b);if(!ka||!kb)return;
  var v1=SEG_ROWS[ka][SEG_KEYS.indexOf(kb)],v2=SEG_ROWS[kb][SEG_KEYS.indexOf(ka)];
  var v=RANK[v1]>=RANK[v2]?v1:v2;if(v1==='*'||v2==='*')v='*';
  if(v==='*'){explosivePair(a,b,x.c,y.c,bump);return;}
  if(!v)return;
  var lbl=x.c+(x.sub?' (subsidiary)':'')+' vs '+y.c+(y.sub?' (subsidiary)':'');
  if(v==='X'&&((NOTE_A_ROWS[ka]&&isAN(b)&&/^1\.[15]/.test(x.c))||(NOTE_A_ROWS[kb]&&isAN(a)&&/^1\.[15]/.test(y.c)))){bump('C','Note A: ammonium nitrate (UN1942) and AN fertilizer may be loaded with Division 1.1 or 1.5 unless 177.835(c) prohibits it.');return;}
  if((x.sub||y.sub)&&samePrim){bump('C',lbl+': '+v+' from a subsidiary hazard, but same-class materials may ride together if they cannot react dangerously (177.848(e)(6)).');return;}
  bump(v,lbl+': '+(v==='X'?'may not be loaded together':'only if separated so leaks cannot mix')+(x.sub||y.sub?' (subsidiary hazard, 177.848(e)(6))':''));
  if(v==='O'&&(ka==='8L'||kb==='8L')&&/^(4|5)/.test(ka==='8L'?kb:ka))bump('O','Class 8 liquids may not be loaded above or next to Class 4 or Class 5 materials (177.848(e)(3)).');
 });});
 // 177.848(c) special rules
 var cy=function(i){return /cyanide/i.test(i.name);},ac=function(i){return /\bacid\b/i.test(i.name)||/acid/i.test(i.name);};
 if((cy(a)&&ac(b)&&!cy(b))||(cy(b)&&ac(a)&&!cy(a)))bump('X','Cyanides may not be loaded with acids if mixing would make hydrogen cyanide (177.848(c)).');
 return res;}
function explosivePair(a,b,ca,cb,bump){
 var ga=cgOf(ca),gb=cgOf(cb);if(!ga||!gb){bump('C','Class 1 vs Class 1: check the compatibility table, 177.848(f).');return;}
 var v=CG_ROWS[ga][CG.indexOf(gb)];
 if(v==='')return;
 if(v==='X'){bump('X','Explosives '+ca+' and '+cb+': compatibility groups '+ga+' and '+gb+' may not ride together (177.848(f)).');return;}
 if(v==='X(4)'){bump('X','Explosives groups B and D may not ride together, except detonators under 177.835(g).');return;}
 if(v==='1'){if(a.un&&a.un===b.un)return;bump('X',CG_NOTES['1']);return;}
 if(v==='4/5'){var s=ga==='S'?a:b,o=ga==='S'?cb:ca;if(/firework/i.test(s.name)&&/^1\.[12]/.test(o)){bump('X',CG_NOTES['5']);return;}bump('C',CG_NOTES['4']+' '+CG_NOTES['5']);return;}
 bump('C',CG_NOTES[v]);}

// ---- Placarding 172.504 / 172.505 ----
function placardFor(cls,it){cls=String(cls);
 if(/^1\.[1-6]/.test(cls)){var d=cls.slice(0,3);return{p:'EXPLOSIVES '+d,t:(['1.1','1.2','1.3'].indexOf(d)>=0)?1:2};}
 if(cls==='2.1')return{p:'FLAMMABLE GAS',t:2};
 if(cls==='2.2')return{p:'NON-FLAMMABLE GAS',t:2,ox:/^UN(1072|1073)$/.test(it.un)};
 if(cls==='2.3')return{p:'POISON GAS',t:1};
 if(cls==='3')return{p:'FLAMMABLE',t:2};
 if(/^comb/i.test(cls))return{p:'COMBUSTIBLE',t:2};
 if(cls==='4.1')return{p:'FLAMMABLE SOLID',t:2};
 if(cls==='4.2')return{p:'SPONTANEOUSLY COMBUSTIBLE',t:2};
 if(cls==='4.3')return{p:'DANGEROUS WHEN WET',t:1};
 if(cls==='5.1')return{p:'OXIDIZER',t:2};
 if(cls==='5.2')return{p:'ORGANIC PEROXIDE',t:it.orgBTC?1:2};
 if(cls==='6.1')return it.pih?{p:'POISON INHALATION HAZARD',t:1}:{p:'POISON',t:2};
 if(cls==='6.2')return{p:null,t:2,note:'Division 6.2: no placard (172.504 Table 2).'};
 if(cls==='7')return it.yellow3?{p:'RADIOACTIVE',t:1}:{p:null,t:0,note:'Class 7: RADIOACTIVE placard only for Yellow-III labeled packages (and the cases in footnote 1 of Table 1).'};
 if(cls==='8')return{p:'CORROSIVE',t:2};
 if(cls==='9')return{p:'CLASS 9',t:2,c9:1};
 return{p:null,t:0};}
var DIVORDER=['EXPLOSIVES 1.1','EXPLOSIVES 1.2','EXPLOSIVES 1.3','EXPLOSIVES 1.4','EXPLOSIVES 1.5','EXPLOSIVES 1.6'];
function placards(items,opt){opt=opt||{};var domestic=opt.domestic!==false;
 var req={},why={},notes=[],t2w={},t2total=0,anyBulkT2=false;
 function add(p,w){if(!p)return;req[p]=1;(why[p]=why[p]||[]).push(w);}
 items.forEach(function(it){var pl=placardFor(it.cls,it);if(pl.note&&notes.indexOf(pl.note)<0)notes.push(pl.note);
  if(!pl.p)return;
  if(pl.t===1)add(pl.p,it.name+': Table 1, any amount');
  else if(it.bulk)add(pl.p,it.name+': bulk packaging, any amount');
  else{t2w[pl.p]=(t2w[pl.p]||0)+(+it.weight||0);t2total+=(+it.weight||0);}
  if(pl.ox)notes.push('Oxygen: an OXYGEN placard may be used instead of NON-FLAMMABLE GAS (172.504(f)(7)).');
  // 172.505 subsidiary placards
  if(it.pih&&it.cls!=='2.3'&&it.cls!=='6.1')add('POISON INHALATION HAZARD',it.name+': inhalation hazard, 172.505(a)');
  if(it.subs.indexOf('4.3')>=0)add('DANGEROUS WHEN WET',it.name+': subsidiary dangerous-when-wet, 172.505(c)');
  if(/^UN(2977|2978)$/.test(it.un)&&(+it.weight||0)>=1001){add('CORROSIVE',it.name+': uranium hexafluoride 1,001 lb or more, 172.505(b)');add('POISON',it.name+': uranium hexafluoride 1,001 lb or more, 172.505(b)');}
 });
 var t2cats=Object.keys(t2w),t2needed=t2total>=1001,dangerousOK=false,mustOwn=[];
 if(t2cats.length){
  if(!t2needed)notes.push('Table 2 materials total '+t2total+' lb (under 1,001 lb), so no Table 2 placards are required (172.504(c)). You may still display them.');
  else{t2cats.forEach(function(p){add(p,'Table 2 materials total '+t2total+' lb (1,001 lb or more)');});

   if(t2cats.length>=2){dangerousOK=true;mustOwn=t2cats.filter(function(p){return t2w[p]>=2205;});}
  }}
 // 172.504(f) exceptions
 var exp=Object.keys(req).filter(function(p){return/^EXPLOSIVES/.test(p);}).sort(function(a,b){return DIVORDER.indexOf(a)-DIVORDER.indexOf(b);});
 if(exp.length>1){exp.slice(1).forEach(function(p){delete req[p];});notes.push('More than one explosives division: only the lowest division placard ('+exp[0]+') is needed (172.504(f)(1)).');}
 if(req['NON-FLAMMABLE GAS']&&req['FLAMMABLE GAS']){delete req['NON-FLAMMABLE GAS'];notes.push('NON-FLAMMABLE GAS placard not needed because FLAMMABLE GAS is displayed (172.504(f)(3)).');}
 if(req['OXIDIZER']&&(req['EXPLOSIVES 1.1']||req['EXPLOSIVES 1.2'])){delete req['OXIDIZER'];notes.push('OXIDIZER placard not needed with EXPLOSIVES 1.1/1.2 placards (172.504(f)(4)).');}
 if(req['OXIDIZER']&&req['EXPLOSIVES 1.5']){delete req['OXIDIZER'];notes.push('OXIDIZER placard not needed with EXPLOSIVES 1.5 placards on a vehicle (172.504(f)(5)).');}
 if(domestic&&req['POISON INHALATION HAZARD']&&req['POISON GAS']){delete req['POISON INHALATION HAZARD'];notes.push('Domestic: POISON INHALATION HAZARD not needed when POISON GAS is displayed (172.504(f)(8)).');}
 if(domestic&&req['POISON']&&(req['POISON INHALATION HAZARD']||req['POISON GAS'])){delete req['POISON'];notes.push('Domestic: POISON placard not needed when POISON INHALATION HAZARD or POISON GAS is displayed (172.504(f)(11)).');}
 if(domestic&&req['CLASS 9']){var bulk9=items.some(function(i){return i.cls==='9'&&i.bulk;});delete req['CLASS 9'];notes.push('Domestic: CLASS 9 placard not required'+(bulk9?', but bulk packaging must show the ID number on a CLASS 9 placard, orange panel or white square-on-point (172.504(f)(9)).':' (172.504(f)(9)).'));}
 if(req['COMBUSTIBLE'])notes.push('A FLAMMABLE placard may replace COMBUSTIBLE on a cargo tank or portable tank (172.504(f)(2)). Combustible liquids in non-bulk packaging are generally not regulated (173.150(f)).');
 if(items.some(function(i){return /^1\.4S/.test(i.cls);}))notes.push('EXPLOSIVES 1.4 placard is not needed for 1.4S materials that are not required to be labeled 1.4S (172.504(f)(6)).');
 var t2still=Object.keys(t2w).filter(function(p){return req[p];});
 var dangerous=null;
 if(dangerousOK&&t2still.length>=2){var own=mustOwn.filter(function(p){return req[p];});var replaceable=t2still.filter(function(p){return own.indexOf(p)<0&&!why[p].some(function(w){return /bulk|172\.505|Table 1/.test(w);});});
  if(replaceable.length>=1)dangerous={replaces:replaceable,mustKeep:own,text:'Option: a DANGEROUS placard may be used instead of '+replaceable.join(', ')+' (172.504(b)).'+(own.length?' '+own.join(', ')+' must still be shown because 2,205 lb or more of that category was loaded at one facility.':'')};}
 return{placards:Object.keys(req),why:why,notes:notes,t2total:t2total,t2byPlacard:t2w,dangerous:dangerous};}

function checkLoad(items){var pairs=[];for(var i=0;i<items.length;i++)for(var j=i+1;j<items.length;j++){var r=segPair(items[i],items[j]);pairs.push({a:i,b:j,level:r.level,notes:r.notes});}return pairs;}
G.HZ={SEG_KEYS:SEG_KEYS,SEG_ROWS:SEG_ROWS,CG:CG,CG_ROWS:CG_ROWS,itemFromEntry:itemFromEntry,segPair:segPair,checkLoad:checkLoad,placards:placards,placardFor:placardFor,zoneOf:zoneOf,isPIH:isPIH,liquidGuess:liquidGuess,subsOf:subsOf,segKey:segKey};
})(typeof window!=='undefined'?window:global);
