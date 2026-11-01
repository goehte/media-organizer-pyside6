# Media Organizer (PySide6)

This project contains a desktop utility for organizing media files in a selected folder.

## What the script does

The script scans a target directory and automatically handles two common media cleanup tasks:

1. HEIC image conversion and organization
   - Finds `.heic` files recursively inside the selected directory.
   - Converts each image to JPEG (`.jpg`) using Pillow.
   - Saves the converted file next to the original file.
   - Moves the original `.heic` file into a `HEIC` subfolder as a backup/archive.
   - Skips conversion if a matching JPG already exists.

2. Video file organization
   - Finds `.mov` and `.mp4` files recursively.
   - Moves each video file into a `Video` subfolder in the same parent directory.
   - Prevents overwriting by automatically renaming duplicates (`_1`, `_2`, etc.).

The app is built with PySide6 and runs as a simple desktop window with:
- a directory selector
- a Start Processing button
- a live status log showing progress and errors

## Requirements

Install the dependencies:

```bash
pip install PySide6 pillow pillow-heif
```

## How to run

```bash
python media_organizer_pyside6.py
```

Then:
1. Click Browse
2. Select the directory to process
3. Click Start Processing
4. Watch the log for conversion and move actions

## Notes

- The script processes files recursively under the selected folder.
- It creates `HEIC` and `Video` folders only where needed.
- The app runs long-running file operations in a background thread so the GUI stays responsive.

## Example workflow

A folder containing:

```text
photos/
  IMG_0001.heic
  IMG_0002.heic
  IMG_0003.mov
  IMG_0004.mp4
```

will be processed into:

```text
photos/
  IMG_0001.jpg
  IMG_0002.jpg
  HEIC/
    IMG_0001.heic
    IMG_0002.heic
  Video/
    IMG_0003.mov
    IMG_0004.mp4
```

## License

MIT
