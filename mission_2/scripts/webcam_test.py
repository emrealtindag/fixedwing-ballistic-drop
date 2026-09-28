import cv2
import os
from ultralytics import YOLO

def main():
    # Eğittiğimiz best.pt dosyasının tam yolu
    model_path = r"C:\Users\Emre\Downloads\fixedwing-ballistic-drop-tekno\runs\detect\teknofest_iha-2\weights\best.pt"
    
    if not os.path.exists(model_path):
        print(f"❌ HATA: Model bulunamadı! Yol: {model_path}")
        return

    print("🧠 Yapay Zeka (best.pt) yükleniyor, lütfen bekleyin...")
    model = YOLO(model_path)
    print("✅ Model yüklendi! Kamera başlatılıyor...")

    # Web kamerasını aç (0 genelde laptop'un dahili kamerasıdır)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ HATA: Bilgisayar kamerası açılamadı!")
        return

    print("🚀 Kamera açıldı! Kapatmak için klavyeden 'q' tuşuna basın.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kameradan görüntü alınamıyor.")
            break

        # YOLO ile canlı tahmin yap (Kullanıcının isteği üzerine eşik %75 yapıldı)
        results = model.predict(source=frame, conf=0.75, verbose=False)

        # Çerçeveleri ve isimleri resmin üzerine çizdir
        annotated_frame = results[0].plot()

        # Ekranda göster
        cv2.imshow("TEKNOFEST IHA - Canli Hedef Tespiti (Cikmak icin Q)", annotated_frame)

        # 'q' tuşuna basılırsa döngüyü kır ve çık
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Kamerayı ve pencereleri serbest bırak
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
