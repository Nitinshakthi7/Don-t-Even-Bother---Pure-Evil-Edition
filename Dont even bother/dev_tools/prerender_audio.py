# dev_tools/prerender_audio.py - bake every sound to a file, once.
#
#   python dev_tools/prerender_audio.py
#
# The game synthesises all of its audio with numpy at startup. That is fine
# natively, but it made the browser build fetch an 11MB numpy wheel before it
# could even start, then spend another second and a half doing the maths -
# which on a phone is most of the wait.
#
# So we do the maths here, where numpy already exists, and ship the results.
# Written as 22kHz mono OGG: pygbag will not package WAV, and Vorbis is a
# fraction of the size for sounds you cannot tell apart on a phone speaker.
# Needs soundfile installed (a build-time tool only, not a game dependency).

import audioop
import os
import sys
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame                                     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sounds")
RATE = 22050


def write(path, sound, src_rate=44100):
    """One pygame Sound -> one 22kHz mono OGG.

    pygbag refuses to package WAV and asks for OGG, which is just as well:
    Vorbis is about a sixth of the size, and size is the whole point here.
    """
    import numpy as np
    import soundfile as sf

    raw = sound.get_raw()
    mono = audioop.tomono(raw, 2, 0.5, 0.5)
    small, _ = audioop.ratecv(mono, 2, 1, src_rate, RATE, None)
    samples = np.frombuffer(small, dtype="<i2").astype("float32") / 32768.0
    # Written in blocks on purpose. Handing libsndfile a whole track in one
    # sf.write() call crashes the process outright - no exception, just a dead
    # interpreter - which silently truncated every music track to a 3KB stub.
    with sf.SoundFile(path, "w", samplerate=RATE, channels=1,
                      format="OGG", subtype="VORBIS") as fh:
        for i in range(0, len(samples), 32768):
            fh.write(samples[i:i + 32768])
    return os.path.getsize(path)


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    if pygame.mixer.get_init() is None:
        raise SystemExit("no mixer - cannot render the sounds")

    import audio
    if audio.np is None:
        raise SystemExit("numpy is needed to render the sounds (this runs on your machine, not the web)")

    audio.np.random.seed(7)                      # same noise every build
    sfx = audio._build_sfx()
    music = {name: audio._to_sound(data, 0.8) for name, data in audio._build_music().items()}

    total = 0
    for kind, table in (("sfx", sfx), ("music", music)):
        folder = os.path.join(OUT, kind)
        os.makedirs(folder, exist_ok=True)
        for name, sound in sorted(table.items()):
            total += write(os.path.join(folder, f"{name}.ogg"), sound)
        print(f"  {kind:<6} {len(table):>3} files")
    print(f"wrote {OUT}")
    print(f"  {total / 1024:.0f} KB at {RATE}Hz mono OGG")


if __name__ == "__main__":
    main()
