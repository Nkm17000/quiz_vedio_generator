# Quiz Video Generator

Generates vertical quiz videos with:
- 3-second countdown slides
- English + Hindi question/options on screen
- Indian-English natural neural question narration
- Question narration only (no options)
- Voice forced to finish within each 3-second question slide
- Background music, countdown tick and answer sound
- Optional Facebook upload

## Indian voice

Default female voice:
`en-IN-NeerjaNeural`

Male alternative:
`en-IN-PrabhatNeural`

Set `TTS_VOICE` in `.env` to switch.

## Run

```bash
pip install -r requirements.txt
python app.py
```

The TTS service needs internet access because it uses Edge TTS.

## Video flow

For every question:

1. 3-second countdown slide — question is spoken
2. 3-second countdown slide — question is spoken
3. 3-second countdown slide — question is spoken
4. Answer slide — no question narration

The narration contains only the English question. Options and Hindi text are never sent to TTS.
