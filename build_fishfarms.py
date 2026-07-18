#!/usr/bin/env python3
"""Balık çiftliği (aquaculture) katmanı — açık veriden.

Her bölge için OSM'den balık çiftliği / dalyan (landuse=aquaculture,
seamark:type=marine_farm/fish_farm) noktalarını çeker, `demo/fishfarms.json`
önbelleğine yazar. build_demo.py bunları her bölgenin marks'ına 'fishfarm'
olarak ekler. Yeniden çalıştırılabilir: sadece önbellekte olmayan bölgeleri
çeker (Overpass yoğunsa tekrar koş, boşlukları doldurur).

    python build_fishfarms.py
"""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = json.load(open(os.path.join(HERE, "demo", "regions.json"), encoding="utf-8"))
CACHE = os.path.join(HERE, "demo", "fishfarms.json")
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
r = lambda v: round(v, 4)

def fetch(bbox):
    # bbox = [W,S,E,N] -> Overpass (S,W,N,E)
    s, w, n, e = bbox[1], bbox[0], bbox[3], bbox[2]
    q = (f'[out:json][timeout:80];('
         f'nwr["landuse"="aquaculture"]({s},{w},{n},{e});'
         f'nwr["seamark:type"="marine_farm"]({s},{w},{n},{e});'
         f'nwr["seamark:type"="fish_farm"]({s},{w},{n},{e}););out center 800;')
    body = urllib.parse.urlencode({"data": q}).encode()
    for url in MIRRORS:
        try:
            req = urllib.request.Request(url, data=body,
                headers={"User-Agent": "boreas-map-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
            out = []
            for el in data.get("elements", []):
                lon = el.get("lon") or (el.get("center") or {}).get("lon")
                lat = el.get("lat") or (el.get("center") or {}).get("lat")
                if lon is None or lat is None:
                    continue
                name = (el.get("tags", {}).get("name", "") or "").strip()
                out.append({"n": name, "c": [r(lon), r(lat)]})
            return out
        except Exception as ex:  # noqa: BLE001 - try next mirror
            host = urllib.parse.urlparse(url).netloc
            print(f"    {host} hata ({ex}); sonraki ayna")
            time.sleep(3)
    return None  # tüm aynalar başarısız

cache = {}
if os.path.exists(CACHE):
    cache = json.load(open(CACHE, encoding="utf-8"))

for reg in REGIONS:
    rid = reg["id"]
    if rid in cache:
        print(f"  {rid:20s} önbellekte ({len(cache[rid])})")
        continue
    print(f"  {rid:20s} çekiliyor…")
    marks = fetch(reg["bbox"])
    if marks is None:
        print(f"    ! {rid}: tüm aynalar başarısız, atlandı (tekrar koş)")
        continue
    cache[rid] = marks
    print(f"    {rid}: {len(marks)} balık çiftliği")
    json.dump(cache, open(CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    time.sleep(4)  # Overpass'a nazik ol

total = sum(len(v) for v in cache.values())
print(f"\n{len(cache)}/{len(REGIONS)} bölge · toplam {total} balık çiftliği · {CACHE}")
