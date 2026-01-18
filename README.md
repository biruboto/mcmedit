```
 __   __  _______  __   __  _______  ______   ___   _______ 
|  |_|  ||       ||  |_|  ||       ||      | |   | |       |
|       ||       ||       ||    ___||  _    ||   | |_     _|
|       ||       ||       ||   |___ | | |   ||   |   |   |  
|       ||      _||       ||    ___|| |_|   ||   |   |   |  
| ||_|| ||     |_ | ||_|| ||   |___ |       ||   |   |   |  
|_|   |_||_______||_|   |_||_______||______| |___|   |___|  
```
A small command-line tool for editing MAX7456 / AT7456E OSD font (.mcm) files for use in analog FPV systems (Betaflight).

## Usage

```bash
mcmedit.py mcm2sheet font.mcm sheet.png
mcmedit.py sheet2mcm sheet.png font.mcm
mcmedit.py inject-logo font.mcm logo_288x72.png out.mcm
