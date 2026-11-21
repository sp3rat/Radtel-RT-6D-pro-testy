# Instrukcja obsługi i aktualizacji Radtel RT-6D Pro (Debian 13)

## 1. Architektura sprzętowa radia
* **Główny mikrokontroler (MCU):** Artery **AT32F423RCT7 (150 MHz, 256 KB Flash, 48 KB SRAM)** (ARM Cortex-M4F).
* **Pamięć wewnętrzna Flash MCU:** 256 KB (`0x08000000 – 0x0803FFFF`).
  * `0x08000000 – 0x080027FF` (pierwsze 10 KB): fabryczny **bootloader** (chroniony, nie jest nadpisywany podczas aktualizacji).
  * `0x08002800 – 0x080398D3`: właściwy **firmware** aplikacji radia (maksymalny bufor: `251 904` bajty = `246` bloków po `1024` bajty).
* **Zewnętrzna pamięć SPI Flash:** **W25Q80** (1 MB) – przechowuje kanały, strefy, kontakty DMR, ustawienia użytkownika (codeplug) oraz czcionki. Aktualizacja głównego firmware'u nie kasuje jej zawartości.
* **Uwaga dotycząca układu DMR:** Radio posiada osobny procesor DMR. Poniższe narzędzia służą **wyłącznie** do aktualizacji głównego procesora (MCU), a nie wsadu układu DMR.

---

## 2. Opis naszych skryptów i plików

### `ekstraktor_fw.py`
* **Co robi:** Uruchamia w tle deasembler .NET (`monodis`), odnajduje w oficjalnym instalatorze Windows (`.exe` lub `.7zip`) zaszyty ciąg w formacie Intel HEX i konwertuje go na dwa czyste pliki: `.hex` oraz surowy obraz binarny `.bin`.
* **Wymagania:** Pakiet systemowy `mono-utils`.

### `flasher_rt6d.py`
* **Co robi:** Natywny program wgrywający firmware do radia po kablu USB-UART na Linuxie. Odtwarza protokół komunikacji z oficjalnego programu `Ido_Update.exe`:
  * **Parametry portu:** `115200 bps`, 8N1, wymuszenie linii `DTR = True`.
  * **Handshake:** Wysyła 3 razy ramkę `39 33 05 10 D3` i oczekuje potwierdzenia `0x06` (ACK).
  * **Inicjalizacja kasowania Flash:** Wysyła ramkę `39 33 05 55 18` i czeka na potwierdzenie `0x06`.
  * **Transfer danych:** Dopełnia plik `.bin` zerami (`0x00`) do rozmiaru `251 904` bajtów i wysyła `246` pakietów po `1028` bajtów każdy:
    * Bajt `0`: `0x57` (`'W'` – nagłówek ramki zapisu)
    * Bajty `1–2`: przesunięcie adresu (`offset` Big-Endian)
    * Bajty `3–1026`: `1024` bajty danych wsadu
    * Bajt `1027`: suma kontrolna `(suma_bajtów_0_do_1026 + 0x52) & 0xFF`
  * **Zakończenie:** Wysyła ramkę `39 33 05 EE B1`.

---

## 3. Procedura ręczna krok po kroku (dla nowych aktualizacji)

### Krok 1: Wypakowanie nowego firmware'u z pliku `.exe` / `.7zip`
1. Umieść pobrany plik aktualizacyjny w katalogu `/home/sp3rat/Dokumenty/Radio/RT-6D_PRO/`.
2. Uruchom ekstraktor:
   ```bash
   cd /home/sp3rat/Dokumenty/Radio/RT-6D_PRO/
   python3 ekstraktor_fw.py Nazwa_Nowego_Pliku.exe
   ```
   *(W wyniku powstaną pliki `Nazwa_Nowego_Pliku.bin` oraz `Nazwa_Nowego_Pliku.hex`).*

### Krok 2: Weryfikacja pliku `.bin` przed wgraniem (WAŻNE!)
Zanim wgrasz plik do radia, sprawdź jego rozmiar oraz czytelność tekstu (upewniasz się, że wsad nie jest zaszyfrowany i dotyczy głównego MCU):
```bash
ls -lh Nazwa_Nowego_Pliku.bin
strings -n 6 Nazwa_Nowego_Pliku.bin | grep -E "VER :|DATE:"
```
* **Prawidłowy wynik:** Rozmiar poniżej `251 904` bajtów (ok. 220–245 KB) oraz widoczna sygnatura wersji, np. `VER :RT-6D V2.10`.
* **Jeśli `strings` nic nie zwraca:** Nie wgrywaj pliku – oznacza to, że producent zmienił format lub zaszyfrował wsad.

### Krok 3: Porównanie zmian względem poprzedniej wersji (opcjonalnie)
Aby sprawdzić, jakie nowe funkcje lub poprawki menu wprowadził producent:
```bash
diff -u <(strings -n 6 "Dissassemble/Radtel_6D_Update V2.09_260609.bin") <(strings -n 6 Nazwa_Nowego_Pliku.bin)
```

### Krok 4: Wgranie nowego firmware'u do radia
1. Podłącz kabel programujący USB-C do komputera i sprawdź nazwę portu:
   ```bash
   ls /dev/ttyUSB*
   ```
   *(Zazwyczaj jest to `/dev/ttyUSB0`).*
2. Wyłącz radiotelefon.
3. Wprowadź radio w **tryb aktualizacji** (przytrzymaj odpowiedni przycisk boczny / PTT podczas włączania radia).
4. Uruchom flasher:
   ```bash
   python3 flasher_rt6d.py /dev/ttyUSB0 Nazwa_Nowego_Pliku.bin
   ```
5. Poczekaj, aż pasek postępu dojdzie do `246/246 (100%)` i radio uruchomi się ponownie.
