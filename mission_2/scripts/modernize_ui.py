import re

file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

new_hud = '''def draw_hud(
    frame: np.ndarray,
    telemetry: TelemetryDispatcher,
    min_err: Optional[float],
    min_err_class: Optional[str],
    p1_done: bool,
    p2_done: bool,
    gate: DetectionGate,
    persistence: PersistenceTracker,
) -> None:
    h, w = frame.shape[:2]
    
    # 1. Transparent Military Overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 65), (15, 20, 15), -1)
    cv2.rectangle(overlay, (0, h - 35), (w, h), (15, 20, 15), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # 2. Modern Colors (BGR)
    CYAN = (255, 230, 0)   # A nice aerospace cyan
    GREEN = (50, 255, 50)  # Bright green
    RED = (50, 50, 255)    # Danger red
    AMBER = (0, 165, 255)  # Warning amber
    
    # 3. Fighter Jet Style Crosshair
    cx, cy = w // 2, h // 2
    cv2.line(frame, (cx - 30, cy), (cx - 10, cy), GREEN, 2)
    cv2.line(frame, (cx + 10, cy), (cx + 30, cy), GREEN, 2)
    cv2.line(frame, (cx, cy - 30), (cx, cy - 10), GREEN, 2)
    cv2.line(frame, (cx, cy + 10), (cx, cy + 30), GREEN, 2)
    cv2.circle(frame, (cx, cy), 4, RED, -1)
    cv2.circle(frame, (cx, cy), 50, GREEN, 1, cv2.LINE_AA)
    
    # Corner brackets for the crosshair
    l = 15
    cv2.line(frame, (cx-50, cy-50), (cx-50+l, cy-50), GREEN, 2)
    cv2.line(frame, (cx-50, cy-50), (cx-50, cy-50+l), GREEN, 2)
    cv2.line(frame, (cx+50, cy-50), (cx+50-l, cy-50), GREEN, 2)
    cv2.line(frame, (cx+50, cy-50), (cx+50, cy-50+l), GREEN, 2)
    cv2.line(frame, (cx-50, cy+50), (cx-50+l, cy+50), GREEN, 2)
    cv2.line(frame, (cx-50, cy+50), (cx-50, cy+50-l), GREEN, 2)
    cv2.line(frame, (cx+50, cy+50), (cx+50-l, cy+50), GREEN, 2)
    cv2.line(frame, (cx+50, cy+50), (cx+50, cy+50-l), GREEN, 2)

    # 4. Top Telemetry Row
    vg = math.hypot(telemetry.ground_vx.value, telemetry.ground_vy.value)
    va = telemetry.airspeed.value
    err_str = f"{min_err:05.1f}m" if min_err is not None else " N/A "
    
    alt_val = telemetry.altitude_agl.value
    alt_color = RED if alt_val > MAX_ALTITUDE_SHGM_M else CYAN
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, f"ALT: {alt_val:05.1f}M", (15, 25), font, 0.55, alt_color, 2, cv2.LINE_AA)
    cv2.putText(frame, f"SPD: {vg:04.1f}M/S", (160, 25), font, 0.55, CYAN, 2, cv2.LINE_AA)
    cv2.putText(frame, f"MOD: {telemetry.flight_mode[:8]}", (320, 25), font, 0.55, AMBER, 2, cv2.LINE_AA)
    cv2.putText(frame, f"TGT ERR: {err_str}", (470, 25), font, 0.55, CYAN, 2, cv2.LINE_AA)
    
    # 5. Second Row (Attitude & System)
    cv2.putText(frame, f"ROLL: {telemetry.roll.value:+05.1f}", (15, 52), font, 0.45, CYAN, 1, cv2.LINE_AA)
    cv2.putText(frame, f"PTCH: {telemetry.pitch.value:+05.1f}", (160, 52), font, 0.45, CYAN, 1, cv2.LINE_AA)
    
    gate_color = RED if gate.is_locked else GREEN
    gate_txt = "SYS: LOCKED [STDBY]" if gate.is_locked else "SYS: ARMED [SEARCH]"
    cv2.putText(frame, gate_txt, (320, 52), font, 0.45, gate_color, 1, cv2.LINE_AA)
    
    ptxt = f"TRACK: R[{persistence.counts['red']}/3] B[{persistence.counts['blue']}/3]"
    cv2.putText(frame, ptxt, (470, 52), font, 0.45, CYAN, 1, cv2.LINE_AA)

    # 6. Bottom Payload Status Bars
    def draw_slot(x, y, label, is_done):
        color = RED if is_done else GREEN
        status = "DROPPED" if is_done else "READY"
        
        # Draw sleek UI box
        cv2.rectangle(frame, (x, y), (x + 200, y + 25), color, 1)
        cv2.rectangle(frame, (x, y), (x + 5, y + 25), color, -1)
        
        cv2.putText(frame, f"{label} : {status}", (x + 15, y + 17), font, 0.45, color, 1, cv2.LINE_AA)

    draw_slot(15, h - 30, "PL-1 [RED]", p1_done)
    draw_slot(230, h - 30, "PL-2 [BLU]", p2_done)
'''

start_idx = text.find('def draw_hud(')
end_idx = text.find('def process_frame(')

if start_idx != -1 and end_idx != -1:
    new_text = text[:start_idx] + new_hud + '\n\n' + text[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("UI modernized!")
else:
    print("Could not find draw_hud.")
