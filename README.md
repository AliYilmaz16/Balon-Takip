# Balon-Takip
Teknofest Hava Savunma Sistemleri Yarışması için geliştirilmiştir.

## Proje Özeti

Bu proje, otonom hava savunma sistemleri için geliştirilmiş, yüksek performanslı ve hibrit bir hedef tespit ve takip (detection & tracking) sistemidir.

Gerçek zamanlı sistemlerde (Real-time Embedded Systems) karşılaşılan donanım kısıtları nedeniyle, en hafif model olan YOLOv8n (Nano) tercih edilmiştir. Nano modelin hafifliğinden kaynaklanan kararsızlık (jitter) ve frame kaçırma sorunları, özel olarak geliştirilen bir Durum Kestirim (State Estimation) algoritması ile çözülmüştür.

## Video ve Görsel Çıktılar

![Demo Video](ciktilar/video.mp4)
