"""
TEKNOFEST 2026 - GOREV 1: OTONOM 8 CIZME
Waypoint Dosyasi Otomatik Olusturucu v2.0

Degisiklikler (v2):
- Kavisler 5 noktaya cikarildi (dumduz sonsuzluk isareti)
- Inis paterni duzgun trafik turu (dikdortgen) olarak yeniden cizildi
- Direk konumlari KML dosyasina yaziliyor (Mission Planner'da gorunur)
- Direkler arasi mesafe ve kavis yaricapi ayarlanabilir

Kullanim:
    python generate_mission1.py

Cikti:
    gorev1_ruzgar_A.waypoints  (Mission Planner -> Load File)
    gorev1_direkler.kml        (Mission Planner -> sag tikla -> Load KML Overlay)
"""

import math
import os

# ============================================================
# AYARLAR - Yarisma gunu sadece bu degerleri degistir
# ============================================================

# Referans koordinat = iki diregin TAM ORTASI
# Burayi degistirirsen tum rota (8 cizme + inis) toplu halde oraya tasir
# Ornek: Ankara Etimesgut icin REF_LAT = 39.9499, REF_LON = 32.6881
REF_LAT = 38.3544163
REF_LON = 38.2547265

# Rotanin yon acisi (derece) - 0 = doguya dogru, 90 = kuzeye dogru
# Bunu degistirerek 8 cizme yonunu ruzgara/piste gore dondur
ROTATION_DEG = 45

# Direkler arasi mesafe (metre) - sartnamede 150m planlandi ama degisebilir
POLE_DISTANCE = 150

# Kavis Yaricapi (metre) - Diregin etrafindan ne kadar genis donecegi
# Diger yapay zekanin hakli oldugu yer: Ruzgar payi icin bunu 45 yapiyoruz
CURVE_RADIUS = 45

# Ucus Irtifasi (metre)
CRUISE_ALT = 35
FINISH_ALT = 30
DOWNWIND_ALT = 25
BASE_ALT = 15
APPROACH_ALT = 10

# Kalkis Pitch Acisi
TAKEOFF_PITCH = 15

# Pistin 1. direge olan uzakligi (metre)
RUNWAY_TO_POLE1 = 100

# Inis trafik turu genisligi (metre)
LANDING_OFFSET_SOUTH = 80    # pistin guneyine mesafe
LANDING_EXTEND_WEST = 80     # pistin batisina uzama

# ============================================================
# KOORDINAT DONUSUM
# ============================================================

def meters_to_lat(meters):
    return meters / 111320.0

def meters_to_lon(meters, lat):
    return meters / (111320.0 * math.cos(math.radians(lat)))

def local_to_gps(x, y, ref_lat, ref_lon):
    """Yerel x,y (metre) -> GPS. ROTATION_DEG kadar dondurur."""
    angle = math.radians(ROTATION_DEG)
    rx = x * math.cos(angle) - y * math.sin(angle)
    ry = x * math.sin(angle) + y * math.cos(angle)
    lat = ref_lat + meters_to_lat(ry)
    lon = ref_lon + meters_to_lon(rx, ref_lat)
    return lat, lon

# ============================================================
# ROTA OLUSTURMA
# ============================================================

def curve_points(pole_x, pole_y, radius, angles):
    """Bir diregin etrafinda verilen acilarda kavis noktalari olustur"""
    points = []
    for a in angles:
        x = pole_x + radius * math.cos(math.radians(a))
        y = pole_y + radius * math.sin(math.radians(a))
        points.append((x, y))
    return points

def wp(cmd, lat, lon, alt, p1=0, label=""):
    return {'cmd': cmd, 'lat': lat, 'lon': lon, 'alt': alt, 'p1': p1, 'label': label}

def generate_figure8():
    half = POLE_DISTANCE / 2.0
    pole1_x = -half      # 1. direk (sol)
    pole2_x = half       # 2. direk (sag)
    R = CURVE_RADIUS

    takeoff_x = pole1_x - RUNWAY_TO_POLE1
    center_x, center_y = 0, 0

    # 5 noktali duzgun yarim daire acilari
    # 2. direk (sag taraf, saat yonunde): ust-sag -> sag -> alt-sag
    p2_angles = [80, 40, 0, -40, -80]
    # 1. direk (sol taraf, saat tersine): alt-sol -> sol -> ust-sol
    p1_angles = [100, 140, 180, -140, -100]
    # Son dis donus (2. direk, 3 nokta yeterli)
    final_angles = [60, 0, -60]

    wps = []

    # ═══ PIST VE ALANA GIRIS ═══
    wps.append(wp(22, 0, 0, CRUISE_ALT, TAKEOFF_PITCH,
                  'TAKEOFF - Pist (kalkis noktasi)'))

    lat, lon = local_to_gps(pole1_x, 0, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                  '1. Direk hizasi (ucus alanina giris)'))

    # ═══ 1. TUR ═══
    for i, (x, y) in enumerate(curve_points(pole2_x, 0, R, p2_angles)):
        lat, lon = local_to_gps(x, y, REF_LAT, REF_LON)
        wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                      f'2. Direk kavisi {i+1}/5 (1. tur)'))

    lat, lon = local_to_gps(center_x, center_y, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, CRUISE_ALT, 0, 'Gobek gecisi (1. tur)'))

    for i, (x, y) in enumerate(curve_points(pole1_x, 0, R, p1_angles)):
        lat, lon = local_to_gps(x, y, REF_LAT, REF_LON)
        wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                      f'1. Direk kavisi {i+1}/5 (1. tur)'))

    # ═══ 2. TUR ═══
    lat, lon = local_to_gps(center_x, center_y, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, CRUISE_ALT, 0, 'Gobek gecisi (2. tur basi)'))

    for i, (x, y) in enumerate(curve_points(pole2_x, 0, R, p2_angles)):
        lat, lon = local_to_gps(x, y, REF_LAT, REF_LON)
        wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                      f'2. Direk kavisi {i+1}/5 (2. tur)'))

    lat, lon = local_to_gps(center_x, center_y, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, CRUISE_ALT, 0, 'Gobek gecisi (2. tur sonu)'))

    for i, (x, y) in enumerate(curve_points(pole1_x, 0, R, p1_angles)):
        lat, lon = local_to_gps(x, y, REF_LAT, REF_LON)
        wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                      f'1. Direk kavisi {i+1}/5 (2. tur)'))

    # ═══ SON DIS DONUS (Sartname Kurali) ═══
    lat, lon = local_to_gps(center_x, center_y, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                  'Son gobek gecisi (sartname kurali)'))

    for i, (x, y) in enumerate(curve_points(pole2_x, 0, R, final_angles)):
        lat, lon = local_to_gps(x, y, REF_LAT, REF_LON)
        wps.append(wp(16, lat, lon, CRUISE_ALT, 0,
                      f'2. Direk son dis donus {i+1}/3'))

    # ═══ BITIS CIZGISI ═══
    lat, lon = local_to_gps(pole1_x, 0, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, FINISH_ALT, 0,
                  'BITIS CIZGISI - Kronometre durur!'))

    # ═══ INIS PATERNI (Sol El Trafik Turu) ═══
    # Ucak batiya (sola) dogru ucuyor. Duzgun dikdortgen trafik turu:
    # 1. Ruzgar alti (downwind): pistin guneyine offset, batiya uzat
    # 2. Esas bacak (base): guneybatida donus
    # 3. Son yaklasma (final): piste hizalan, doguya dogru in
    # 4. LAND: piste teker koy

    wps.append(wp(189, 0, 0, 0, 0, 'DO_LAND_START (inis proseduru)'))

    # Downwind - pistin 150m guneyinde, doguya dogru
    lat, lon = local_to_gps(center_x, -LANDING_OFFSET_SOUTH, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, DOWNWIND_ALT, 0,
                  'Ruzgar alti bacagi (downwind)'))

    # Base - guneybatida donus noktasi
    lat, lon = local_to_gps(takeoff_x - LANDING_EXTEND_WEST, -LANDING_OFFSET_SOUTH,
                            REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, BASE_ALT, 0,
                  'Esas bacak (base turn)'))

    # Final approach - pistin batisinda, pist cizgisine hizali
    lat, lon = local_to_gps(takeoff_x - LANDING_EXTEND_WEST, 0, REF_LAT, REF_LON)
    wps.append(wp(16, lat, lon, APPROACH_ALT, 0,
                  'Son yaklasma (final approach)'))

    # LAND
    lat, lon = local_to_gps(takeoff_x, 0, REF_LAT, REF_LON)
    wps.append(wp(21, lat, lon, 0, 0,
                  'LAND - Teker koyma'))

    return wps, pole1_x, pole2_x

# ============================================================
# DOSYA YAZMA
# ============================================================

def write_waypoint_file(waypoints, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, filename)

    with open(filepath, 'w') as f:
        f.write("QGC WPL 110\n")
        home_lat, home_lon = local_to_gps(
            -POLE_DISTANCE / 2 - RUNWAY_TO_POLE1, 0, REF_LAT, REF_LON
        )
        f.write(f"0\t1\t0\t16\t0\t0\t0\t0\t"
                f"{home_lat:.8f}\t{home_lon:.8f}\t{CRUISE_ALT}\t1\n")

        for i, w in enumerate(waypoints):
            f.write(f"{i+1}\t0\t3\t{w['cmd']}\t{w['p1']}\t0\t0\t0\t"
                    f"{w['lat']:.8f}\t{w['lon']:.8f}\t{w['alt']}\t1\n")

    print(f"\n  [OK] Waypoint dosyasi: {filepath}")
    print(f"       Toplam {len(waypoints)} satir yazildi.")
    return filepath

def write_kml_file(pole1_x, pole2_x, filename):
    """Direk konumlarini KML dosyasina yaz (Mission Planner haritasinda gorunur)"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, filename)

    p1_lat, p1_lon = local_to_gps(pole1_x, 0, REF_LAT, REF_LON)
    p2_lat, p2_lon = local_to_gps(pole2_x, 0, REF_LAT, REF_LON)

    # Basit bir KML ile direkleri "kirmizi raptiye" olarak haritada goster
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>TEKNOFEST Direkleri</name>
    <description>Gorev 1 - 8 cizme direkleri ({POLE_DISTANCE}m aralik)</description>

    <Style id="poleStyle">
      <IconStyle>
        <color>ff0000ff</color>
        <scale>1.5</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <color>ff0000ff</color>
        <scale>1.2</scale>
      </LabelStyle>
    </Style>

    <Placemark>
      <name>1. DIREK (SOL)</name>
      <description>1. Direk - Ucus alani sol siniri</description>
      <styleUrl>#poleStyle</styleUrl>
      <Point>
        <coordinates>{p1_lon:.8f},{p1_lat:.8f},0</coordinates>
      </Point>
    </Placemark>

    <Placemark>
      <name>2. DIREK (SAG)</name>
      <description>2. Direk - Ucus alani sag siniri</description>
      <styleUrl>#poleStyle</styleUrl>
      <Point>
        <coordinates>{p2_lon:.8f},{p2_lat:.8f},0</coordinates>
      </Point>
    </Placemark>

    <Placemark>
      <name>BITIS/BASLANGIC CIZGISI</name>
      <description>Kronometre burada durur</description>
      <Style>
        <IconStyle>
          <color>ff00ff00</color>
          <scale>1.3</scale>
          <Icon>
            <href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
          </Icon>
        </IconStyle>
      </Style>
      <Point>
        <coordinates>{p1_lon:.8f},{p1_lat:.8f},0</coordinates>
      </Point>
    </Placemark>

    <Placemark>
      <name>Direkler Arasi Mesafe</name>
      <description>{POLE_DISTANCE} metre</description>
      <LineString>
        <coordinates>
          {p1_lon:.8f},{p1_lat:.8f},0
          {p2_lon:.8f},{p2_lat:.8f},0
        </coordinates>
      </LineString>
      <Style>
        <LineStyle>
          <color>ff0000ff</color>
          <width>3</width>
        </LineStyle>
      </Style>
    </Placemark>

  </Document>
</kml>"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(kml)

    print(f"  [OK] Direk KML dosyasi: {filepath}")
    print(f"       Mission Planner'da sag tikla -> 'Load KML Overlay' ile yukle.")
    return filepath

# ============================================================
# ANA PROGRAM
# ============================================================

if __name__ == "__main__":
    CMD_NAMES = {22: 'TAKEOFF', 16: 'WAYPOINT', 21: 'LAND', 189: 'DO_LAND_START'}

    print()
    print("=" * 65)
    print("  TEKNOFEST 2026 - GOREV 1: OTONOM 8 CIZME  (v2.0)")
    print("  Duzgun Sonsuzluk Isareti + Direk Isareti + Trafik Turu")
    print("=" * 65)
    print()
    print(f"  [*] Referans Koordinat : {REF_LAT}, {REF_LON}")
    print(f"  [*] Direkler Arasi     : {POLE_DISTANCE} metre")
    print(f"  [*] Kavis Yaricapi     : {CURVE_RADIUS} metre (disaridan donus)")
    print(f"  [*] Ucus Irtifasi      : {CRUISE_ALT} metre (AGL)")
    print(f"  [*] Kalkis Pitch       : {TAKEOFF_PITCH} derece")
    print(f"  [*] Pist -> 1. Direk   : {RUNWAY_TO_POLE1} metre")
    print()

    waypoints, pole1_x, pole2_x = generate_figure8()

    # Direk GPS koordinatlarini hesapla ve goster
    p1_lat, p1_lon = local_to_gps(pole1_x, 0, REF_LAT, REF_LON)
    p2_lat, p2_lon = local_to_gps(pole2_x, 0, REF_LAT, REF_LON)

    print(f"  DIREK KONUMLARI:")
    print(f"  1. Direk (SOL): Lat={p1_lat:.6f}  Lon={p1_lon:.6f}")
    print(f"  2. Direk (SAG): Lat={p2_lat:.6f}  Lon={p2_lon:.6f}")
    print(f"  Aralarindaki mesafe: {POLE_DISTANCE} metre")
    print()

    print(f"  OLUSTURULAN ROTA ({len(waypoints)} satir):")
    print("  " + "-" * 63)
    for i, w in enumerate(waypoints):
        cmd_name = CMD_NAMES.get(w['cmd'], str(w['cmd']))
        alt_str = f"Alt={w['alt']:2.0f}m" if w['alt'] > 0 else "Alt= --"
        print(f"  {i+1:2d}: {cmd_name:14s} {alt_str:10s} | {w['label']}")
    print("  " + "-" * 63)

    # Dosyalari olustur
    print()
    write_waypoint_file(waypoints, "gorev1_ruzgar_A.waypoints")
    write_kml_file(pole1_x, pole2_x, "gorev1_direkler.kml")

    print()
    print("  " + "=" * 63)
    print("  MISSION PLANNER'DA YUKLEME:")
    print("  1. Plan sekmesi -> 'Load File' -> gorev1_ruzgar_A.waypoints")
    print("  2. Haritaya sag tikla -> 'Load KML Overlay' -> gorev1_direkler.kml")
    print("     (Direklerin yeri kirmizi raptiye olarak gorunecek)")
    print("  " + "=" * 63)
    print()

