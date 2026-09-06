"""
Build docs/index.html, the page that gets published on GitHub Pages.

The figures are inlined into the HTML rather than fetched from the JSON at
runtime. Two reasons: the page then works when opened straight off the disk
with a double click, and there is no moment where a visitor sees an empty
shell while a request is in flight.

Run 06_maps.py first; this reads docs/dashboard_data.json.
"""

import json

from settings import DOCS

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reaching a hospital by bus in Bengaluru</title>
<meta name="description" content="How long it takes to reach a hospital by BMTC bus from each of Bengaluru's 198 wards.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,600;0,700;0,800&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,400&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#070C22;
  --navy:#0E1740;
  --oxblood:#3E0F1E;
  --ember:#C0392B;
  --emberlight:#E8654F;
  --paper:#EEF1FA;
  --muted:#9AA4C6;
  --line:rgba(238,241,250,.14);
  --band1:#2E8B7A;
  --band2:#E8C468;
  --band3:#E08A4A;
  --band4:#C0392B;
  --band5:#4A4A55;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;
  background:
    radial-gradient(1100px 700px at 82% -6%, rgba(192,57,43,.42), transparent 62%),
    radial-gradient(900px 620px at 8% 8%, rgba(62,15,30,.55), transparent 60%),
    linear-gradient(168deg, var(--ink) 0%, var(--navy) 44%, #16113A 74%, var(--oxblood) 100%);
  background-attachment:fixed;
  color:var(--paper);
  font-family:"Newsreader",Georgia,serif;
  font-size:17px;
  line-height:1.62;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1120px;margin:0 auto;padding:0 26px}
h1,h2,h3,.blk,.stat b,.tbl th,.chip{font-family:"Archivo",system-ui,sans-serif}
.blk{text-transform:uppercase;letter-spacing:.14em;font-weight:700}

/* ---------- masthead ---------- */
header{padding:46px 0 0}
.rule{height:3px;background:linear-gradient(90deg,var(--ember),var(--emberlight) 28%,transparent 78%)}
.masthead{display:flex;justify-content:space-between;align-items:baseline;gap:20px;flex-wrap:wrap;
  padding:16px 0 0;font-size:12px;color:var(--muted)}
.masthead .blk{font-size:12px;color:var(--paper)}

.hero{padding:34px 0 56px;position:relative;overflow:hidden}
h1{
  font-size:clamp(2.5rem,7.4vw,5.6rem);
  line-height:.92;margin:8px 0 0;font-weight:800;
  text-transform:uppercase;letter-spacing:-.015em;
  text-shadow:0 2px 0 rgba(0,0,0,.35), 0 22px 48px rgba(0,0,0,.45);
}
h1 span{display:block}
h1 .thin{font-weight:400;color:var(--muted);letter-spacing:.02em;font-size:.42em;
  text-transform:none;font-family:"Newsreader",serif;margin-top:18px;max-width:34ch;line-height:1.45}
.routeline{position:absolute;right:-40px;top:40px;width:52%;max-width:560px;opacity:.5;pointer-events:none}
.routeline path{fill:none;stroke:var(--emberlight);stroke-width:2.2;stroke-linecap:round}
.routeline .dashed{stroke-dasharray:1400;stroke-dashoffset:1400;animation:draw 3.4s ease-out .4s forwards}
.routeline circle{fill:var(--paper);opacity:0;animation:pop .5s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes pop{to{opacity:.9}}

/* ---------- big number ---------- */
.headline{
  margin:38px 0 0;padding:30px 32px;border-radius:2px;
  background:linear-gradient(120deg, rgba(192,57,43,.24), rgba(14,23,64,.5));
  border-left:6px solid var(--ember);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.07), 0 26px 60px rgba(0,0,0,.4);
  display:flex;gap:34px;align-items:center;flex-wrap:wrap;
}
.bignum{font-family:"Archivo";font-weight:800;font-size:clamp(3rem,9vw,5.4rem);
  line-height:.88;font-variant-numeric:tabular-nums;
  background:linear-gradient(180deg,#fff,#F3B9AE);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 3px 0 rgba(0,0,0,.3));}
.headline p{margin:0;max-width:36ch;font-size:1.05rem}

/* ---------- stats ---------- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:2px;
  margin:2px 0 0;background:var(--line)}
.stat{background:rgba(7,12,34,.55);padding:22px 20px}
.stat b{display:block;font-size:2rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1}
.stat span{display:block;font-size:.9rem;color:var(--muted);margin-top:4px}

section{padding:64px 0 0}
h2{font-size:clamp(1.5rem,3.2vw,2.2rem);text-transform:uppercase;letter-spacing:.02em;
  font-weight:800;margin:0 0 6px;line-height:1.06}
h2::after{content:"";display:block;width:64px;height:3px;background:var(--ember);margin-top:14px}
.lede{color:var(--muted);max-width:66ch;margin:18px 0 26px;font-size:1.06rem}
p{max-width:70ch}

/* ---------- band ladder ---------- */
.ladder{display:grid;gap:10px;margin-top:8px}
.rung{display:grid;grid-template-columns:158px 1fr;gap:16px;align-items:center}
.rung .name{font-family:"Archivo";font-size:.82rem;text-transform:uppercase;letter-spacing:.1em;
  color:var(--paper);text-align:right}
.bar{height:44px;background:rgba(255,255,255,.05);position:relative;overflow:hidden}
.bar i{position:absolute;inset:0 auto 0 0;width:0;transition:width 1.3s cubic-bezier(.2,.7,.2,1)}
.bar em{position:absolute;left:14px;top:50%;transform:translateY(-50%);font-style:normal;
  font-family:"Archivo";font-size:.86rem;font-weight:600;
  font-variant-numeric:tabular-nums;white-space:nowrap}

/* ---------- tables ---------- */
.tbl{width:100%;border-collapse:collapse;margin-top:10px;font-size:.98rem}
.tbl th{font-size:.74rem;text-transform:uppercase;letter-spacing:.11em;font-weight:700;
  text-align:right;color:var(--muted);padding:0 12px 10px;border-bottom:1px solid var(--line)}
.tbl th:first-child,.tbl td:first-child{text-align:left}
.tbl td{padding:11px 12px;border-bottom:1px solid rgba(238,241,250,.07);
  font-variant-numeric:tabular-nums;text-align:right}
.tbl tbody tr:hover{background:rgba(192,57,43,.14)}
.tbl td.ward{font-family:"Archivo";font-weight:600;letter-spacing:.01em}
.dot{display:inline-block;width:9px;height:9px;margin-right:9px;vertical-align:1px;border-radius:50%}
.two{display:grid;grid-template-columns:1fr 1fr;gap:44px}

/* ---------- map ---------- */
.mapframe{margin-top:12px;border:1px solid var(--line);height:560px;background:#0b1130}
.mapframe iframe{width:100%;height:100%;border:0;display:block}
.chip{display:inline-block;font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;
  font-weight:700;padding:7px 13px;border:1px solid var(--line);color:var(--paper);
  text-decoration:none;margin:14px 8px 0 0;background:rgba(255,255,255,.04)}
.chip:hover{background:var(--ember);border-color:var(--ember)}

/* ---------- scatter ---------- */
.scatter{width:100%;height:420px;margin-top:14px;display:block}
.scatter text{font-family:"Archivo";font-size:11px;fill:var(--muted)}
.scatter .grid{stroke:rgba(238,241,250,.1);stroke-width:1}
.scatter circle{opacity:.82}
.scatter circle:hover{stroke:#fff;stroke-width:2}

/* ---------- notes ---------- */
.limits{border-top:1px solid var(--line);margin-top:16px}
.limits div{padding:20px 0;border-bottom:1px solid rgba(238,241,250,.07);
  display:grid;grid-template-columns:210px 1fr;gap:24px}
.limits h3{margin:0;font-size:.82rem;text-transform:uppercase;letter-spacing:.11em;
  font-weight:700;color:var(--emberlight)}
.limits p{margin:0;color:var(--muted)}

footer{margin-top:78px;padding:34px 0 60px;border-top:1px solid var(--line);
  color:var(--muted);font-size:.92rem}
footer a{color:var(--paper)}

@media (max-width:820px){
  .two{grid-template-columns:1fr;gap:34px}
  .rung{grid-template-columns:96px 1fr}
  .rung .name{font-size:.7rem}
  .limits div{grid-template-columns:1fr;gap:6px}
  .routeline{display:none}
  .headline{padding:22px}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  .routeline .dashed{stroke-dashoffset:0}
  .routeline circle{opacity:.9}
}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="rule"></div>
  <div class="masthead">
    <span class="blk">Bengaluru bus access &middot; ward analysis</span>
    <span>BMTC timetable 12 July 2026 &nbsp;|&nbsp; BBMP wards, Census 2011 &nbsp;|&nbsp; Karnataka health GIS</span>
  </div>

  <div class="hero">
    <svg class="routeline" viewBox="0 0 560 300" aria-hidden="true">
      <path class="dashed" d="M10 250 C 90 250, 120 170, 190 168 S 300 190, 350 120 S 440 70, 548 52"/>
      <circle cx="10" cy="250" r="6" style="animation-delay:.6s"/>
      <circle cx="190" cy="168" r="5" style="animation-delay:1.5s"/>
      <circle cx="350" cy="120" r="5" style="animation-delay:2.4s"/>
      <circle cx="548" cy="52" r="7" style="animation-delay:3.2s"/>
    </svg>
    <h1>
      <span>Five kilometres.</span>
      <span>One hundred</span>
      <span>minutes.</span>
      <span class="thin">That is Varthur ward on the eastern edge of Bengaluru: 54,625 people,
      five kilometres from the nearest hospital, and a typical bus journey of an hour and forty
      minutes to reach it. Access to healthcare is not only about how many hospitals a city has.
      It is about whether people can get to one.</span>
    </h1>

    <div class="headline">
      <div class="bignum" data-count="__POP_OVER_45__">0</div>
      <p>people live in a ward where the typical bus journey to a hospital
      takes <b>45 minutes or more</b>. That is __PCT_OVER_45__ per cent of Bengaluru,
      spread across __WARDS_OVER_45__ wards on the eastern and southern edges of the city.</p>
    </div>

    <div class="stats">
      <div class="stat"><b data-count="__WARDS__">0</b><span>BBMP wards measured</span></div>
      <div class="stat"><b data-count="__HOSPITALS__">0</b><span>hospital sites</span></div>
      <div class="stat"><b data-count="__STOPS__">0</b><span>BMTC bus stops</span></div>
      <div class="stat"><b>__CITY_MEDIAN__ min</b><span>typical journey, citywide</span></div>
    </div>
  </div>
</header>

<section id="finding">
  <h2>Where the city stands</h2>
  <p class="lede">Every ward is covered with sample points 250 metres apart. Each point is routed
  to the nearest hospital on foot and by bus, and the ward keeps the median of its points, so the
  figure describes a typical resident rather than the luckiest corner.</p>
  <div class="ladder" id="ladder"></div>
</section>

<section id="map">
  <h2>The map</h2>
  <p class="lede">Green in the middle, red at the edges. The pattern follows the city's growth:
  the hospitals sit where Bengaluru was in 1990, and the wards added since are the ones waiting
  for a bus.</p>
  <div class="mapframe"><iframe src="map.html" title="Ward journey times to hospitals" loading="lazy"></iframe></div>
  <a class="chip" href="map.html">Open the full map</a>
  <a class="chip" href="https://github.com/yashasr21/bengaluru-bus-access">Code and data</a>
</section>

<section id="wards">
  <div class="two">
    <div>
      <h2>Worst served</h2>
      <p class="lede">Ranked by the typical journey from inside the ward.</p>
      <table class="tbl"><thead><tr><th>Ward</th><th>Minutes</th><th>People</th><th>Km away</th></tr></thead>
      <tbody id="worst"></tbody></table>
    </div>
    <div>
      <h2>Close, but slow</h2>
      <p class="lede">Wards within four kilometres of a hospital where the bus still takes far
      longer than the distance suggests. These are route problems, not hospital problems.</p>
      <table class="tbl"><thead><tr><th>Ward</th><th>Minutes</th><th>Km away</th><th>Bus vs crow</th></tr></thead>
      <tbody id="slow"></tbody></table>
    </div>
  </div>
</section>

<section id="scatter">
  <h2>Distance is not the story</h2>
  <p class="lede">Each dot is a ward: how far the nearest hospital is against how long the bus
  takes. If distance explained everything the dots would sit on a line. The ones high above it
  are wards the network has left behind.</p>
  <svg class="scatter" id="plot" viewBox="0 0 900 420" preserveAspectRatio="xMidYMid meet"></svg>
</section>

<section id="sensitivity">
  <h2>How much the answer moves</h2>
  <p class="lede">The headline rests on four assumptions. Changing each one, and leaving the rest
  alone, gives the numbers below. The finding survives all of them; it gets worse when you insist
  on a bus that actually turns up.</p>
  <table class="tbl"><thead><tr><th>Assumption</th><th>People over 45 min</th><th>Wards</th></tr></thead>
  <tbody id="sens"></tbody></table>
</section>

<section id="limits">
  <h2>What this cannot tell you</h2>
  <p class="lede">Four things are wrong with these numbers, and they are worth stating plainly
  because they all push in the same direction: the real journey is worse than the one modelled here.</p>
  <div class="limits">
    <div><h3>Scheduled, not real</h3><p>The times come from BMTC's published timetable. Bengaluru
    traffic is not in the data, so a journey shown as 40 minutes at 9 a.m. is optimistic.</p></div>
    <div><h3>Straight-line walking</h3><p>Walking distance is measured as a circle around each stop,
    not along the road network. Lakes, railway lines and roads without footpaths all make the real
    walk longer.</p></div>
    <div><h3>Public hospitals mostly</h3><p>The facility list comes from the Karnataka health GIS.
    It covers government hospitals and empanelled tertiary centres, and misses much of the private
    sector, which matters more in some wards than others.</p></div>
    <div><h3>Population spread evenly</h3><p>Ward population is assumed to be spread evenly across
    the ward. In a ward like Varthur it is not: people cluster along the main roads, which are also
    where the buses are.</p></div>
  </div>
</section>

<footer>
  <p>Built from three open datasets: the unofficial BMTC GTFS feed published 12 July 2026,
  the BBMP 2022 delimitation ward layer carrying Census 2011 population, and the Karnataka
  health department's facility layers. Method, code and the full ward table are in the
  <a href="https://github.com/yashasr21/bengaluru-bus-access">repository</a>.</p>
</footer>

</div>
<script>
const DATA = __DATA__;

const nf = new Intl.NumberFormat("en-IN");
const brightness = hex => {
  const v = hex.replace("#", "");
  const r = parseInt(v.slice(0, 2), 16), g = parseInt(v.slice(2, 4), 16), b = parseInt(v.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
};
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* counters ------------------------------------------------------------- */
document.querySelectorAll("[data-count]").forEach(el => {
  const target = Number(el.dataset.count);
  if (reduced) { el.textContent = nf.format(target); return; }
  const started = performance.now();
  const run = now => {
    const t = Math.min(1, (now - started) / 1400);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = nf.format(Math.round(target * eased));
    if (t < 1) requestAnimationFrame(run);
  };
  requestAnimationFrame(run);
});

/* band ladder ---------------------------------------------------------- */
const ladder = document.getElementById("ladder");
const biggest = Math.max(...DATA.bands.map(b => b.population));
DATA.bands.forEach((b, i) => {
  const row = document.createElement("div");
  row.className = "rung";
  row.innerHTML =
    `<div class="name">${b.band}</div>
     <div class="bar"><i style="background:${b.colour}"></i>
     <em>${nf.format(b.population)} people &middot; ${b.share}% &middot; ${b.wards} wards</em></div>`;
  ladder.appendChild(row);
  const fill = row.querySelector("i");
  const label = row.querySelector("em");
  const width = (b.population / biggest) * 100;

  // Put the caption inside the bar when there is room, and pick black or white
  // for it by the brightness of the band colour. The yellow band needs dark
  // text and the red band needs light text; guessing once for both looked bad.
  if (width < 40) {
    label.style.left = "calc(" + width + "% + 14px)";
    label.style.color = "var(--paper)";
  } else {
    label.style.color = brightness(b.colour) > 0.62 ? "#10101a" : "#ffffff";
  }
  if (reduced) { fill.style.width = width + "%"; }
  else setTimeout(() => { fill.style.width = width + "%"; }, 260 + i * 130);
});

/* tables --------------------------------------------------------------- */
const colourFor = m => m < 30 ? "#2E8B7A" : m < 45 ? "#E8C468" : m < 60 ? "#E08A4A" : "#C0392B";

document.getElementById("worst").innerHTML = DATA.worst.map(r =>
  `<tr><td class="ward"><span class="dot" style="background:${colourFor(r.median_min)}"></span>${r.ward_label}</td>
   <td>${r.median_min.toFixed(0)}</td><td>${nf.format(r.population)}</td>
   <td>${r.straight_line_km.toFixed(1)}</td></tr>`).join("");

document.getElementById("slow").innerHTML = DATA.close_but_slow.map(r =>
  `<tr><td class="ward"><span class="dot" style="background:${colourFor(r.median_min)}"></span>${r.ward_label}</td>
   <td>${r.median_min.toFixed(0)}</td><td>${r.straight_line_km.toFixed(1)}</td>
   <td>${r.penalty_ratio.toFixed(2)}&times;</td></tr>`).join("");

document.getElementById("sens").innerHTML = DATA.sensitivity.map(r =>
  `<tr><td class="ward">${r.label}</td><td>${nf.format(r.population_over_45)}</td>
   <td>${r.wards_over_45}</td></tr>`).join("");

/* scatter -------------------------------------------------------------- */
(function plot() {
  const svg = document.getElementById("plot");
  const W = 900, H = 420, L = 62, R = 18, T = 16, B = 46;
  const pts = DATA.scatter.filter(d => d.median_min != null);
  const maxX = Math.ceil(Math.max(...pts.map(d => d.straight_line_km)));
  const maxY = Math.ceil(Math.max(...pts.map(d => d.median_min)) / 20) * 20;
  const x = v => L + (v / maxX) * (W - L - R);
  const y = v => H - B - (v / maxY) * (H - T - B);
  let out = "";

  for (let g = 0; g <= maxY; g += 20) {
    out += `<line class="grid" x1="${L}" y1="${y(g)}" x2="${W - R}" y2="${y(g)}"/>`;
    out += `<text x="${L - 10}" y="${y(g) + 4}" text-anchor="end">${g}</text>`;
  }
  for (let g = 0; g <= maxX; g += 2) {
    out += `<text x="${x(g)}" y="${H - B + 20}" text-anchor="middle">${g}</text>`;
  }
  out += `<text x="${L}" y="${H - 8}" text-anchor="start">Straight-line kilometres to the nearest hospital</text>`;
  out += `<text transform="translate(16 ${T + 96}) rotate(-90)" text-anchor="middle">Typical bus journey, minutes</text>`;

  pts.forEach(d => {
    const r = Math.max(3.2, Math.sqrt(d.population) / 62);
    out += `<circle cx="${x(d.straight_line_km).toFixed(1)}" cy="${y(d.median_min).toFixed(1)}" r="${r.toFixed(1)}"
      fill="${d.band_colour}"><title>${d.ward_label} — ${d.median_min.toFixed(0)} min, ${nf.format(d.population)} people</title></circle>`;
  });
  svg.innerHTML = out;
})();
</script>
</body>
</html>
"""


def main():
    data = json.loads((DOCS / "dashboard_data.json").read_text())
    head = data["headline"]

    html = TEMPLATE
    html = html.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    html = html.replace("__POP_OVER_45__", str(head["pop_over_45"]))
    html = html.replace(
        "__PCT_OVER_45__", f"{head['pop_over_45'] / head['population'] * 100:.1f}"
    )
    html = html.replace("__WARDS_OVER_45__", str(head["wards_over_45"]))
    html = html.replace("__WARDS__", str(head["wards"]))
    html = html.replace("__HOSPITALS__", str(head["hospitals"]))
    html = html.replace("__STOPS__", str(head["stops"]))
    html = html.replace("__CITY_MEDIAN__", f"{head['city_median_min']:.0f}")

    (DOCS / "index.html").write_text(html, encoding="utf-8")
    size_kb = (DOCS / "index.html").stat().st_size / 1024
    print(f"wrote {DOCS / 'index.html'} ({size_kb:.0f} KB, no runtime fetch)")


if __name__ == "__main__":
    main()
