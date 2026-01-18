```
 __   __  _______  __   __  _______  ______   ___   _______ 
|  |_|  ||       ||  |_|  ||       ||      | |   | |       |
|       ||       ||       ||    ___||  _    ||   | |_     _|
|       ||       ||       ||   |___ | | |   ||   |   |   |  
|       ||      _||       ||    ___|| |_|   ||   |   |   |  
| ||_|| ||     |_ | ||_|| ||   |___ |       ||   |   |   |  
|_|   |_||_______||_|   |_||_______||______| |___|   |___|  
```
A small command-line tool for converting MAX7456/AT7456E OSD font (.mcm) files to and from PNG for use in analog FPV systems (Betaflight). The tool can also inject a pre-made 288x72 boot logo file.

## Usage

```bash
mcmedit.py mcm2sheet font.mcm sheet.png
mcmedit.py sheet2mcm sheet.png font.mcm
mcmedit.py inject-logo font.mcm logo_288x72.png out.mcm
```

Graphics must contain pixels that are either pure black #000000, pure white #FFFFFF, and a transparency color of either gray #808080, or green #18FF00.