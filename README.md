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
 # FAQ

# Where is my data actually stored? 
In tasks.json and completed_tasks.json, sitting next to Main.py (or next to the .exe, if you built one)

# How do I back up or move my tasks to another computer? 
Copy tasks.json and completed_tasks.json over to the new machine, into the same folder as the app. That's the whole migration.

# Do completed tasks pile up forever in completed_tasks.json? 
Nope, its cleared out automatically once a day. If you want to keep a record of what you've finished (for tracking or stats), copy completed_tasks.json elsewhere before it gets wiped.

