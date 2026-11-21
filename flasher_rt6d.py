#!/usr/bin/env python3
import sys
import time
import serial

# Pakiety sterujące odczytane bezpośrednio z Ido_Update.exe
SEND_CONNECT = bytes([0x39, 0x33, 0x05, 0x10, 0xD3])
SEND_UPDATE  = bytes([0x39, 0x33, 0x05, 0x55, 0x18])
SEND_END     = bytes([0x39, 0x33, 0x05, 0xEE, 0xB1])

TOTAL_SIZE   = 251904  # 246 bloków * 1024 bajty
BLOCK_SIZE   = 1024
NUM_BLOCKS   = TOTAL_SIZE // BLOCK_SIZE

def calc_checksum(packet_1027):
    return (sum(packet_1027) + 0x52) & 0xFF

def flash_radio(port_name, bin_path):
    with open(bin_path, "rb") as f:
        fw_data = f.read()

    if len(fw_data) > TOTAL_SIZE:
        print(f"Błąd: Plik .bin jest za duży ({len(fw_data)} B > {TOTAL_SIZE} B)!")
        sys.exit(1)

    # Dopełniamy bufor zerami (0x00) dokładnie tak samo jak UpDate_Load w C#
    padded_fw = fw_data.ljust(TOTAL_SIZE, b"\x00")

    print(f"[*] Otwieranie portu {port_name} (115200 bps, DTR=True)...")
    ser = serial.Serial(
        port=port_name,
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=5.0
    )
    ser.dtr = True
    time.sleep(0.1)
    ser.reset_input_buffer()

    try:
        # 1. Handshake (3x Send_Connect + oczekiwanie na 0x06)
        print("[*] Nawiązywanie połączenia z bootloaderem radia...")
        for attempt in range(1, 4):
            ser.write(SEND_CONNECT)
            time.sleep(0.05)
            ack = ser.read(1)
            if ack != b"\x06":
                print(f"[-] Brak potwierdzenia ACK (0x06) w kroku {attempt}/3. Odebrano: {ack}")
                print("    Upewnij się, że radio jest włączone w trybie aktualizacji (z wciśniętym PTT).")
                return
        print("[+] Połączono z bootloaderem!")

        # 2. Komenda rozpoczęcia zapisu (Send_Update)
        ser.write(SEND_UPDATE)
        time.sleep(0.5)
        ack = ser.read(1)
        if ack != b"\x06":
            print(f"[-] Błąd inicjalizacji zapisu (odebrano: {ack}).")
            return

        # 3. Wysyłanie 246 bloków po 1028 bajtów
        print(f"[*] Rozpoczynam wgrywanie {NUM_BLOCKS} bloków ({len(fw_data)} B właściwego kodu)...")
        for block_idx in range(NUM_BLOCKS):
            offset = block_idx * BLOCK_SIZE
            chunk = padded_fw[offset : offset + BLOCK_SIZE]

            # Nagłówek 3 bajty: [0x00, offset_hi, offset_lo]
            header = bytes([0x57, (offset >> 8) & 0xFF, offset & 0xFF])
            payload = header + chunk
            csum = bytes([calc_checksum(payload)])
            packet = payload + csum  # Razem 1028 bajtów

            ser.write(packet)
            time.sleep(0.05)

            ack = ser.read(1)
            if ack == b"\x06":
                print(f"\r[+] Postęp: {block_idx + 1:03d}/{NUM_BLOCKS} ({int((block_idx+1)*100/NUM_BLOCKS)}%)", end="", flush=True)
            else:
                print(f"\n[-] Błąd komunikacji przy bloku {block_idx + 1} (odebrano: {ack})! Przerywam.")
                return

        # 4. Zakończenie aktualizacji (Send_End)
        print("\n[*] Wysyłanie komendy zakończenia (Send_End)...")
        ser.write(SEND_END)
        time.sleep(0.1)
        print("[+] Aktualizacja zakończona sukcesem! Radio powinno się zrestartować.")

    finally:
        ser.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Użycie: python3 flasher_rt6d.py <port_szeregowy> <plik_firmware.bin>")
        print("Przykład: python3 flasher_rt6d.py /dev/ttyUSB0 'Dissassemble/Radtel_6D_Update V2.09_260609.bin'")
        sys.exit(1)
    flash_radio(sys.argv[1], sys.argv[2])
