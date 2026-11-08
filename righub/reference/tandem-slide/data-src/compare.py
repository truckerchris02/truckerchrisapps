# Compare JS engine text output with the original Python on many cases.
import io,contextlib,json,random,subprocess,sys
sys.path.insert(0,'/workspace/tandemslide/data-src')
from high_mile_original import calculate_tandem_shift as f
random.seed(7)
cases=[(11800,35200,31600,4),(11800,35200,31600,6),(12000,34000,34000,4),(12500,30000,36000,6),(11000,33000,33000,4),(12000,35000,34000,4),(10000,30000,30001,4),(11500,33200,33100,6),(12400,34200,34300,4),(0,0,0,4)]
for _ in range(3000):cases.append((random.randint(8000,14000),random.randint(20000,40000),random.randint(15000,40000),random.choice([4,6])))
py=[]
for c in cases:
    b=io.StringIO()
    with contextlib.redirect_stdout(b): f(*c[:3],hole_spacing_inches=c[3])
    py.append(b.getvalue())
js=subprocess.run(['node','-e','''const T=require("/workspace/tandemslide/assets/engine.js");const cs=JSON.parse(require("fs").readFileSync(0,"utf8"));
console.log(JSON.stringify(cs.map(c=>T.calc(c[0],c[1],c[2],c[3]).lines.join("\\n")+"\\n")))'''],input=json.dumps(cases),capture_output=True,text=True,check=True)
js=json.loads(js.stdout)
bad=[i for i in range(len(cases)) if py[i]!=js[i]]
print(len(cases),'cases, mismatches:',len(bad))
for i in bad[:3]:print(cases[i]);print(repr(py[i]));print(repr(js[i]))
