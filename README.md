# Bank Format YAML Builder (FR/EN) – by F3F364fr & GPT5

⚠️ **Note**: I may not continue updating this tool, which is why I’m also sharing the source.  
⚠️ **Remarque** : Je risque de ne pas continuer à le mettre à jour, c’est pour cela que je partage la source.

---

## 📖 Overview

**Bank Format YAML Builder** is a portable Windows utility to manage a YAML “serial bank” with ease.

- Paste raw serials or YAML blocks  
- Organize them by category  
- Add comments  
- Clean duplicates with smart deduplication  
- Export or merge into your `bank.yaml`  

Supports **FR/EN**, Light/Dark theme, and optional auto-decryption via [Awzam – Borderlands 4 Gear n Gun Editor](https://www.nexusmods.com/).

---

## ✨ Features

- **Paste & Import:** serials (`@U…`) or YAML blocks (`slot_X:` + `serial:`); `.txt` import supported.
- **Display & Sorting:** sortable list, category filters, search by substring.
- **Comments:** quick edit, right-click/Ctrl+C copy, shows selected item’s comment.
- **Smart Deduplication:** keeps the one with a comment (or the first if both have comments).
- **Export & Merge:**  
  - Export → save current **view** to YAML (custom indentation).  
  - Merge → merge full **bank** into `bank.yaml` (next to exe).  
- **Custom Indentation:** adjust indentation for `slot_X:` and sub-lines (`serial`, `state_flags`).  
- **Other:** serial counter in title, FR/EN toggle, Light/Dark theme (ttkbootstrap).  
- **Optional:** auto-decrypt using `main.py` from Awzam’s Borderlands 4 Gear n Gun Editor.

---

## 📌 Example

**Input (paste area):**
```text
@Ugr$)Nm/)}}!sIWYM^$QlbwG_;UrPW
@Ugr$)Nm/)}}!qj=7L{(~iG&=-}*pW;C

slot_7:
  serial: '@Ugr$)Nm/)}}!abcd123456789'
  state_flags: 1
slot_8:
  serial: '@Ugr$)Nm/)}}!efgh987654321'
  state_flags: 33
```
Exported YAML:


yaml 
```text
slot_0:
  serial: '@Ugr$)Nm/)}}!sIWYM^$QlbwG_;UrPW'
  state_flags: 1
slot_1:
  serial: '@Ugr$)Nm/)}}!qj=7L{(~iG&=-}*pW;C'
  state_flags: 1
slot_2:
  serial: '@Ugr$)Nm/)}}!abcd123456789'
  state_flags: 1
slot_3:
  serial: '@Ugr$)Nm/)}}!efgh987654321'
  state_flags: 1
With comments:
```
yaml
```text
slot_0:
  serial: '@Ugr$)Nm/)}}!sIWYM^$QlbwG_;UrPW' # Legendary SMG
  state_flags: 1
slot_1:
  serial: '@Ugr$)Nm/)}}!qj=7L{(~iG&=-}*pW;C' # Shield (rare)
  state_flags: 1
slot_2:
  serial: '@Ugr$)Nm/)}}!abcd123456789' # Pistol
  state_flags: 1
slot_3:
  serial: '@Ugr$)Nm/)}}!efgh987654321' # Artifact
  state_flags: 1
```
du contenu ici

⚙️ Installation
Portable (Windows users)
Download the ZIP release.

Extract it anywhere.

Run bank_builder.exe.

✅ No Python required.

From source
Install Python 3.10 – 3.12.

Install dependencies:

bash
Copier le code
pip install ttkbootstrap
(Optional) For exe build or auto-decrypt:

bash
Copier le code
pip install pyinstaller
Run the app:

bash
Copier le code
python bank_builder.pyw
🔧 Build EXE (PyInstaller)
Windows:

```text
python -m PyInstaller --noconsole --onefile --add-data "main.py;." --add-data "fr.json;." --add-data "en.json;." bank_builder.pyw
```
Linux/macOS (replace ; with :):

```text
python -m PyInstaller --noconsole --onefile --add-data "main.py:." --add-data "fr.json:." --add-data "en.json:." bank_builder.pyw
```
The exe will be in dist/bank_builder.exe.

🖥️ Compatibility
Windows 10/11 (64-bit) for the exe build.

Python 3.10–3.12 for source runs.

Portable app, no extra prerequisites.

❓ FAQ
Does it modify bank.yaml automatically?
No. Export creates a separate file; Merge updates bank.yaml.

Where is bank.yaml stored?
Next to the executable.

Internet required?
No. Everything is local.

SmartScreen/Antivirus warning?
Possible with PyInstaller binaries. Add the folder to exclusions and run anyway.

🐞 Known Issues
Poorly formatted YAML may be skipped.

Auto-decoded categories depend on main.py.

🙏 Credits
Utility code: F3F364fr

Assistance & tooling: GPT-5

Optional decryption: Awzam – Borderlands 4 Gear n Gun Editor

License: Non-commercial use for modding/tooling
