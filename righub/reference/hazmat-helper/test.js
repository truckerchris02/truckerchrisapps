require('./engine.js');const HZ=global.HZ;const D=require('/workspace/hazdata/hazdata.json').hmt;
const P=require('/workspace/hazdata/seg_parsed.json');let fail=0;const ok=(c,m)=>{if(!c){fail++;console.log('FAIL',m)}else console.log('ok  ',m)};
// 1. engine tables == eCFR parsed tables
P.seg.forEach((r,i)=>{const k=HZ.SEG_KEYS[i];ok(JSON.stringify(HZ.SEG_ROWS[k])===JSON.stringify(r.slice(3)),'seg row '+k+' matches eCFR');});
P.cg.forEach(r=>ok(JSON.stringify(HZ.CG_ROWS[r[0]])===JSON.stringify(r.slice(1)),'compat row '+r[0]+' matches eCFR'));
const f=(un,pg)=>D.find(e=>e.u===un&&(!pg||e.pg===pg));
const it=(un,w,o)=>HZ.itemFromEntry(f(un,o&&o.pg),Object.assign({weight:w},o||{}));
// lookups
ok(f('UN1203').c==='3'&&f('UN1203').pg==='II'&&f('UN1203').g[0]==='128','Gasoline UN1203 class 3 PG II guide 128');
ok(f('UN1005').c==='2.3'&&D.filter(e=>e.u==='UN1005')[1].c==='2.2'&&D.filter(e=>e.u==='UN1005')[1].s==='D'&&f('UN1005').t===1&&f('UN1005').g[0]==='125','Anhydrous ammonia: 2.3 intl (I), 2.2 domestic (D), ERG 125, green-table');
ok(f('UN1017').c==='2.3'&&HZ.zoneOf(f('UN1017'))==='B','Chlorine 2.3 Zone B');
ok(f('UN1090').g[0]==='127','Acetone guide 127');
// segregation
const lv=(a,b)=>HZ.segPair(a,b).level;
ok(lv(it('UN1203',500),it('UN1830',500,{pg:'II'}))==='','Gasoline + sulfuric acid (8 liquid): no restriction');
ok(lv(it('UN1017',500),it('UN1203',500))==='O','Chlorine (2.3 Zone B) + gasoline: O');
ok(lv(it('UN1203',500),it('UN1942',500))==='O','Gasoline + ammonium nitrate (5.1): O');
ok(lv(it('UN1428',100),it('UN1830',100))==='O','Sodium (4.3) + sulfuric acid: O');
const hcn=D.find(e=>e.u==='UN1051');ok(lv(HZ.itemFromEntry(hcn,{}),it('UN1203',10))==='X','Hydrogen cyanide (6.1 PG I zone A liquid) + gasoline: X  [zone '+HZ.zoneOf(hcn)+']');
ok(lv(it('UN1689',10),it('UN1789',10))==='X','Sodium cyanide + hydrochloric acid: X per 177.848(c)');
ok(lv(it('UN0081',10),it('UN1203',10))==='X','Explosive 1.1D + gasoline: X');
ok(lv(it('UN0081',10),it('UN1942',10))==='C','1.1D + ammonium nitrate: Note A allowed');
ok(lv(it('UN0081',10),it('UN0029',10))==='X','1.1D + 1.1B detonators: X (B-D)');
ok(lv(it('UN1072',10),it('UN1203',10))==='O','Oxygen 2.2 with 5.1 subsidiary vs gasoline (O via 177.848(e)(6)): '+lv(it('UN1072',10),it('UN1203',10)));
// placards
const pl=(items)=>HZ.placards(items).placards.sort().join('|');
ok(pl([it('UN1203',800)])==='','800 lb gasoline non-bulk: no placard');
ok(pl([it('UN1203',1001)])==='FLAMMABLE','1,001 lb gasoline: FLAMMABLE');
ok(pl([it('UN1203',600),it('UN1830',600,{pg:'II'})])==='CORROSIVE|FLAMMABLE','600+600 lb flam+corr: both (aggregate >=1001)');
ok(!!HZ.placards([it('UN1203',600),it('UN1830',600,{pg:'II'})]).dangerous,'DANGEROUS option offered');
ok(HZ.placards([it('UN1203',3000),it('UN1830',600,{pg:'II'})]).dangerous.mustKeep.join()==='FLAMMABLE','2,205+ lb category must keep own placard');
ok(pl([it('UN1017',50)])==='POISON GAS','50 lb chlorine: POISON GAS (Table 1)');
ok(pl([it('UN1428',50)])==='DANGEROUS WHEN WET','50 lb sodium 4.3: DWW');
ok(pl([it('UN1203',200,{bulk:true})])==='FLAMMABLE','bulk gasoline any qty: FLAMMABLE');
ok(pl([it('UN1072',1500),it('UN1954',100)])==='FLAMMABLE GAS','oxygen+flammable gas: NFG dropped (f)(3)');
const pih6=D.find(e=>e.c==='6.1'&&HZ.zoneOf(e)==='B');ok(pl([HZ.itemFromEntry(pih6,{weight:10})])==='POISON INHALATION HAZARD','6.1 PIH small qty: PIH placard ('+pih6.n+')');
ok(pl([it('UN3077',5000)])==='','Class 9 domestic: none');
console.log(fail?fail+' FAILED':'ALL PASSED');
