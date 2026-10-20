# 🕌 Islamic Prayer Tracker & Daily Worship Assistant

A Streamlit web app that helps Muslims track the five daily prayers, build a consistent Salah habit, review progress with charts, record missed prayers privately, and ask an AI assistant (Google Gemini Flash) about Salah.

## Features

| Feature | What it does |
|---|---|
| Five-prayer tracker | Mark Fajr, Dhuhr, Asr, Maghrib and Isha as *Prayed*, *Missed* or *Made up (Qada)* for any date |
| Daily progress | "3 of 5 prayers completed" with a progress bar, a positive message and a streak counter |
| Reports | Last 7 / 30 days: daily completion chart, completion rate per prayer, data table |
| Missed prayer record | Private notes, gentle encouragement, one-click "Mark as made up" |
| Knowledge assistant | Gemini Flash answers Salah questions, clearly labelled **AI-generated** |
| Rewards page | Verified Quran verses and Hadith references. No invented reward numbers. |
| Daily reminder | A verified verse or hadith, different each day |

## Files

| File | Purpose |
|---|---|
| `app.py` | The whole application |
| `requirements.txt` | Libraries that Streamlit Cloud installs |
| `README.md` | This guide |
| `.gitignore` | Stops secrets and private databases from being uploaded |
| `test_app.py` | 30 automated tests (uses a fake AI, no API key needed) |

## Libraries and why we use them

- **Python**: the programming language.
- **Streamlit**: turns Python code into a web page with no HTML/JavaScript. Each widget (`st.radio`, `st.progress`) is one line.
- **google-genai**: the official Google SDK used to send a question to Gemini Flash and receive the answer.
- **SQLite** (built into Python): a small database stored in one file. It keeps prayer records between visits.
- **Pandas**: organises records into tables (DataFrames) and calculates totals and percentages.
- **Plotly**: draws interactive charts (hover, zoom) that work well on phones.

## How the app works (for your presentation)

1. **Start**: Streamlit runs `main()` in `app.py` every time the user clicks something.
2. **Profile**: the user creates a username and PIN. The PIN is never saved, only a *salted PBKDF2 hash*, so even the database owner cannot read it.
3. **Tracking**: each choice is saved in the `prayer_log` table (one row per user, date and prayer). Saving the same prayer again *updates* the row, so there are no duplicates.
4. **Progress**: `daily_progress()` counts *Prayed* and *Made up* records out of 5.
5. **Reports**: `history_report()` loads records into Pandas, fills days with no records as 0, and Plotly draws the bars.
6. **AI assistant**: `ask_gemini()` validates the question, sends it with a *system prompt* that forbids inventing verses or reward numbers, and shows the reply with an "AI-generated" label. Errors are turned into friendly messages.
7. **Verified content**: verses and hadith come from a hand-written list in `app.py`, each with a reference. AI text is never mixed into this list.

The code is split into 7 numbered sections. Sections 1-6 contain no Streamlit code, which is why they can be unit tested.

## Security and privacy

- API key is read from Streamlit **Secrets** or an environment variable, never from the source code.
- All inputs are validated (username, PIN, date, prayer, note length, question length).
- SQL uses `?` placeholders, which prevents SQL injection.
- Each user can see only their own records. Users can delete their account and all data.
- Five wrong logins in a session lock the login form.
- Religious content is labelled: **Verified source** (hand-written with reference) vs **AI-generated**.

## Run it on your own computer

```bash
pip install -r requirements.txt
python -m unittest test_app -v          # run the tests
streamlit run app.py
```

To test the AI locally, create the file `.streamlit/secrets.toml` (it is ignored by Git):

```toml
GEMINI_API_KEY = "your-key-here"
```

Get a free key at <https://aistudio.google.com/apikey>.

## Upload to GitHub (website only)

1. Go to <https://github.com> and sign in (create an account if needed).
2. Click **+** (top right) → **New repository**.
3. Repository name: `islamic-prayer-tracker`. Choose **Public** (needed for the free Streamlit Cloud plan unless you connect a private repo). Click **Create repository**.
4. On the new page click **uploading an existing file**.
5. Drag and drop `app.py`, `requirements.txt`, `README.md`, `.gitignore` and `test_app.py`.
   - Hidden-file tip: if `.gitignore` is not visible on your computer, enable "Show hidden files", or on GitHub use **Add file → Create new file**, name it `.gitignore` and paste the content.
6. Scroll down and click **Commit changes**.
7. **Never upload your API key or `secrets.toml`.**

## Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and click **Sign in with GitHub**.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Choose your repository `islamic-prayer-tracker`, branch `main`, main file path `app.py`.
4. Click **Advanced settings** → **Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
   (Optional) choose a different model: `GEMINI_MODEL = "gemini-2.5-flash"`.
5. Click **Deploy**. After a minute you get a public link like `https://your-app.streamlit.app`.
6. To change the key later: app menu → **Settings → Secrets**.

## Important limitations (mention these honestly in class)

- Streamlit Community Cloud storage is **temporary**: the SQLite file can be reset when the app restarts or sleeps. For permanent storage, move to a hosted database (e.g. Supabase or PostgreSQL).
- Username + PIN is a simple login suitable for a student project. For real-world use, add proper authentication.
- Gemini model names change over time. If you see a "model not found" error, set `GEMINI_MODEL` to a current Flash model listed in the Google AI documentation.
- AI answers can be wrong. They are explanations, **not fatwas**. Always verify with the Quran, authentic Hadith and a qualified scholar.
- English text of verses and hadith in this app is a paraphrased meaning. Please check a reliable translation before sharing publicly.
- Prayer times are not calculated; users record their own prayers.

## Possible improvements

Prayer-time API, Qibla direction, Sunnah/Nafl prayers, Ramadan mode, reminders by email, Urdu/Arabic interface.
