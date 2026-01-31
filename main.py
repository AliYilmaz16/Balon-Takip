import cv2
import numpy as np
from ultralytics import YOLO
import time
import threading
import math

class Balon:
    """Ultra kararlı balon düğümü"""
    def __init__(self, X1, X2, Y1, Y2, guvenSkoru, tip="HEAD"):
        self.X1 = X1
        self.X2 = X2
        self.Y1 = Y1
        self.Y2 = Y2
        self.guvenSkoru = guvenSkoru
        self.tip = tip
        self.zamanDamgasi = time.time()
        self.sonGorulen = time.time()
        
        # Kararlılık için önemli değişkenler
        self.olusturulmaZamani = time.time()
        self.kilitliMi = False  # İlk 3 saniye kilitli kalacak
        self.kilitSuresi = 2.0  # 2 saniye kilitlenme süresi
        self.toplameHits = 0    # Toplam başarılı hit sayısı
        self.stabiliteSkoru = 0  # Ne kadar stabil olduğu
        
        # Hareket takibi
        self.oncekiKonumlar = []
        self.hizVektoruX = 0
        self.hizVektoruY = 0
        self.tahminEdilenX = None
        self.tahminEdilenY = None
        
        # Çok sıkı miss kontrolü
        self.consecutiveMisses = 0
        self.consecutiveHits = 0
        self.maxMisses = 2  # Sadece 2 frame kaçırabilir
        
        # İlk konumu kaydet
        merkezX, merkezY = self.ortaNokta()
        self.oncekiKonumlar.append((merkezX, merkezY, time.time()))
    
    def ortaNokta(self):
        """Balonun merkez koordinatı"""
        return (self.X1 + self.X2) // 2, (self.Y1 + self.Y2) // 2
    
    def mesafe(self, digerBalon):
        """İki balon arasındaki mesafe"""
        x1, y1 = self.ortaNokta()
        x2, y2 = digerBalon.ortaNokta()
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
    
    def isLocked(self):
        """Bu balon kilitli mi? (İlk birkaç saniye değiştirilmemeli)"""
        gecenSure = time.time() - self.olusturulmaZamani
        return gecenSure < self.kilitSuresi or self.toplameHits > 15
    
    def guncelle(self, X1, X2, Y1, Y2, guvenSkoru):
        """Daha responsive güncelleme"""
        # Daha hızlı smoothing - daha iyi takip
        smoothing = 0.6  # Daha hızlı adaptasyon
        self.X1 = int(self.X1 * smoothing + X1 * (1 - smoothing))
        self.Y1 = int(self.Y1 * smoothing + Y1 * (1 - smoothing))
        self.X2 = int(self.X2 * smoothing + X2 * (1 - smoothing))
        self.Y2 = int(self.Y2 * smoothing + Y2 * (1 - smoothing))
        
        # Güven skoru daha hızlı değişir
        self.guvenSkoru = max(self.guvenSkoru * 0.8 + guvenSkoru * 0.2, guvenSkoru)
        self.sonGorulen = time.time()
        self.zamanDamgasi = time.time()
        
        # Hit sayaçları
        self.consecutiveHits += 1
        self.consecutiveMisses = 0
        self.toplameHits += 1
        
        # Stabilite skoru artır
        self.stabiliteSkoru = min(self.stabiliteSkoru + 1, 100)
        
        # Hız vektörünü güncelle
        self.hizVektoruGuncelle()
    
    def missedFrame(self):
        """Frame kaçırıldığında - çok yavaş düşürme"""
        self.consecutiveMisses += 1
        self.consecutiveHits = 0
        # Güven skorunu çok az düşür
        self.guvenSkoru *= 0.95  # Çok yavaş düşüş
        # Stabilite skorunu düşür
        self.stabiliteSkoru = max(0, self.stabiliteSkoru - 2)
    
    def hizVektoruGuncelle(self):
        """Gelişmiş hız hesaplama ve tahmin"""
        merkezX, merkezY = self.ortaNokta()
        suankiZaman = time.time()
        self.oncekiKonumlar.append((merkezX, merkezY, suankiZaman))
        
        # Daha fazla konum sakla - daha iyi hız hesabı
        if len(self.oncekiKonumlar) > 8:
            self.oncekiKonumlar.pop(0)
        
        # Çoklu nokta kullanarak daha stabil hız hesapla
        if len(self.oncekiKonumlar) >= 3:
            # Son 3 noktanın ortalamasını al
            toplamDx = 0
            toplamDy = 0
            toplamDt = 0
            validSayac = 0
            
            for i in range(len(self.oncekiKonumlar) - 1):
                nokta1 = self.oncekiKonumlar[i]
                nokta2 = self.oncekiKonumlar[i + 1]
                
                dx = nokta2[0] - nokta1[0]
                dy = nokta2[1] - nokta1[1]
                dt = nokta2[2] - nokta1[2]
                
                if dt > 0:
                    toplamDx += dx
                    toplamDy += dy
                    toplamDt += dt
                    validSayac += 1
            
            if validSayac > 0 and toplamDt > 0:
                # Ortalama hız
                self.hizVektoruX = toplamDx / toplamDt
                self.hizVektoruY = toplamDy / toplamDt
                
                # Daha uzun tahmin süresi - gelecekteki konumu daha iyi tahmin et
                tahminZamani = 0.15  # 150ms ilerisini tahmin et
                tahminCarpani = 40   # Daha agresif tahmin
                
                self.tahminEdilenX = merkezX + (self.hizVektoruX * tahminZamani * tahminCarpani)
                self.tahminEdilenY = merkezY + (self.hizVektoruY * tahminZamani * tahminCarpani)
    
    def gecenSure(self):
        """Son görülmeden geçen süre"""
        return time.time() - self.sonGorulen
    
    def kalitePuani(self):
        """Bu balonun toplam kalite puanı"""
        zamanBonus = min(self.toplameHits * 2, 50)  # Uzun süre tracking bonusu
        stabiliteBinus = self.stabiliteSkoru
        guvenBonus = max(0, self.guvenSkoru - 50)
        kilitBonus = 100 if self.isLocked() else 0
        
        return zamanBonus + stabiliteBinus + guvenBonus + kilitBonus
    
    def isValid(self):
        """Daha esnek geçerlilik kontrolü"""
        if self.consecutiveMisses >= self.maxMisses:
            return False
        if self.guvenSkoru < 30:  # Çok düşük threshold
            return False
        if self.gecenSure() > 2.0:  # 2 saniye timeout
            return False
        return True

class UltraKararliUcBalonSistemi:
    """Ultra kararlı 3 balon sistemi - HEAD, 1. balon, 2. balon"""
    
    def __init__(self):
        self.headBalon = None
        self.birinciBalon = None
        self.ikinciBalon = None  # 2. balon eklendi
        self.sonKontrolZamani = time.time()
        self.kontrolAraligi = 5.0  # 5 saniyede bir büyük kontrol
        self.mesafeThreshold = 150  # Daha geniş arama alanı
        self.frame_count = 0
        
        # Kararlılık için ekstra değişkenler
        self.sonDeğişiklikZamani = time.time()
        self.minDeğişiklikAraligi = 2.0  # En az 2 saniye bekle
        self.beklemedekiYeniBalon = None
        self.beklemeSayaci = 0
        self.degisiklikThreshold = 20  # Daha dengeli threshold
    
    def IoUHesapla(self, box1, box2):
        """Hızlı IoU hesaplama"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        if x1_max <= x2_min or x2_max <= x1_min or y1_max <= y2_min or y2_max <= y1_min:
            return 0.0
        
        kesisimX1 = max(x1_min, x2_min)
        kesisimY1 = max(y1_min, y2_min)
        kesisimX2 = min(x1_max, x2_max)
        kesisimY2 = min(y1_max, y2_max)
        
        kesisimAlani = (kesisimX2 - kesisimX1) * (kesisimY2 - kesisimY1)
        alan1 = (x1_max - x1_min) * (y1_max - y1_min)
        alan2 = (x2_max - x2_min) * (y2_max - y2_min)
        birlesimAlani = alan1 + alan2 - kesisimAlani
        
        return kesisimAlani / birlesimAlani if birlesimAlani > 0 else 0.0
    
    def enIyiEslestirme(self, X1, X2, Y1, Y2, guvenSkoru):
        """Çok konservativ eşleştirme - 3 balon desteği"""
        yeniMerkezX, yeniMerkezY = (X1 + X2) // 2, (Y1 + Y2) // 2
        
        headSkor = 0
        birinciSkor = 0
        ikinciSkor = 0
        
        # HEAD balon kontrolü - çok geniş tolerans
        if self.headBalon and self.headBalon.isValid():
            headMerkezX, headMerkezY = self.headBalon.ortaNokta()
            headMesafe = math.sqrt((headMerkezX - yeniMerkezX) ** 2 + 
                                 (headMerkezY - yeniMerkezY) ** 2)
            
            if headMesafe < self.mesafeThreshold:
                iou = self.IoUHesapla((self.headBalon.X1, self.headBalon.Y1, 
                                     self.headBalon.X2, self.headBalon.Y2),
                                    (X1, Y1, X2, Y2))
                
                mesafeSkor = 1.0 - (headMesafe / self.mesafeThreshold)
                
                # Kilitli bonusu
                kilitBonus = 0.5 if self.headBalon.isLocked() else 0
                
                # Güçlendirilmiş tahmin skoru
                tahminSkor = 0
                if self.headBalon.tahminEdilenX and self.headBalon.tahminEdilenY:
                    tahminMesafe = math.sqrt((self.headBalon.tahminEdilenX - yeniMerkezX) ** 2 + 
                                           (self.headBalon.tahminEdilenY - yeniMerkezY) ** 2)
                    if tahminMesafe < self.mesafeThreshold:
                        # Tahmin mesafesi ne kadar yakınsa o kadar bonus
                        tahminNormalize = 1.0 - (tahminMesafe / self.mesafeThreshold)
                        tahminSkor = 0.6 * tahminNormalize  # Daha yüksek bonus
                
                headSkor = mesafeSkor * 0.3 + iou * 0.4 + kilitBonus + tahminSkor
        
        # 1. BALON kontrolü
        if self.birinciBalon and self.birinciBalon.isValid():
            birinciMerkezX, birinciMerkezY = self.birinciBalon.ortaNokta()
            birinciMesafe = math.sqrt((birinciMerkezX - yeniMerkezX) ** 2 + 
                                    (birinciMerkezY - yeniMerkezY) ** 2)
            
            if birinciMesafe < self.mesafeThreshold:
                iou = self.IoUHesapla((self.birinciBalon.X1, self.birinciBalon.Y1,
                                     self.birinciBalon.X2, self.birinciBalon.Y2),
                                    (X1, Y1, X2, Y2))
                
                mesafeSkor = 1.0 - (birinciMesafe / self.mesafeThreshold)
                kilitBonus = 0.5 if self.birinciBalon.isLocked() else 0
                
                tahminSkor = 0
                if self.birinciBalon.tahminEdilenX and self.birinciBalon.tahminEdilenY:
                    tahminMesafe = math.sqrt((self.birinciBalon.tahminEdilenX - yeniMerkezX) ** 2 + 
                                           (self.birinciBalon.tahminEdilenY - yeniMerkezY) ** 2)
                    if tahminMesafe < self.mesafeThreshold:
                        tahminNormalize = 1.0 - (tahminMesafe / self.mesafeThreshold)
                        tahminSkor = 0.6 * tahminNormalize
                
                birinciSkor = mesafeSkor * 0.3 + iou * 0.4 + kilitBonus + tahminSkor
        
        # 2. BALON kontrolü
        if self.ikinciBalon and self.ikinciBalon.isValid():
            ikinciMerkezX, ikinciMerkezY = self.ikinciBalon.ortaNokta()
            ikinciMesafe = math.sqrt((ikinciMerkezX - yeniMerkezX) ** 2 + 
                                    (ikinciMerkezY - yeniMerkezY) ** 2)
            
            if ikinciMesafe < self.mesafeThreshold:
                iou = self.IoUHesapla((self.ikinciBalon.X1, self.ikinciBalon.Y1,
                                     self.ikinciBalon.X2, self.ikinciBalon.Y2),
                                    (X1, Y1, X2, Y2))
                
                mesafeSkor = 1.0 - (ikinciMesafe / self.mesafeThreshold)
                kilitBonus = 0.5 if self.ikinciBalon.isLocked() else 0
                
                tahminSkor = 0
                if self.ikinciBalon.tahminEdilenX and self.ikinciBalon.tahminEdilenY:
                    tahminMesafe = math.sqrt((self.ikinciBalon.tahminEdilenX - yeniMerkezX) ** 2 + 
                                           (self.ikinciBalon.tahminEdilenY - yeniMerkezY) ** 2)
                    if tahminMesafe < self.mesafeThreshold:
                        tahminNormalize = 1.0 - (tahminMesafe / self.mesafeThreshold)
                        tahminSkor = 0.6 * tahminNormalize
                
                ikinciSkor = mesafeSkor * 0.3 + iou * 0.4 + kilitBonus + tahminSkor
        
        # Düşük threshold - kolay algılama (3 balon için)
        skorlar = [("HEAD", headSkor), ("BIRINCI", birinciSkor), ("IKINCI", ikinciSkor)]
        enIyi = max(skorlar, key=lambda x: x[1])
        
        if enIyi[1] > 0.2:
            return enIyi[0], enIyi[1]
        else:
            return None, 0
    
    def degisiklikYapilabilirMi(self):
        """Değişiklik yapılabilir mi kontrol et"""
        gecenSure = time.time() - self.sonDeğişiklikZamani
        return gecenSure >= self.minDeğişiklikAraligi
    
    def tumDetectionlariIsle(self, detectionlar):
        """Basitleştirilmiş ve fix edilmiş detection işleme - 3 balon desteği"""
        if len(detectionlar) == 0:
            # Hiç detection yok - missed frame
            if self.headBalon:
                self.headBalon.missedFrame()
            if self.birinciBalon:
                self.birinciBalon.missedFrame()
            if self.ikinciBalon:
                self.ikinciBalon.missedFrame()
            return
        
        # Güncellemeleri takip et
        headGuncellendi = False
        birinciGuncellendi = False
        ikinciGuncellendi = False
        kullanilmisDetectionlar = set()
        
        # Önce mevcut balonları güncellemeye çalış
        for i, tespit in enumerate(detectionlar):
            X1, Y1, X2, Y2, guvenSkoru, _ = tespit
            X1, Y1, X2, Y2 = int(X1), int(Y1), int(X2), int(Y2)
            
            if guvenSkoru * 100 < 40:  # Çok düşük güven skip
                continue
            
            # HEAD balon için kontrol
            if self.headBalon and self.headBalon.isValid() and not headGuncellendi:
                eslestirme, skor = self.enIyiEslestirme(X1, X2, Y1, Y2, guvenSkoru * 100)
                if eslestirme == "HEAD" and skor > 0.3:
                    self.headBalon.guncelle(X1, X2, Y1, Y2, guvenSkoru * 100)
                    headGuncellendi = True
                    kullanilmisDetectionlar.add(i)
                    continue
            
            # BIRINCI balon için kontrol
            if self.birinciBalon and self.birinciBalon.isValid() and not birinciGuncellendi and i not in kullanilmisDetectionlar:
                eslestirme, skor = self.enIyiEslestirme(X1, X2, Y1, Y2, guvenSkoru * 100)
                if eslestirme == "BIRINCI" and skor > 0.3:
                    self.birinciBalon.guncelle(X1, X2, Y1, Y2, guvenSkoru * 100)
                    birinciGuncellendi = True
                    kullanilmisDetectionlar.add(i)
                    continue
            
            # IKINCI balon için kontrol
            if self.ikinciBalon and self.ikinciBalon.isValid() and not ikinciGuncellendi and i not in kullanilmisDetectionlar:
                eslestirme, skor = self.enIyiEslestirme(X1, X2, Y1, Y2, guvenSkoru * 100)
                if eslestirme == "IKINCI" and skor > 0.3:
                    self.ikinciBalon.guncelle(X1, X2, Y1, Y2, guvenSkoru * 100)
                    ikinciGuncellendi = True
                    kullanilmisDetectionlar.add(i)
                    continue
        
        # Yeni balon ekleme - 3 balon için
        for i, tespit in enumerate(detectionlar):
            if i in kullanilmisDetectionlar:
                continue
                
            X1, Y1, X2, Y2, guvenSkoru, _ = tespit
            X1, Y1, X2, Y2 = int(X1), int(Y1), int(X2), int(Y2)
            
            if guvenSkoru * 100 < 40:  # Minimum güven
                continue
            
            yeniMerkez = ((X1 + X2) // 2, (Y1 + Y2) // 2)
            
            # HEAD yoksa veya geçersizse, direkt ekle
            if self.headBalon is None or not self.headBalon.isValid():
                self.headBalon = Balon(X1, X2, Y1, Y2, guvenSkoru * 100, "HEAD")
                self.sonDeğişiklikZamani = time.time()
                headGuncellendi = True
                kullanilmisDetectionlar.add(i)
                continue
            
            # BIRINCI yoksa veya geçersizse, HEAD'den farklıysa ekle
            if self.birinciBalon is None or not self.birinciBalon.isValid():
                # HEAD'den minimum mesafe kontrolü
                headMerkez = self.headBalon.ortaNokta()
                mesafe = math.sqrt((headMerkez[0] - yeniMerkez[0]) ** 2 + (headMerkez[1] - yeniMerkez[1]) ** 2)
                
                if mesafe > 30:  # Daha düşük mesafe threshold
                    self.birinciBalon = Balon(X1, X2, Y1, Y2, guvenSkoru * 100, "BIRINCI")
                    self.sonDeğişiklikZamani = time.time()
                    birinciGuncellendi = True
                    kullanilmisDetectionlar.add(i)
                    continue
            
            # IKINCI yoksa veya geçersizse, HEAD ve BIRINCI'den farklıysa ekle
            if self.ikinciBalon is None or not self.ikinciBalon.isValid():
                # HEAD ve BIRINCI'den minimum mesafe kontrolü
                headMerkez = self.headBalon.ortaNokta()
                mesafeHead = math.sqrt((headMerkez[0] - yeniMerkez[0]) ** 2 + (headMerkez[1] - yeniMerkez[1]) ** 2)
                
                mesafeBirinci = 999  # Varsayılan büyük değer
                if self.birinciBalon and self.birinciBalon.isValid():
                    birinciMerkez = self.birinciBalon.ortaNokta()
                    mesafeBirinci = math.sqrt((birinciMerkez[0] - yeniMerkez[0]) ** 2 + (birinciMerkez[1] - yeniMerkez[1]) ** 2)
                
                if mesafeHead > 30 and mesafeBirinci > 30:
                    self.ikinciBalon = Balon(X1, X2, Y1, Y2, guvenSkoru * 100, "IKINCI")
                    self.sonDeğişiklikZamani = time.time()
                    ikinciGuncellendi = True
                    kullanilmisDetectionlar.add(i)
                    continue
        
        # ÖZEL DURUM: HEAD yoksa terfi sistemi
        if self.headBalon is None and self.birinciBalon and self.birinciBalon.isValid():
            self.birinciBalon.tip = "HEAD"
            self.headBalon = self.birinciBalon
            self.birinciBalon = self.ikinciBalon  # 2. balon 1.'ye terfi
            self.ikinciBalon = None
            if self.birinciBalon:
                self.birinciBalon.tip = "BIRINCI"
            headGuncellendi = True
            print("BIRINCI BALON HEAD'e otomatik terfi etti!")
        
        # ÖZEL DURUM: BIRINCI yoksa IKINCI terfi etsin
        if self.birinciBalon is None and self.ikinciBalon and self.ikinciBalon.isValid():
            self.ikinciBalon.tip = "BIRINCI"
            self.birinciBalon = self.ikinciBalon
            self.ikinciBalon = None
            birinciGuncellendi = True
            print("IKINCI BALON BIRINCI'ye otomatik terfi etti!")
        
        # Güncellenmeyenlere missed frame
        if not headGuncellendi and self.headBalon:
            self.headBalon.missedFrame()
        if not birinciGuncellendi and self.birinciBalon:
            self.birinciBalon.missedFrame()
        if not ikinciGuncellendi and self.ikinciBalon:
            self.ikinciBalon.missedFrame()
        
        # HEAD'e en yakın balon 1. balon olsun
        self.mesafeKontrolVeYenidenSirala()
    
    def balonEkleveyaGuncelle(self, X1, X2, Y1, Y2, guvenSkoru):
        """Tekil detection işleme - KULLANILMIYOR ARTIK"""
        # Bu fonksiyon artık kullanılmıyor
        # Tüm detectionlar tumDetectionlariIsle() ile işleniyor
        pass
    
    def mesafeKontrolVeYenidenSirala(self):
        """HEAD'e en yakın balon 1. balon olacak şekilde sırala"""
        if not self.headBalon or not self.headBalon.isValid():
            return
        
        headMerkez = self.headBalon.ortaNokta()
        
        # Her iki balon da varsa mesafe kontrolü yap
        if (self.birinciBalon and self.birinciBalon.isValid() and 
            self.ikinciBalon and self.ikinciBalon.isValid()):
            
            birinciMerkez = self.birinciBalon.ortaNokta()
            ikinciMerkez = self.ikinciBalon.ortaNokta()
            
            mesafeBirinci = math.sqrt((headMerkez[0] - birinciMerkez[0]) ** 2 + 
                                     (headMerkez[1] - birinciMerkez[1]) ** 2)
            mesafeIkinci = math.sqrt((headMerkez[0] - ikinciMerkez[0]) ** 2 + 
                                    (headMerkez[1] - ikinciMerkez[1]) ** 2)
            
            # Eğer 2. balon HEAD'e daha yakınsa, yer değiştir
            if mesafeIkinci < mesafeBirinci:
                # Balonları yer değiştir
                self.birinciBalon.tip = "IKINCI"
                self.ikinciBalon.tip = "BIRINCI"
                self.birinciBalon, self.ikinciBalon = self.ikinciBalon, self.birinciBalon
                print(f"Balonlar yer değiştirdi! 1.balon HEAD'e daha yakın ({mesafeIkinci:.0f} < {mesafeBirinci:.0f})")
    
    def optimize_kontrol(self):
        """Her frame hızlı kontrol + Otomatik terfi sistemi - 3 balon"""
        # HEAD geçersizse 1.BALON'u HEAD yap
        if self.headBalon and not self.headBalon.isValid():
            if self.birinciBalon and self.birinciBalon.isValid():
                # 1.BALON'u HEAD'e terfi ettir
                self.birinciBalon.tip = "HEAD"
                self.headBalon = self.birinciBalon
                # 2.BALON'u 1.BALON'a terfi ettir
                if self.ikinciBalon and self.ikinciBalon.isValid():
                    self.ikinciBalon.tip = "BIRINCI"
                    self.birinciBalon = self.ikinciBalon
                    self.ikinciBalon = None
                else:
                    self.birinciBalon = None
                self.sonDeğişiklikZamani = time.time()
                print("1. BALON HEAD'e terfi etti!")
            else:
                self.headBalon = None
            
        # 1.BALON geçersizse 2.BALON'u terfi ettir
        if self.birinciBalon and not self.birinciBalon.isValid():
            if self.ikinciBalon and self.ikinciBalon.isValid():
                self.ikinciBalon.tip = "BIRINCI"
                self.birinciBalon = self.ikinciBalon
                self.ikinciBalon = None
                print("2. BALON 1. BALON'a terfi etti!")
            else:
                self.birinciBalon = None
        
        # 2.BALON geçersizse sadece sil
        if self.ikinciBalon and not self.ikinciBalon.isValid():
            self.ikinciBalon = None
        
        # HEAD'e en yakın balon 1. balon olsun
        self.mesafeKontrolVeYenidenSirala()
    
    def beslikliBalonKontrolu(self):
        """5 saniyede bir kontrol - ÇOK SINIRLI"""
        simdikiZaman = time.time()
        
        if simdikiZaman - self.sonKontrolZamani >= self.kontrolAraligi:
            # Sadece KİLİTLİ OLMAYAN balonlar için kontrol
            if (self.birinciBalon and self.headBalon and 
                not self.birinciBalon.isLocked() and 
                not self.headBalon.isLocked() and
                self.degisiklikYapilabilirMi()):
                
                # Kalite farkı ÇOK büyükse değiştir
                headKalite = self.headBalon.kalitePuani()
                birinciKalite = self.birinciBalon.kalitePuani()
                
                if birinciKalite > headKalite + 30:  # Büyük fark gerekli
                    # Yer değiştir
                    self.headBalon.tip = "BIRINCI"
                    self.birinciBalon.tip = "HEAD"
                    self.headBalon, self.birinciBalon = self.birinciBalon, self.headBalon
                    self.sonDeğişiklikZamani = time.time()
            
            self.sonKontrolZamani = simdikiZaman
    
    def aktifBalonSayisi(self):
        """Aktif balon sayısını döndür"""
        sayisi = 0
        if self.headBalon and self.headBalon.isValid(): sayisi += 1
        if self.birinciBalon and self.birinciBalon.isValid(): sayisi += 1
        if self.ikinciBalon and self.ikinciBalon.isValid(): sayisi += 1
        return sayisi

# Kamera kurulumu (canlı görüntü)
cap = cv2.VideoCapture(0)

genislik = int(cap.get(3))
yukseklik = int(cap.get(4))
kamera_fps = float(cap.get(5))
print(f"Kamera FPS: {kamera_fps:.2f}")

# Kamera optimizasyonu
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# Model ve sistem
model = YOLO("/Users/aliyilmaz/Desktop/HAVASAVUNMASİSTEMLERİ/best.pt") # Model Yolu
balonSistemi = UltraKararliUcBalonSistemi()

# FPS takibi
onceki_zaman = time.time()
frame_sayaci = 0

while True:
    kameraBasarili, img = cap.read()
    if not kameraBasarili:
        print("Kamera bulunamadı veya okunamadı")
        break

    simdiki_zaman = time.time()
    gecen_sure = simdiki_zaman - onceki_zaman
    fps = 1 / (gecen_sure + 1e-8)
    onceki_zaman = simdiki_zaman
    
    # Her frame detection yap - YENİ ÇAKIŞMA ÖNLEYİCİ SİSTEM
    frame_sayaci += 1
    sonuclar = model(img, verbose=False)[0]
    tespitler = np.array(sonuclar.boxes.data.tolist() if sonuclar.boxes is not None else [])

    # Tüm detectionları bir arada işle - çakışmayı önle
    balonSistemi.tumDetectionlariIsle(tespitler)
    
    # Her frame hızlı kontrol
    balonSistemi.optimize_kontrol()
    
    # Periyodik kontrol
    balonSistemi.beslikliBalonKontrolu()
    
    # HEAD balon çizimi
    if balonSistemi.headBalon and balonSistemi.headBalon.isValid():
        fx, fy = balonSistemi.headBalon.ortaNokta()
        dogruluk = balonSistemi.headBalon.guvenSkoru
        
        # HEAD için yeşil renk
        renk = (0, 255, 0)
        
        # Çizimler
        cv2.circle(img, (fx, fy), 100, renk, 2)
        cv2.circle(img, (fx, fy), 15, renk, -1)
        cv2.putText(img, "HEAD", (fx + 15, fy - 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        cv2.putText(img, str(f"{dogruluk:.1f}"), (fx, fy + 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        
        # Hız vektörü
        if balonSistemi.headBalon.hizVektoruX != 0 or balonSistemi.headBalon.hizVektoruY != 0:
            hizX = int(fx + balonSistemi.headBalon.hizVektoruX * 30)
            hizY = int(fy + balonSistemi.headBalon.hizVektoruY * 30)
            cv2.arrowedLine(img, (fx, fy), (hizX, hizY), (255, 255, 0), 2)
        
        # Tahmin edilen konum
        if balonSistemi.headBalon.tahminEdilenX and balonSistemi.headBalon.tahminEdilenY:
            tahminX = int(balonSistemi.headBalon.tahminEdilenX)
            tahminY = int(balonSistemi.headBalon.tahminEdilenY)
            cv2.circle(img, (tahminX, tahminY), 30, (255, 255, 255), 2)
        
        # Koordinat çizgileri
        cv2.line(img, (0, fy), (genislik, fy), (0, 0, 0), 1)
        cv2.line(img, (fx, yukseklik), (fx, 0), (0, 0, 0), 1)
        
        # Koordinat bilgisi
        konum = f"({fx}, {fy})"
        cv2.putText(img, konum, (fx + 15, fy - 15), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
    
    # 1. BALON çizimi
    if balonSistemi.birinciBalon and balonSistemi.birinciBalon.isValid():
        fx, fy = balonSistemi.birinciBalon.ortaNokta()
        dogruluk = balonSistemi.birinciBalon.guvenSkoru
        
        # 1. BALON için turuncu renk
        renk = (0, 165, 255)
        
        # Çizimler
        cv2.circle(img, (fx, fy), 100, renk, 2)
        cv2.circle(img, (fx, fy), 15, renk, -1)
        cv2.putText(img, "1. balon", (fx + 15, fy - 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        cv2.putText(img, str(f"{dogruluk:.1f}"), (fx, fy + 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        
        # Hız vektörü
        if balonSistemi.birinciBalon.hizVektoruX != 0 or balonSistemi.birinciBalon.hizVektoruY != 0:
            hizX = int(fx + balonSistemi.birinciBalon.hizVektoruX * 30)
            hizY = int(fy + balonSistemi.birinciBalon.hizVektoruY * 30)
            cv2.arrowedLine(img, (fx, fy), (hizX, hizY), (255, 255, 0), 2)
        
        # Tahmin edilen konum
        if balonSistemi.birinciBalon.tahminEdilenX and balonSistemi.birinciBalon.tahminEdilenY:
            tahminX = int(balonSistemi.birinciBalon.tahminEdilenX)
            tahminY = int(balonSistemi.birinciBalon.tahminEdilenY)
            cv2.circle(img, (tahminX, tahminY), 30, (255, 255, 255), 2)
    
    # 2. BALON çizimi
    if balonSistemi.ikinciBalon and balonSistemi.ikinciBalon.isValid():
        fx, fy = balonSistemi.ikinciBalon.ortaNokta()
        dogruluk = balonSistemi.ikinciBalon.guvenSkoru
        
        # 2. BALON için mor renk
        renk = (255, 0, 255)
        
        # Çizimler
        cv2.circle(img, (fx, fy), 100, renk, 2)
        cv2.circle(img, (fx, fy), 15, renk, -1)
        cv2.putText(img, "2. balon", (fx + 15, fy - 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        cv2.putText(img, str(f"{dogruluk:.1f}"), (fx, fy + 50), cv2.FONT_HERSHEY_PLAIN, 2, renk, 2)
        
        # Hız vektörü
        if balonSistemi.ikinciBalon.hizVektoruX != 0 or balonSistemi.ikinciBalon.hizVektoruY != 0:
            hizX = int(fx + balonSistemi.ikinciBalon.hizVektoruX * 30)
            hizY = int(fy + balonSistemi.ikinciBalon.hizVektoruY * 30)
            cv2.arrowedLine(img, (fx, fy), (hizX, hizY), (255, 255, 0), 2)
        
        # Tahmin edilen konum
        if balonSistemi.ikinciBalon.tahminEdilenX and balonSistemi.ikinciBalon.tahminEdilenY:
            tahminX = int(balonSistemi.ikinciBalon.tahminEdilenX)
            tahminY = int(balonSistemi.ikinciBalon.tahminEdilenY)
            cv2.circle(img, (tahminX, tahminY), 30, (255, 255, 255), 2)
    
    # Performance bilgileri
    cv2.putText(img,f"FPS: {fps:.1f}",(10,30),cv2.FONT_HERSHEY_SIMPLEX, 1,(0,255,0),2)
    cv2.putText(img,f"Dugum: {balonSistemi.aktifBalonSayisi()}",(10,60),cv2.FONT_HERSHEY_SIMPLEX, 1,(0,255,0),2)
    
    cv2.imshow("Canli Takip", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()