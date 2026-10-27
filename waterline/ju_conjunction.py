"""Jupiter–Uranus conjunction, 21 Apr 2024 — Scalar Flower field analysis + the cycle, with the real ephemeris.
Every number here is [REAL] unless tagged. Geocentric, tropical longitudes; invariants are frame-indifferent (checked)."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.expanduser("~/whit/scalar-flower-api/engine")); os.environ.setdefault("SWE_EPHE", os.path.expanduser("~/.hermes/ephe"))
import swisseph as swe
from scalar_field_core import compute_chart, Field, BODIES, fmt_lon
swe.set_ephe_path(os.environ["SWE_EPHE"])

def lon(body, jd): return swe.calc_ut(jd, body)[0][0]
def sep(jd): return (lon(swe.JUPITER, jd) - lon(swe.URANUS, jd) + 180) % 360 - 180

# ---- 1. find the exact 2024 conjunction (sep crosses 0), two-witness the shelf's 21 Apr 02:26 UT
jd0 = swe.julday(2024, 4, 15, 0); jd1 = swe.julday(2024, 4, 27, 0)
lo, hi = jd0, jd1
for _ in range(60):
    mid = (lo + hi) / 2
    if sep(lo) * sep(mid) <= 0: hi = mid
    else: lo = mid
jdc = (lo + hi) / 2; y, m, d, h = swe.revjul(jdc)
print(f"[REAL] exact conjunction: {int(y)}-{int(m):02d}-{int(d):02d} {int(h):02d}:{int((h%1)*60):02d} UT  at {fmt_lon(lon(swe.JUPITER,jdc))}  (shelf: 21 Apr 2024 02:26 UT, 21°49′ Tau)")

# ---- 2. the field at that instant (node-anchored invariants; location irrelevant for the invariants)
ch = compute_chart(int(y), int(m), int(d), h, 0.0, 51.5, -0.1)  # London placeholder: invariants don't depend on it
f = Field(ch, mode="keplerian"); fu = Field(ch, mode="uniform")
theta = np.array([f.theta[b] for b in BODIES]); N = len(theta)
mags = [float(abs(np.exp(1j*p*theta).mean())) for p in range(1, 7)]
magu = [float(abs(np.exp(1j*p*np.array([fu.theta[b] for b in BODIES])).mean())) for p in range(1, 7)]
# re-anchor check: rotate every theta by +23.85°
rot = theta + np.deg2rad(23.85); magr = [float(abs(np.exp(1j*p*rot).mean())) for p in range(1, 7)]
inv = all(abs(a-b) < 1e-9 for a, b in zip(mags, magu)) and all(abs(a-b) < 1e-9 for a, b in zip(mags, magr))
th = sorted(np.rad2deg(theta) % 360); gaps = sorted([((th[(i+1) % N] - th[i]) % 360) for i in range(N)], reverse=True)
m1, m2, m3 = mags[:3]
modality = "unipolar" if m1 >= .5 else "bipolar" if (m2 >= m1 and m2 >= m3 and m2 > .25) else "trilobed" if (m3 >= m1 and m3 >= m2 and m3 > .2) else "diffuse"
print(f"[REAL] bodies: " + ", ".join(f"{b} {fmt_lon(ch['bodies'][b])}" for b in BODIES))
print(f"[REAL] node {fmt_lon(ch['north_node'])} | hub {N*m1:.3f} | |m1..m6| {[round(x,3) for x in mags]} | modality {modality} | dominant m{int(np.argmax(mags))+1}")
print(f"[REAL] silences (phasor gaps) top3: {[round(g,1) for g in gaps[:3]]}° | invariance (uniform mode + re-anchor): {inv}")
print(f"[REAL] Saturn toll on hub: {f.ablation_hub(['Saturn']) - f.hub():+.3f} | Jupiter+Uranus removed: {f.ablation_hub(['Jupiter','Uranus']) - f.hub():+.3f}")

# ---- 3. population percentile for hub/m1,m2,m3 against the 20k null (seed 42) — generate on the spot
rng = np.random.RandomState(42); jds = rng.uniform(swe.julday(1900,1,1), swe.julday(2100,1,1), 20000)
pop = np.zeros((20000, 6))
for i, j in enumerate(jds):
    node = swe.calc_ut(j, swe.MEAN_NODE)[0][0]
    t = np.deg2rad(np.array([swe.calc_ut(j, getattr(swe, b.upper()))[0][0] for b in BODIES]) - node)
    pop[i] = [abs(np.exp(1j*p*t).mean()) for p in range(1, 7)]
pct = [(pop[:, p] < mags[p]).mean()*100 for p in range(6)]
print(f"[REAL] percentiles vs 20k null (1900–2100): m1 {pct[0]:.0f}th · m2 {pct[1]:.0f}th · m3 {pct[2]:.0f}th · m4 {pct[3]:.0f}th · m5 {pct[4]:.0f}th · m6 {pct[5]:.0f}th")

# ---- 4. the cycle: every Jupiter–Uranus conjunction 1900–2100 with sign; the ~13.8-yr period; the 1941 return in Taurus
conj = []
jd = swe.julday(1900, 1, 1); step = 10
prev = sep(jd)
while jd < swe.julday(2100, 1, 1):
    jd2 = jd + step; cur = sep(jd2)
    if prev * cur < 0 and abs(prev) < 90:
        a, b = jd, jd2
        for _ in range(50):
            mm = (a+b)/2
            if sep(a)*sep(mm) <= 0: b = mm
            else: a = mm
        jc = (a+b)/2; yy, mo, dd, hh = swe.revjul(jc); conj.append((jc, int(yy), int(mo), int(dd), lon(swe.JUPITER, jc)))
    prev = cur; jd = jd2
# collapse retrograde triples (same pass) into clusters within 400 days
clusters = []
for c in conj:
    if clusters and c[0] - clusters[-1][-1][0] < 400: clusters[-1].append(c)
    else: clusters.append([c])
print("\n[REAL] Jupiter–Uranus conjunction passes 1900–2100 (clustered; sign = tropical):")
for cl in clusters:
    print("   " + " | ".join(f"{c[1]}-{c[2]:02d}-{c[3]:02d} {fmt_lon(c[4])}" for c in cl))
mids = [np.mean([c[0] for c in cl]) for cl in clusters]
per = np.diff(mids)/365.25; print(f"[REAL] mean synodic period {per.mean():.2f} yr (range {per.min():.2f}–{per.max():.2f})")
taurus = [cl for cl in clusters if any(30 <= c[4] % 360 < 60 for c in cl)]
print(f"[REAL] passes in Taurus: {[cl[0][1] for cl in taurus]}  → sign-return interval {[taurus[i+1][0][1]-taurus[i][0][1] for i in range(len(taurus)-1)]} yr")
json.dump(dict(conj=[(int(y),int(m),int(d),round(h,3)) for (_,y,m,d,_),h in [((0,y,m,d,0),h)]], mags=mags, pct=pct, modality=modality, gaps=gaps, clusters=[[(c[1],c[2],c[3],round(c[4],2)) for c in cl] for cl in clusters], period=float(per.mean())), open(os.path.expanduser("~/architect/waterline/ju_2024.json"), "w"), indent=1)
