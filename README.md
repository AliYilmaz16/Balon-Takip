# Balon Takip Sistemi
Teknofest Hava Savunma Sistemleri Yarışması için geliştirilmiştir.

## Proje Özeti

Bu proje, otonom hava savunma sistemleri için geliştirilmiş, yüksek performanslı ve hibrit bir hedef tespit ve takip (detection & tracking) sistemidir.

Gerçek zamanlı sistemlerde (Real-time Embedded Systems) karşılaşılan donanım kısıtları nedeniyle, en hafif model olan YOLOv8n (Nano) tercih edilmiştir. Nano modelin hafifliğinden kaynaklanan kararsızlık (jitter) ve frame kaçırma sorunları, özel olarak geliştirilen bir Durum Kestirim (State Estimation) algoritması ile çözülmüştür.

## Video ve Görsel Çıktılar

https://github.com/user-attachments/assets/8abe831c-b72a-40f8-9212-d3c8d0553ed5

![resim](https://github.com/user-attachments/assets/99bcd10d-d260-4834-83b6-7cd47969880a)


## Teknik Detaylar
1. Zorluk (The Challenge)

Donanım Kısıtı: Yarışma kuralları ve donanım limitleri nedeniyle yüksek FPS gerekiyordu.

Model Seçimi: YOLOv8n hızlıydı ancak uzak mesafede veya ani hareketlerde hedefi kaçırabiliyordu.

Stabilite Sorunu: Ham tespit verileri titreme (jitter) yapıyor, bu da atış mekanizmasını bozuyordu.

2. Çözüm (The Solution)

Hazır tracker algoritmaları (DeepSORT vb.) yerine, sisteme özel hibrit bir takip sınıfı (Python Class) geliştirildi:

⚡ Hız Vektörü Analizi (Velocity Vector Analysis): Hedefin geçmiş 8 konum verisi hafızada tutularak anlık hız vektörü (V x,V y) hesaplanır.

🔮 Prediktif Takip (Prediction): Kamera hedefi kaçırsa (missed frame) bile, fizik tabanlı hesaplama ile hedefin bir sonraki konumu tahmin edilir ve kilitlenme (lock-on) korunur.

📉 EMA Smoothing: Koordinat verileri Exponential Moving Average filtresinden geçirilerek titreme engellenir.

🎯 Dinamik Önceliklendirme: Sahnedeki tehditler "HEAD" (Ana Hedef) ve "Secondary" olarak ayrılır. En kararlı hedef otomatik seçilir.

## Kurulum (Installation)
Projeyi yerel makinenizde çalıştırmak için:

### 1- Repoyu klonlayın:

Bash
git clone https://github.com/kullaniciadi/proje-adi.git
cd proje-adi

### 2- Gereklilikleri yükleyin:

Bash
pip install ultralytics opencv-python numpy

### 3- Model Dosyası
Eğittiğimiz best.pt model dosyasını proje ana dizinine yerleştirin.

### 4- Çalıştırın:

Bash
python main.py

## Veri Seti (Dataset)
Modelin eğitimi için:

- Yarışma sahasına uygun balonlar ve uygun ortamlarda özel çekimler yapıldı.

- makesense.ai kullanılarak binlerce fotoğraf manuel olarak etiketlendi.

- Veri seti; farklı ışık koşulları, mesafeler ve açılarla zenginleştirildi.
