# Radtel RT-6D Pro Firmware Extraction & Flashing Guide (Debian 13)

## 1. Radio Hardware Architecture
* **Main Microcontroller (MCU):** Artery **AT32F423RCT7 (150 MHz, 256 KB Flash, 48 KB SRAM)** (ARM Cortex-M4F).
* **Internal MCU Flash Memory:** 256 KB (`0x08000000 – 0x0803FFFF`).
  * `0x08000000 – 0x080027FF` (first 10 KB): Factory **bootloader** (protected; never overwritten during standard updates).
  * `0x08002800 – 0x080398D3`: Main radio application **firmware** (maximum padded buffer: `251,904` bytes = `246` blocks of `1,024` bytes).
* **External SPI Flash Memory:** **W25Q80** (1 MB) – stores channels, zones, DMR contacts, user settings (codeplug), and fonts. Flashing the main MCU firmware does not erase this chip.
* **DMR Chip Note:** This transceiver uses a separate secondary processor for DMR. The tools below are strictly for the **main MCU firmware** and must **not** be used to flash DMR baseband updates.

---

## 2. Scripts & Tools Overview

### `ekstraktor_fw.py`
* **Purpose:** Runs the .NET disassembler (`monodis`) in the background, locates the embedded Intel HEX string inside the official Windows updater (`Ido_Update.exe` / `.7zip`), and converts it into clean `.hex` and raw `.bin` files.
* **Dependencies:** `mono-utils` package (`sudo apt install mono-utils`).

### `flasher_rt6d.py`
* **Purpose:** Native Linux CLI firmware flasher over USB-UART. Replicates the exact serial protocol of the official `Ido_Update.exe` utility:
  * **Serial Port Settings:** `115200 bps`, 8N1, with `DTR = True`.
  * **Handshake:** Sends `39 33 05 10 D3` three times, expecting a `0x06` (ACK) byte after each packet.
  * **Flash Erase Initialization:** Sends `39 33 05 55 18` and waits for `0x06` (ACK) once the MCU finishes erasing flash pages.
  * **Data Transfer:** Pads the `.bin` file with `0x00` bytes up to `251,904` bytes and transmits `246` frames of `1,028` bytes each:
    * Byte `0`: `0x57` (`'W'` – Write frame header)
    * Bytes `1–2`: Address offset (Big-Endian)
    * Bytes `3–1026`: `1,024` bytes of firmware payload
    * Byte `1027`: Checksum calculated as `(sum(bytes_0_to_1026) + 0x52) & 0xFF`
  * **Finalization:** Sends `39 33 05 EE B1` to reboot the radio.

---

## 3. Manual Step-by-Step Procedure (For Future Updates)

### Step 1: Extract Clean Firmware from `.exe` / `.7zip`
1. Place the downloaded update file into `/home/sp3rat/Dokumenty/Radio/RT-6D_PRO/`.
2. Run the extractor script:
   ```bash
   cd /home/sp3rat/Dokumenty/Radio/RT-6D_PRO/
   python3 ekstraktor_fw.py New_Update_File.exe
   ```
   *(This outputs `New_Update_File.bin` and `New_Update_File.hex`).*

### Step 2: Verify the `.bin` File Before Flashing (CRITICAL!)
Before writing anything to the radio, check the file size and readable strings to ensure it is unencrypted and intended for the main MCU:
```bash
ls -lh New_Update_File.bin
strings -n 6 New_Update_File.bin | grep -E "VER :|DATE:"
```
* **Expected Result:** File size under `251,904` bytes (~220–245 KB) and a clear version tag such as `VER :RT-6D V2.10`.
* **If `strings` outputs nothing:** Do **not** flash the file—the manufacturer may have encrypted the payload or changed the format.

### Step 3: Compare Changes Against the Previous Version (Optional)
To inspect new menu items, features, or bug fixes introduced in the new release:
```bash
diff -u <(strings -n 6 "Dissassemble/Radtel_6D_Update V2.09_260609.bin") <(strings -n 6 New_Update_File.bin)
```

### Step 4: Flash the New Firmware to the Radio
1. Plug the USB-C programming cable into your PC and check the assigned serial device:
   ```bash
   ls /dev/ttyUSB*
   ```
   *(Usually `/dev/ttyUSB0`).*
2. Turn off the transceiver.
3. Put the radio into **firmware update mode** (hold the PTT / designated side key while powering on the radio).
4. Run the flasher script:
   ```bash
   python3 flasher_rt6d.py /dev/ttyUSB0 New_Update_File.bin
   ```
5. Wait until the progress bar reaches `246/246 (100%)` and the radio reboots automatically.
