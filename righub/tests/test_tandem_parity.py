#!/usr/bin/env python3
"""The Rig Hub calculator must match the standalone Tandem Slide engine and Chris's original Python."""
import contextlib, io, json, math, pathlib, random, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "tandem-slide"
sys.path.insert(0, str(REF / "data-src"))
from high_mile_original import calculate_tandem_shift  # noqa: E402

ENGINES = [
    ROOT / "android" / "assets" / "tandem" / "engine.js",
    ROOT / "flatpak" / "app" / "tandem" / "engine.js",
    REF / "assets" / "engine.js",
]
PAGES = [
    ROOT / "android" / "assets" / "tandem" / "index.html",
    ROOT / "flatpak" / "app" / "tandem" / "index.html",
    REF / "assets" / "index.html",
]


def fail(msg):
    raise SystemExit(msg)


def python_text(steer, drives, tandems, spacing):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        calculate_tandem_shift(steer, drives, tandems, hole_spacing_inches=spacing)
    return buf.getvalue()


def main():
    engine_bytes = [p.read_bytes() for p in ENGINES]
    if len(set(engine_bytes)) != 1:
        fail("Rig Hub engine.js is not the standalone engine")
    page_bytes = [p.read_bytes() for p in PAGES]
    if len(set(page_bytes)) != 1:
        fail("Rig Hub calculator page is not the standalone page")
    page = page_bytes[0].decode("utf-8")
    engine = engine_bytes[0].decode("utf-8")
    for text in [
        "always re-scale",
        "limit 12,000",
        "limit 34,000",
        "Gross limit 80,000",
        "Invalid input",
    ]:
        if text not in page:
            fail("calculator page lost safety or input text: " + text)
    for text in [
        "Return to shipper for rework",
        "You cannot balance this out with a tandem slide",
        "check tire ratings",
        "Always re-scale after pinning",
        "toward the cab",
        "toward the rear doors",
    ]:
        if text not in engine:
            fail("calculator engine lost safety text: " + text)

    random.seed(7)
    cases = [
        (11800, 35200, 31600, 4),
        (11800, 35200, 31600, 6),
        (12000, 34000, 34000, 4),
        (12500, 30000, 36000, 6),
        (11000, 33000, 33000, 4),
        (12000, 35000, 34000, 4),
        (10000, 30000, 30001, 4),
        (11500, 33200, 33100, 6),
        (12400, 34200, 34300, 4),
        (0, 0, 0, 4),
        (12000, 34000, 34000, 6),
        (8000, 36000, 36000, 4),
        (12001, 33999, 34000, 4),
    ]
    for _ in range(3000):
        cases.append((
            random.randint(8000, 14000),
            random.randint(20000, 40000),
            random.randint(15000, 40000),
            random.choice([4, 6]),
        ))
    node = r"""
const T = require(process.argv[1]);
const cs = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = cs.map(function (c) {
  const r = T.calc(c[0], c[1], c[2], c[3]);
  return {
    lines: r.lines.join("\n") + "\n",
    gross: r.gross,
    returnToShipper: !!r.returnToShipper,
    dir: r.plan ? r.plan.dir : null,
    holes: r.plan ? r.plan.holes : null,
    lbs: r.plan ? r.plan.lbsPerHole : null,
    transfer: r.plan ? r.plan.transfer : null,
    alerts: (r.alerts || []).map(function (a) { return a.kind + ":" + a.text; })
  };
});
const weights = ["12,000", " 11800 ", "+34000", "12.5", "12a", "", "1 2", "-5"];
const parsed = weights.map(function (w) { return T.parseWeight(w); });
process.stdout.write(JSON.stringify({out: out, parsed: parsed}));
"""
    proc = subprocess.run(
        ["node", "-e", node, str(ENGINES[0])],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
    )
    got = json.loads(proc.stdout)
    parsed = got["parsed"]
    expect_parsed = [12000, 11800, 34000, None, None, None, None, -5]
    if parsed != expect_parsed:
        fail("parseWeight mismatch %s" % parsed)
    mismatches = 0
    for i, c in enumerate(cases):
        py = python_text(*c)
        js = got["out"][i]
        if py != js["lines"]:
            mismatches += 1
            if mismatches <= 3:
                print("CASE", c)
                print("PY", repr(py))
                print("JS", repr(js["lines"]))
        steer, drives, tandems, spacing = c
        gross = steer + drives + tandems
        if js["gross"] != gross:
            fail("gross mismatch %s" % (c,))
        if gross > 80000:
            if not js["returnToShipper"] or js["dir"] is not None:
                fail("over-gross case still offered a slide %s" % (c,))
            if not any("Return to shipper" in a for a in js["alerts"]):
                fail("missing return-to-shipper guidance %s" % (c,))
            continue
        direction = "FORWARD" if drives > tandems else "BACK" if drives < tandems else "NONE"
        if js["dir"] != direction:
            fail("direction %s for %s" % (js["dir"], c))
        transfer = abs(drives - tandems) // 2
        lph = 450 if spacing == 6 else 300
        holes = math.ceil(transfer / lph) if lph else 0
        if js["transfer"] != transfer or js["lbs"] != lph or js["holes"] != holes:
            fail("holes mismatch %s got %s" % (c, js))
        if steer > 12000 and not any("check tire ratings" in a for a in js["alerts"]):
            fail("missing steer tire warning %s" % (c,))
        if drives > 34000 and not any("Drives are OVER" in a for a in js["alerts"]):
            fail("missing drive overweight warning %s" % (c,))
        if tandems > 34000 and not any("Tandems are OVER" in a for a in js["alerts"]):
            fail("missing tandem overweight warning %s" % (c,))
    if mismatches:
        fail("%s text mismatches against the original Python" % mismatches)
    # Documented sample: drives heavy, 4 inch pins, six holes forward.
    sample = got["out"][0]
    if sample["dir"] != "FORWARD" or sample["holes"] != 6 or sample["lbs"] != 300:
        fail("sample 11800/35200/31600 @ 4in is %s" % sample)
    sample6 = got["out"][1]
    if sample6["dir"] != "FORWARD" or sample6["holes"] != 4 or sample6["lbs"] != 450:
        fail("sample @ 6in is %s" % sample6)
    print("ok", len(cases), "cases match the standalone calculator")


if __name__ == "__main__":
    main()
