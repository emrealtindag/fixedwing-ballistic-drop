"""
TEKNOFEST İHA Görev 2 - YOLOv8 Eğitim Scripti
Bu script, EVREN MLOps Platformu veya Google Colab üzerinde YOLOv8 modelini
sentetik veri setimizle eğitmek için optimize edilmiştir.
"""

import os
import sys
from ultralytics import YOLO

def main():
    print("🚀 TEKNOFEST İHA Görev 2 YOLOv8 Eğitimi Başlıyor...")

    # Roboflow'dan inen data.yaml dosyasının tam yolu
    dataset_yaml = r"C:\Users\Emre\Downloads\fixedwing-ballistic-drop-tekno\new.v1i.yolov8\data.yaml"
    
    if not os.path.exists(dataset_yaml):
        print(f"❌ HATA: {dataset_yaml} bulunamadı! Yolu doğru kopyaladığından emin ol.")
        return

    # İHA (Raspberry Pi / Jetson) üzerinde gerçek zamanlı çalışabilmesi için
    # en hafif model olan yolov8n (Nano) kullanıyoruz. (Biraz daha güç varsa 'yolov8s.pt' seçilebilir)
    model = YOLO('yolov8n.pt')

    # Eğitimi Başlat
    results = model.train(
        data=dataset_yaml,
        epochs=100,            # 100 Epoch sentetik veri için yeterlidir
        imgsz=640,             # Görüntü boyutu
        batch=16,              # GPU belleğine göre artırılabilir (32, 64)
        name='teknofest_iha',  # Çıktı klasörünün adı
        
        # --- TEKNOFEST'E ÖZEL OPTİMİZASYONLAR ---
        # 1. Küçük objeler (1 metrelik üçgen) olduğu için mozaik büyütmesini açıyoruz
        mosaic=1.0, 
        
        # 2. Sentetik veriyi Roboflow'da ürettiğimiz için YOLO'nun kendi içinde ekstra döndürme
        # (degrees) yapmasını KAPATIYORUZ. Çünkü YOLO resimleri döndürürken Bounding Box'ları (kareleri)
        # şişirir ve koordinat merkezini kaydırır!
        degrees=0.0,
        translate=0.1,         # Kameranın hedeften kayması
        scale=0.5,             # İrtifa değişimini simüle etme
        shear=2.0,             # Perspektif bozulması simülasyonu
        
        # 3. Aşırı uydurmayı (Overfitting) engellemek için
        dropout=0.1
    )

    print("\n✅ Eğitim Tamamlandı!")
    best_weights = os.path.join(results.save_dir, "weights", "best.pt")
    print(f"🎯 En iyi ağırlık dosyası şurada: {best_weights}")
    print("Bu 'best.pt' dosyasını İHA'nın beynindeki (demo_pipeline.py) model olarak kullanacaksın.")

if __name__ == '__main__':
    main()
