import re

file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# --- 1. HUD FIXES ---
text = re.sub(r'alt_warn = ".*SHGM!"', 'alt_warn = " [ALT LIMIT EXCEEDED!]"', text)
text = text.replace('BLUE:', 'BLUE:')
text = text.replace('BLUE??:', 'BLUE:')
text = text.replace('', '') # Remove any floating unicode replacement chars
# Move payload boxes down so they don't overlap with the top bar
text = text.replace('y0 = 50 + slot_idx * 32', 'y0 = 90 + slot_idx * 35')

# --- 2. TERMINAL LOG TRANSLATION ---
text = text.replace('G?rev loglar? olu?turuluyor', 'Creating mission logs')
text = text.replace('G\xc3\xb6rev loglar\xc4\xb1 olu\xc5\x9fturuluyor', 'Creating mission logs')
text = text.replace('Kalk?? tespit edildi', 'Takeoff detected')
text = text.replace('Kalk\xc4\xb1\xc5\x9f tespit edildi', 'Takeoff detected')
text = text.replace('alg?lama kilidi zamanlay?c?s? ba?lad?', 'detection gate timer started')
text = text.replace('alg\xc4\xb1lama kilidi zamanlay\xc4\xb1c\xc4\xb1s\xc4\xb1 ba\xc5\x9flad\xc4\xb1', 'detection gate timer started')
text = text.replace('SHGM ?RT?FA L?M?T? A?ILDI', 'ALTITUDE LIMIT EXCEEDED')
text = text.replace('SHGM \xc4\xb0RT\xc4\xb0FA L\xc4\xb0M\xc4\xb0T\xc4\xb0 A\xc5\x9eILDI', 'ALTITUDE LIMIT EXCEEDED')
text = text.replace('ALGILAMA K?L?D? A?ILDI', 'DETECTION GATE OPENED')
text = text.replace('ALGILAMA K\xc4\xb0L\xc4\xb0D\xc4\xb0 A\xc3\x87ILDI', 'DETECTION GATE OPENED')
text = text.replace('zaman kilidi (45s). GPS koordinat? girilmemi?ti.', 'time unlock (45s fallback used).')
text = text.replace('GPS tabanl?', 'GPS based')
text = text.replace('zaman kilidi', 'timer lock')
text = text.replace('Telemetri bayat; bu karede at?? karar? atlan?yor.', 'Telemetry stale; skipping drop decision for this frame.')
text = text.replace('Telemetri bayat; bu karede at\xc4\xb1\xc5\x9f karar\xc4\xb1 atlan\xc4\xb1yor.', 'Telemetry stale; skipping drop decision for this frame.')
text = text.replace('Video kayna?? a??lamad?', 'Failed to open video source')
text = text.replace('Video ak??? sonland? veya kare okunamad?.', 'Video stream ended or frame unreadable.')
text = text.replace('Kare i?lenirken ge?ici hata olu?tu, kare atlan?yor', 'Temporary error during frame processing, skipping frame')
text = text.replace('?l?mc?l hata nedeniyle boru hatt? durduruluyor', 'Fatal error, stopping pipeline')
text = text.replace('Kaynaklar serbest b?rak?l?yor...', 'Releasing resources...')
text = text.replace('g?rev g?nl??? kaydedilemedi', 'failed to save mission log')
text = text.replace('Master Pipeline v2 g?venle kapat?ld?.', 'Master Pipeline closed safely.')
text = text.replace('Tolerans', 'Tolerance')
text = text.replace('??k??', 'Exit')
text = text.replace('kare', 'frames')
text = text.replace('menzilde ama persistence bekleniyor', 'in range but waiting for persistence')
text = text.replace('MAV? HEDEF MENZ?LDE (Hata:', 'BLUE TARGET IN DROP ZONE (Error:')
text = text.replace('KIRMIZI HEDEF MENZ?LDE (Hata:', 'RED TARGET IN DROP ZONE (Error:')
text = text.replace('Tetikleniyor...', 'Triggering release...')
text = text.replace('DetectionGate ba?lat?ld?. Mod:', 'DetectionGate initialized. Mode:')
text = text.replace('ba?land?', 'connected')
text = text.replace('Al?nd?', 'Received')
text = text.replace('al?nd?', 'received')
text = text.replace('Master Pipeline v2 ba?lad?', 'Master Pipeline v2 started')

# Emoji removals in logger (which cause utf-8 terminal rendering issues)
text = re.sub(r'[\u2600-\u27BF]|[\uD83C][\uDF00-\uDFFF]|[\uD83D][\uDC00-\uDE4F]|[\uD83D][\uDE80-\uDEFF]', '', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
