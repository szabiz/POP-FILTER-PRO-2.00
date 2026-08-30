# Pop Filter Pro

An intelligent, memory-efficient pop-noise (microphone "plosive") removal
engine and GUI for WAV audio files. Features a custom native Canvas-based
waveform engine and a Cubic Spline curve editor.

Copyright © 2026 szabiz — *Soli Deo Gloria*

![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## Project Structure

```text
PopFilterPro/
├── app.py                  # GUI application code (GPLv3)
├── cli.py                  # CLI interface code (GPLv3)
├── pop_core.py             # Core filter engine (GPLv3)
├── icon.ico                # Application icon
├── LICENSE                 # Main project license: GNU General Public License v3.0
├── LICENSE-THIRD-PARTY.txt # Third-party dependency legal notices
└── README.md               # Project description and usage guide
```

## Running from Source

### Requirements
- Python 3.13+
- The following packages:

```bash
pip install numpy scipy sounddevice
```

*(`tkinter` usually ships with most Windows/macOS Python installations by
default; on Linux you may need to install it separately, e.g.
`sudo apt install python3-tk`)*

### Launch

```bash
python app.py
```

## Building Your Own .exe (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --name app --windowed --onedir app.py
```

The resulting build is created in the `dist/app/` folder (`app.exe` +
the `_internal/` folder). These two must always be distributed together.

## Key Features

- Band-limited, threshold-sensitive pop detection (adjustable frequency
  band and dB threshold)
- Chunked processing — no freezing or crashing even on long (30+ minute)
  files, low RAM footprint
- Real-time original / filtered preview, "Delta mode" (listen to only the
  removed noise)
- Custom region selection with Cubic Spline curve fine-tuning
- Audacity-compatible label export
- Save/load presets

## License

This project is licensed under the **GNU General Public License v3.0
(GPLv3)** — see the [`LICENSE`](LICENSE) file.

This means you are free to use, modify, and distribute it (including for
commercial purposes), **but** any distributed modified version must also
remain open source, released under GPLv3.

The third-party libraries bundled into the compiled `.exe` (NumPy, SciPy,
sounddevice/PortAudio, Tcl/Tk, etc.) are listed with their licenses in
[`THIRD-PARTY-LICENSES.txt`](THIRD-PARTY-LICENSES.txt). All of them are
permissive (BSD/MIT/PSF) licenses, compatible with GPLv3.

## Contributing

Pull requests and issues are welcome. Since the project is licensed under
GPLv3, any contributed changes will also fall under the same license.

## Acknowledgments

Thanks to the NumPy, SciPy, and sounddevice development teams, as well as
the researchers behind HPSS (Harmonic-Percussive Source Separation) and
Wiener filtering, without whom this software could not have been created.
