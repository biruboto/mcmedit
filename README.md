```
 __   __  _______  __   __  _______  ______   ___   _______ 
|  |_|  ||       ||  |_|  ||       ||      | |   | |       |
|       ||       ||       ||    ___||  _    ||   | |_     _|
|       ||       ||       ||   |___ | | |   ||   |   |   |  
|       ||      _||       ||    ___|| |_|   ||   |   |   |  
| ||_|| ||     |_ | ||_|| ||   |___ |       ||   |   |   |  
|_|   |_||_______||_|   |_||_______||______| |___|   |___|  
```
A small command-line tool for converting MAX7456/AT7456E OSD font (.mcm) files to and from .png for use in analog FPV systems (Betaflight). The tool can also inject a pre-made 288x72 boot logo file.

The .mcm format contains a 16x16 grid of 12x18 glyphs for displaying characters over analog video. This tool converts the .mcm into a 192x288 .png for modification in image editing software. 
Graphics must contain pixels that are either pure black #000000, pure white #FFFFFF, and a transparency color of either gray #808080, or green #18FF00.
You can then convert your modified .png back into an .mcm to upload to your quad.

## Usage

```bash
mcmedit.py mcm2sheet font.mcm sheet.png
mcmedit.py sheet2mcm sheet.png font.mcm
mcmedit.py inject-logo font.mcm logo_288x72.png out.mcm
```