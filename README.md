# 📄 PDF Studio

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow)

**PDF Studio** è un'applicazione desktop **offline e privacy-first** per manipolare i PDF: unisci, dividi, ruota, comprimi, proteggi, estrai dati e fai OCR — tutto in un'unica interfaccia, senza mai caricare i tuoi documenti su internet.

> 🛡️ **I tuoi PDF non lasciano mai il tuo computer.**

![Screenshot di PDF Studio](docs/screenshot.png)
<!-- Sostituisci con il percorso reale di uno screenshot dell'app -->

---

## ✨ Funzionalità

### 🔗 Unisci PDF
- Unisci più PDF in un unico file
- **Uniforma le dimensioni delle pagine** — scegli A4, Lettera (anche orizzontali) o lascia "Auto" per usare il formato del primo PDF. Le pagine vengono scalate e centrate senza deformazioni
- Aggiunge automaticamente un **segnalibro per ogni file** unito
- Riordina i file con drag & drop

### ✂️ Dividi e Ruota
- **Split** per range di pagine (`1-3, 5, 7-10`) o una pagina per file
- **Rotazione** con anteprima live: vedi subito come apparirà il PDF prima di salvare

### 🗜️ Comprimi e Proteggi
- **Compressione** con `pikepdf` per ridurre il peso dei file
- **Protezione** con password AES-256
- **Watermark** testuale diagonale personalizzabile

### 📊 Estrai Dati
- **Testo** pagina per pagina → `.txt`
- **Tabelle** → `.csv`
- **Immagini embedded** → PNG
- **Rasterizza** le pagine → PNG

### 🔍 OCR
- Riconoscimento testo su PDF scansionati tramite **Tesseract** (italiano + inglese)
- Genera un PDF con **layer di testo invisibile** → diventa ricercabile e copiabile

### 👁️ Anteprima Live
- Pannello anteprima integrato con navigazione pagine, zoom, adattamento larghezza/pagina e **rotazione in tempo reale**

---

## 🖥️ Installazione

### Requisiti
- **Python 3.11+**
- **Tesseract OCR** installato nel sistema (solo per la funzione OCR)

### Setup rapido

```bash
git clone https://github.com/TUO_USERNAME/pdf-studio.git
cd pdf-studio

# Virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# Dipendenze
pip install -r requirements.txt

# Avvia
python main.py
