#!/usr/bin/env python3
import sys
import os
import re
import subprocess

def extract_firmware(exe_path):
    if not os.path.isfile(exe_path):
        print(f"Błąd: Nie znaleziono pliku '{exe_path}'")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(exe_path))[0]
    print(f"[*] Analizuję plik: {exe_path}")

    # Uruchamiamy monodis w pamięci (bez tworzenia śmieciowych plików pośrednich)
    try:
        res = subprocess.run(
            ["monodis", exe_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=True
        )
    except FileNotFoundError:
        print("Błąd: Brak narzędzia 'monodis'. Zainstaluj je: sudo apt install mono-utils")
        sys.exit(1)

    # Szukamy ciągu Intel HEX w zdeasemblowanym kodzie IL
    raw_hex = None
    for line in res.stdout.splitlines():
        if ":020000040800" in line:
            match = re.search(r'ldstr\s+"([^"]+)"', line)
            if match:
                raw_hex = match.group(1)
                break

    if not raw_hex:
        print("[-] Nie znaleziono osadzonego firmware'u w formacie Intel HEX w tym pliku.")
        sys.exit(1)

    # Zapis do pliku .hex
    records = [":" + r for r in raw_hex.split(":") if r]
    hex_out_path = f"{base_name}.hex"
    with open(hex_out_path, "w", encoding="utf-8") as hex_file:
        hex_file.write("\n".join(records) + "\n")

    # Konwersja Intel HEX -> surowy obraz binarny (.bin)
    mem = {}
    base_addr = 0
    for rec in records:
        length = int(rec[1:3], 16)
        addr = int(rec[3:7], 16)
        rec_type = int(rec[7:9], 16)
        data = bytes.fromhex(rec[9:9 + length * 2])

        if rec_type == 0x00:
            for i, b in enumerate(data):
                mem[base_addr + addr + i] = b
        elif rec_type == 0x04:
            base_addr = int.from_bytes(data, "big") << 16

    min_addr = min(mem.keys())
    max_addr = max(mem.keys())
    bin_data = bytes([mem.get(a, 0xFF) for a in range(min_addr, max_addr + 1)])

    bin_out_path = f"{base_name}.bin"
    with open(bin_out_path, "wb") as bin_file:
        bin_file.write(bin_data)

    print(f"[+] Sukces! Wyodrębniono firmware:")
    print(f"    -> Plik HEX : {hex_out_path} ({len(records)} rekordów)")
    print(f"    -> Plik BIN : {bin_out_path} ({len(bin_data)} bajtów)")
    print(f"    -> Adresy   : {hex(min_addr)} - {hex(max_addr)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python3 ekstraktor_fw.py <plik_aktualizacji.exe_lub_7zip>")
        sys.exit(1)
    extract_firmware(sys.argv[1])
