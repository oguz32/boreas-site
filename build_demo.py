#!/usr/bin/env python3
"""Boreas web harita demosu — veri boru hattı.

marine-map'teki bölge paketlerinden (land + contours + seamarks) web demosu
için minify edilmiş, bölge-başına JSON'lar üretir + bir index yazar.

Uygulamada harita verisi güncellenince (yeni bölge, tazelenmiş tehlikeler…)
bu script'i tekrar çalıştır, sonra boreas-site'ı commit et — web hep senkron.

    python build_demo.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
MM = os.path.join(HERE, "..", "marine-map")
PKG = os.path.join(MM, "region-packages")
ASSETS = os.path.join(MM, "assets", "map")
OUT = os.path.join(HERE, "demo", "regions")
os.makedirs(OUT, exist_ok=True)

r = lambda v: round(v, 4)
def rc(pt): return [r(pt[0]), r(pt[1])]
def walkgeom(coords):
    if coords and isinstance(coords[0], (int, float)):
        return rc(coords)
    return [walkgeom(c) for c in coords]

def land_out(land):
    out = []
    for f in land.get("features", []):
        g = f["geometry"]
        out.append({"t": g["type"], "c": walkgeom(g["coordinates"])})
    return out

def contours_out(contours):
    out = []
    for c in contours:
        out.append({"d": c["depth"], "l": [[rc(p) for p in line] for line in c["lines"]]})
    return out

def marks_out(seamarks):
    feats = seamarks.get("features", seamarks) if isinstance(seamarks, dict) else seamarks
    out = []
    for f in feats:
        p = f.get("properties", {})
        g = f["geometry"]["coordinates"] if "geometry" in f else f["c"]
        out.append({"k": p.get("kind"), "n": p.get("name", "") or "",
                    "c": rc(g), "lt": p.get("light", "")})
    return out

def write_region(rid, name, bbox, land, contours, marks):
    obj = {"id": rid, "name": name, "bbox": [r(x) for x in bbox],
           "land": land, "contours": contours, "marks": marks}
    path = os.path.join(OUT, f"{rid}.json")
    open(path, "w", encoding="utf-8").write(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    kb = round(os.path.getsize(path) / 1024)
    return {"id": rid, "name": name, "bbox": obj["bbox"], "file": f"{rid}.json",
            "kb": kb, "marks": len(marks)}

# Display order + friendly names (grouped Türkiye first, then expansion).
ORDER = [
    ("marmara", "Marmara"),
    ("ege", "Ege"), ("gokova", "Gökova – Bodrum"),
    ("akdeniz-bati", "Akdeniz Batı"), ("akdeniz-dogu", "Akdeniz Doğu"),
    ("karadeniz-bati", "Karadeniz Batı"), ("karadeniz-dogu", "Karadeniz Doğu"),
    ("kibris", "Kıbrıs"),
    ("yunanistan-ion", "Yunanistan – İyonya"), ("yunanistan-ege", "Yunanistan – Ege"),
    ("yunanistan-girit", "Yunanistan – Girit"),
    ("ispanya-dogu", "İspanya – Katalonya/Valensiya"), ("ispanya-guney", "İspanya – Güney"),
    ("balear", "Balear Adaları"),
    ("portekiz-guney", "Portekiz – Algarve"), ("portekiz-bati", "Portekiz – Atlantik"),
    ("hirvatistan-kuzey", "Hırvatistan – Kuzey"), ("hirvatistan-guney", "Hırvatistan – Güney"),
    ("malta", "Malta"), ("karadag", "Karadağ"),
]

index = []
for rid, name in ORDER:
    if rid == "marmara":
        land = json.load(open(os.path.join(ASSETS, "marmara_land_v1.json"), encoding="utf-8"))
        con = json.load(open(os.path.join(ASSETS, "marmara_contours_v1.json"), encoding="utf-8"))["contours"]
        sea = json.load(open(os.path.join(ASSETS, "marmara_seamarks_v1.json"), encoding="utf-8"))
        bbox = [25.8, 39.7, 30.4, 41.8]
        entry = write_region(rid, name, bbox, land_out(land), contours_out(con), marks_out(sea))
    else:
        pkgpath = os.path.join(PKG, f"{rid}_v1.json")
        if not os.path.exists(pkgpath):
            print(f"  ! atlandı (paket yok): {rid}")
            continue
        d = json.load(open(pkgpath, encoding="utf-8"))
        entry = write_region(rid, name, d.get("bbox"),
                             land_out(d.get("land", {"features": []})),
                             contours_out(d.get("contours", [])),
                             marks_out(d.get("seamarks", {"features": []})))
    index.append(entry)
    print(f"  {entry['id']:20s} {entry['kb']:5d} KB  {entry['marks']:5d} işaret")

open(os.path.join(HERE, "demo", "regions.json"), "w", encoding="utf-8").write(
    json.dumps(index, ensure_ascii=False, separators=(",", ":")))
total = sum(e["kb"] for e in index)
print(f"\n{len(index)} bölge · toplam {total} KB · index yazıldı (regions.json)")
