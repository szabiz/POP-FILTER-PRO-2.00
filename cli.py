# Copyright (C) 2026 szabiz - Soli Deo Gloria
#
# Pop Filter Pro Application
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Parancssoros pop-szűrő (GUI nélkül) - ugyanaz a motor, mint az app.py-ban.
Hasznos, ha sok fájlt kell automatikusan (script-ből) feldolgozni.

Használat:
    python cli.py bemenet.wav kimenet.wav
    python cli.py bemenet.wav kimenet.wav --low_f 60 --high_f 150 --threshold_db 8 --max_reduction_db 24
"""
import argparse
import sys

from pop_core import AudioFile, PopParams, build_cache, detect_all_from_cache, render_all_from_cache, save_wav


def main():
    p = argparse.ArgumentParser(description="Célzott, dinamikus pop-zaj eltávolító.")
    p.add_argument("input", help="bemeneti WAV fájl")
    p.add_argument("output", help="kimeneti (tisztított) WAV fájl")
    p.add_argument("--low_f", type=float, default=37.0, help="alsó frekvenciahatár (Hz), alapértelmezett: 37")
    p.add_argument("--high_f", type=float, default=172.0, help="felső frekvenciahatár (Hz), alapértelmezett: 172")
    p.add_argument("--threshold_db", type=float, default=13.0, help="detektálási küszöb (dB), alapértelmezett: 13")
    p.add_argument("--max_reduction_db", type=float, default=26.0, help="max. csillapítás (dB), alapértelmezett: 26")
    p.add_argument("--attack_ms", type=float, default=2.0)
    p.add_argument("--release_ms", type=float, default=45.0)
    p.add_argument("--max_pop_duration_ms", type=float, default=180.0,
                    help="ennél hosszabb 'pop'-nak tűnő szakaszt kihagyjuk (valószínűleg nem is pop)")
    p.add_argument("--quiet", action="store_true", help="ne írjon folyamatjelzést a konzolra")
    args = p.parse_args()

    def cb(pct, msg):
        if not args.quiet:
            print(f"\r[{pct:3d}%] {msg}", end="", flush=True)

    print(f"Fájl betöltése: {args.input}")
    try:
        audio = AudioFile(args.input, progress_callback=cb)
    except FileNotFoundError:
        print(f"\nHiba: a bemeneti fájl nem található: {args.input}", file=sys.stderr)
        sys.exit(1)

    params = PopParams(
        low_f=args.low_f, high_f=args.high_f,
        threshold_db=args.threshold_db, max_reduction_db=args.max_reduction_db,
        attack_ms=args.attack_ms, release_ms=args.release_ms,
        max_pop_duration_ms=args.max_pop_duration_ms,
    )

    cache = build_cache(audio, progress_callback=cb)
    if not args.quiet:
        print()

    _, segs = detect_all_from_cache(cache, params)
    print(f"{len(segs)} pop-szakasz észlelve:")
    for s, e, peak in segs:
        print(f"  {s:.3f}s - {e:.3f}s  (csúcs csillapítás: {peak:.1f} dB)")

    print("Szűrt hang előállítása...")
    out = render_all_from_cache(audio, cache, params, progress_callback=cb)
    if not args.quiet:
        print()

    save_wav(audio, out, args.output)
    print(f"Mentve: {args.output}")


if __name__ == "__main__":
    main()
