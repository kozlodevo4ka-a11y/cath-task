# Cath-task

A small desktop task manager built with PyQt6:

- to-do list with tags and importance colours
- Pomodoro timer (5 / 10 / 15 / 25 min, 1 hour)
- calendar view that highlights days with tasks
- a vamp mascot that is happy when you have completed tasks
- a compact, always-on-top window mode

Tasks are stored as JSON next to the script: `tasks.json` n
`completed_tasks.json`.

# Run from source

```bash
pip install PyQt6
python Main.py
```

Keep the image and sound files in the same folder as `Main.py`^^

# Build a standalone .exe (4 windows)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed ^
  --add-data "happy_cat.png;." --add-data "sad_cat.png;." ^
  --add-data "happy_blink.png;." --add-data "sad_blink.png;." ^
  --add-data "sound.mp3;." ^
  Main.py
```
