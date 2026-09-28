import cv2
import numpy as np
import os
import random
from pathlib import Path
import math

# Ayarlar
NUM_IMAGES_TO_GENERATE = 2000
OUTPUT_DIR = Path("synthetic_dataset")
IMAGES_DIR = OUTPUT_DIR / "images"
LABELS_DIR = OUTPUT_DIR / "labels"
BG_DIR = Path("backgrounds")

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LABELS_DIR.mkdir(parents=True, exist_ok=True)
BG_DIR.mkdir(parents=True, exist_ok=True)

CLASS_BLUE_SQUARE = 0
CLASS_RED_SQUARE = 1

def check_overlap(box1, boxes):
    x1_min, y1_min, x1_max, y1_max = box1
    for box2 in boxes:
        x2_min, y2_min, x2_max, y2_max = box2
        pad = 5
        if not (x1_max + pad < x2_min or x1_min - pad > x2_max or y1_max + pad < y2_min or y1_min - pad > y2_max):
            return True
    return False

def add_tarp_texture(img):
    """Branda/muşamba dokusu ve güneş solmaları ekler (Noise + Gradient)."""
    alpha = img[:, :, 3]
    rgb = img[:, :, :3].astype(np.float32)
    
    # Kırışıklık simülasyonu (Gaussian bulanıklaştırılmış rastgele gürültü)
    noise = np.random.randint(0, 60, rgb.shape[:2], dtype=np.int16) - 30
    noise = cv2.GaussianBlur(noise.astype(np.float32), (9, 9), 0)
    
    for c in range(3):
        rgb[:, :, c] += noise
        
    # Parlaklık farklılıkları (Güneş solması)
    h, w = rgb.shape[:2]
    gradient = np.tile(np.linspace(0.8, 1.1, w), (h, 1)).astype(np.float32)
    for c in range(3):
        rgb[:, :, c] *= gradient
        
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return np.dstack((rgb, alpha))

def random_perspective(img, max_warp=0.15):
    """Kamera yatış (roll) ve yunuslama (pitch) açısı simülasyonu."""
    h, w = img.shape[:2]
    src_pts = np.float32([[0,0], [w,0], [w,h], [0,h]])
    
    dst_pts = np.float32([
        [w * random.uniform(0, max_warp), h * random.uniform(0, max_warp)],
        [w * random.uniform(1-max_warp, 1), h * random.uniform(0, max_warp)],
        [w * random.uniform(1-max_warp, 1), h * random.uniform(1-max_warp, 1)],
        [w * random.uniform(0, max_warp), h * random.uniform(1-max_warp, 1)]
    ])
    
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

def apply_motion_blur(img, max_size=15):
    """İHA seyir hızından kaynaklı motion blur ekler."""
    if random.random() > 0.5:
        return img
    size = random.randint(5, max_size)
    kernel = np.zeros((size, size))
    kernel[int((size-1)/2), :] = np.ones(size)
    kernel = kernel / size
    
    angle = random.randint(0, 360)
    M = cv2.getRotationMatrix2D((size/2-0.5, size/2-0.5), angle, 1)
    kernel = cv2.warpAffine(kernel, M, (size, size))
    return cv2.filter2D(img, -1, kernel)

def create_target(shape, color, side_length_px):
    # Işık/Kamera dengesine göre rengi biraz oyna (Color Jitter)
    color = (
        int(np.clip(color[0] + random.randint(-20, 20), 0, 255)),
        int(np.clip(color[1] + random.randint(-20, 20), 0, 255)),
        int(np.clip(color[2] + random.randint(-20, 20), 0, 255))
    )

    if shape == 'square':
        img = np.zeros((side_length_px, side_length_px, 4), dtype=np.uint8)
        cv2.rectangle(img, (0, 0), (side_length_px, side_length_px), (*color, 255), -1)
    elif shape == 'triangle':
        h = int(side_length_px * (3**0.5) / 2.0)
        img = np.zeros((h, side_length_px, 4), dtype=np.uint8)
        pts = np.array([[side_length_px//2, 0], [side_length_px, h], [0, h]], np.int32)
        cv2.fillPoly(img, [pts], (*color, 255))
    elif shape == 'hexagon':
        w = int(2 * side_length_px)
        h = int(side_length_px * (3**0.5))
        img = np.zeros((h, w, 4), dtype=np.uint8)
        center = (w//2, h//2)
        pts = []
        for i in range(6):
            angle_rad = math.radians(30 + i * 60)
            pts.append([int(center[0] + side_length_px * math.cos(angle_rad)), int(center[1] + side_length_px * math.sin(angle_rad))])
        cv2.fillPoly(img, [np.array(pts, np.int32)], (*color, 255))
        
    img = add_tarp_texture(img)
    return img

def overlay_image(bg, fg, x, y, angle):
    diagonal = int(math.hypot(fg.shape[0], fg.shape[1])) * 2
    padded_fg = np.zeros((diagonal, diagonal, 4), dtype=np.uint8)
    dx = (diagonal - fg.shape[1]) // 2
    dy = (diagonal - fg.shape[0]) // 2
    padded_fg[dy:dy+fg.shape[0], dx:dx+fg.shape[1]] = fg
    
    # 1. Homografi / Perspektif
    padded_fg = random_perspective(padded_fg)
    
    # 2. Döndürme
    M = cv2.getRotationMatrix2D((diagonal//2, diagonal//2), angle, 1.0)
    rotated_fg = cv2.warpAffine(padded_fg, M, (diagonal, diagonal), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    
    coords = np.argwhere(rotated_fg[:,:,3] > 0)
    if coords.size == 0: return bg, None
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    cropped_fg = rotated_fg[y0:y1+1, x0:x1+1]
    
    h, w = cropped_fg.shape[:2]
    bg_h, bg_w = bg.shape[:2]
    
    # Kısmi Kapanma (Occlusion) için sınırların dışına çıkmasına izin ver (kırp)
    if x >= bg_w or y >= bg_h or x + w <= 0 or y + h <= 0: return bg, None
    
    fg_x_min, fg_y_min, fg_x_max, fg_y_max = 0, 0, w, h
    bg_x_min, bg_y_min, bg_x_max, bg_y_max = x, y, x + w, y + h
    
    if bg_x_min < 0: fg_x_min -= bg_x_min; bg_x_min = 0
    if bg_y_min < 0: fg_y_min -= bg_y_min; bg_y_min = 0
    if bg_x_max > bg_w: fg_x_max -= (bg_x_max - bg_w); bg_x_max = bg_w
    if bg_y_max > bg_h: fg_y_max -= (bg_y_max - bg_h); bg_y_max = bg_h
    
    cropped_fg = cropped_fg[fg_y_min:fg_y_max, fg_x_min:fg_x_max]
    
    h, w = cropped_fg.shape[:2]
    alpha_fg = cropped_fg[:, :, 3] / 255.0
    alpha_bg = 1.0 - alpha_fg
    
    bg_patch = bg[bg_y_min:bg_y_max, bg_x_min:bg_x_max]
    
    for c in range(3):
        # Sonra cismi (renk) yapıştır
        bg_patch[:, :, c] = (alpha_fg * cropped_fg[:, :, c] + alpha_bg * bg_patch[:, :, c])
        
    bg[bg_y_min:bg_y_max, bg_x_min:bg_x_max] = bg_patch
    
    bbox = [bg_x_min, bg_y_min, bg_x_max, bg_y_max]
    return bg, bbox

def get_real_background():
    """Gerçek drone fotoğrafları klasöründen resim alır, yoksa prosedürel üretir."""
    # Doğru backgrounds klasörüne yönlendirme
    BG_DIR = Path(__file__).parent.parent.parent / "backgrounds"
    
    valid_exts = ['.jpg', '.jpeg', '.png', '.avif']
    if BG_DIR.exists():
        images = [p for p in BG_DIR.iterdir() if p.suffix.lower() in valid_exts]
        # %70 ihtimalle senin koyduğun gerçek fotoğrafları kullanacak,
        # %30 ihtimalle yapay zekayı zorlamak için eski usül (gürültülü) çim/toprak üretecek.
        if images and random.random() < 0.7:
            img_path = random.choice(images)
            # Türkçe karakterli dosya yolları için numpy ile okuyup OpenCV'ye çeviriyoruz
            bg_array = np.fromfile(str(img_path), dtype=np.uint8)
            bg = cv2.imdecode(bg_array, cv2.IMREAD_COLOR)
            
            if bg is not None:
                h, w = bg.shape[:2]
                if h >= 640 and w >= 640:
                    y = random.randint(0, h - 640)
                    x = random.randint(0, w - 640)
                    return bg[y:y+640, x:x+640].copy()
                return cv2.resize(bg, (640, 640))
                
    # Fallback: Prosedürel
    bg_type = random.choice(['grass', 'dirt', 'asphalt'])
    bg = np.zeros((640, 640, 3), dtype=np.uint8)
    if bg_type == 'grass': base_color = (random.randint(20, 60), random.randint(80, 140), random.randint(20, 60))
    elif bg_type == 'dirt': base_color = (random.randint(40, 80), random.randint(70, 120), random.randint(90, 150))
    else: g = random.randint(80, 120); base_color = (g, g, g)
    bg[:] = base_color
    bg = np.clip(bg + np.random.randn(640, 640, 3) * 25, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(bg, (5, 5), 0)

def generate_dataset():
    print("Profesyonel Veri Üretimi Başlatılıyor... Lütfen 'backgrounds' klasörüne gerçek saha resimleri atın!")
    
    for i in range(NUM_IMAGES_TO_GENERATE):
        bg = get_real_background()
        labels = []
        placed_boxes = []
        
        # 1 metrenin kameradaki piksel karşılığı. İrtifayı biraz daha alçak simüle edelim (20-40m arası)
        # ki yapay zeka küçük nesnelerin (üçgen vb.) şekilsel özelliklerini (köşelerini) net öğrenebilsin.
        px_per_meter = random.randint(20, 40)
        
        objects = [
            {'shape': 'square', 'color': (255, 50, 50), 'side': 4 * px_per_meter, 'class_id': CLASS_BLUE_SQUARE},
            {'shape': 'square', 'color': (50, 50, 255), 'side': 2 * px_per_meter, 'class_id': CLASS_RED_SQUARE},
            {'shape': 'hexagon', 'color': (255, 50, 50), 'side': 2 * px_per_meter, 'class_id': -1},
            # Üçgeni sistemin daha iyi öğrenmesi için gerçekte 1m olmasına rağmen 1.5m gibi biraz daha büyük çizdiriyoruz
            {'shape': 'triangle', 'color': (50, 50, 255), 'side': 1.5 * px_per_meter, 'class_id': -1}
        ]
        
        random.shuffle(objects)
        
        for obj in objects:
            if obj['class_id'] == -1 and random.random() > 0.8: continue
                
            img_obj = create_target(obj['shape'], obj['color'], int(obj['side']))
            
            for _ in range(15):
                max_w = int(math.hypot(img_obj.shape[0], img_obj.shape[1])) * 2
                
                # Kenarlardan taşmasına izin veriyoruz (Occlusion)
                x = random.randint(-max_w//2, 640 - max_w//2)
                y = random.randint(-max_w//2, 640 - max_w//2)
                angle = random.randint(0, 360)
                
                test_box = [max(0, x), max(0, y), min(640, x + max_w), min(640, y + max_w)]
                if not check_overlap(test_box, placed_boxes):
                    bg, bbox = overlay_image(bg, img_obj, x, y, angle)
                    if bbox is not None:
                        # Görünür alan %20'den azsa etiketleme
                        bw, bh = bbox[2]-bbox[0], bbox[3]-bbox[1]
                        if bw * bh > (max_w * max_w * 0.05): 
                            placed_boxes.append(bbox)
                            if obj['class_id'] != -1:
                                x_c, y_c = (bbox[0] + bbox[2])/2 / 640.0, (bbox[1] + bbox[3])/2 / 640.0
                                w_n, h_n = bw / 640.0, bh / 640.0
                                labels.append(f"{obj['class_id']} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}\n")
                    break
                    
        # JPEG Artefaktları simülasyonu
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), random.randint(70, 95)]
        _, encimg = cv2.imencode('.jpg', bg, encode_param)
        bg = cv2.imdecode(encimg, 1)

        cv2.imwrite(str(IMAGES_DIR / f"synth_{i:04d}.jpg"), bg)
        with open(LABELS_DIR / f"synth_{i:04d}.txt", "w") as f:
            f.writelines(labels)
            
    print(f"Bitti! {NUM_IMAGES_TO_GENERATE} adet görsel hazır.")

if __name__ == "__main__":
    generate_dataset()
