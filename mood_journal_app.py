import streamlit as st
import datetime
import sqlite3
from collections import Counter
import pandas as pd
import os

# Mood keywords
MOOD_KEYWORDS = {
    'happy': ['happy', 'great', 'awesome', 'excited', 'joyful'],
    'neutral': ['okay', 'fine', 'normal', 'meh'],
    'sad': ['sad', 'tired', 'bad', 'down', 'upset']
}

# Mood emojis and activity suggestions
MOOD_EMOJIS = {
    'happy': '😊',
    'neutral': '😐',
    'sad': '😢'
}
ACTIVITY_SUGGESTIONS = {
    'happy': 'Keep shining! Maybe share your positivity with a friend!',
    'neutral': 'How about a relaxing walk or reading a book?',
    'sad': 'Take it easy. Try some music or a warm drink to lift your spirits.'
}

# DB setup
def init_db():
    conn = sqlite3.connect('mood_journal.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entries 
                 (user_name TEXT, date TEXT, entry TEXT, mood TEXT,
                  FOREIGN KEY(user_name) REFERENCES users(name))''')
    conn.commit()
    conn.close()

class UserProfile:
    def __init__(self, name):
        self.name = name
        self.mood_history = self.load_entries()

    def add_entry(self, date, entry, mood):
        conn = sqlite3.connect('mood_journal.db')
        c = conn.cursor()
        c.execute("INSERT INTO entries (user_name, date, entry, mood) VALUES (?, ?, ?, ?)",
                  (self.name, date, entry, mood))
        conn.commit()
        conn.close()
        self.mood_history[date] = (entry, mood)

    def load_entries(self):
        conn = sqlite3.connect('mood_journal.db')
        c = conn.cursor()
        c.execute("SELECT date, entry, mood FROM entries WHERE user_name = ?", (self.name,))
        entries = {row[0]: (row[1], row[2]) for row in c.fetchall()}
        conn.close()
        return entries

    def get_history(self):
        return self.mood_history

    def get_most_common_mood(self):
        if not self.mood_history:
            return "No entries yet"
        moods = [mood for _, mood in self.mood_history.values()]
        return Counter(moods).most_common(1)[0][0]

def analyze_mood(entry):
    entry = entry.lower()
    for mood, keywords in MOOD_KEYWORDS.items():
        if any(keyword in entry for keyword in keywords):
            return mood
    return 'neutral'

def get_weekly_summary(user):
    today = datetime.datetime.now()
    week_ago = today - datetime.timedelta(days=7)
    weekly_moods = [
        mood for date, (_, mood) in user.get_history().items()
        if datetime.datetime.strptime(date, '%Y-%m-%d') >= week_ago
    ]
    if not weekly_moods:
        return "No entries this week."
    mood_counts = Counter(weekly_moods)
    return mood_counts

def export_to_txt(user, filename='mood_journal.txt'):
    try:
        with open(filename, 'w') as file:
            file.write(f"{user.name}'s Mood Journal\n\n")
            for date, (entry, mood) in user.get_history().items():
                file.write(f"Date: {date}\nEntry: {entry}\nMood: {mood}\n\n")
        st.success(f"Journal exported to {filename}!")
        return filename
    except Exception as e:
        st.error(f"Error exporting journal: {e}")
        return None

# -------- Streamlit App ----------
def main():
    st.set_page_config(page_title="Mood Journal", page_icon="📘")
    init_db()

    st.markdown(
        """
        <div style='text-align: center;'>
            <img src='https://cdn-icons-png.flaticon.com/512/742/742751.png' width='80'>
            <h1 style='color:#4CAF50;'>Mood Journal & Sentiment Tracker</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    if 'user' not in st.session_state:
        st.session_state.user = None

    # Sidebar Navigation
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3771/3771394.png", width=100)
    
    menu = st.sidebar.radio("📌 Menu", [
        "Login / Register",
        "Add New Entry",
        "View Mood History",
        "Most Common Mood",
        "Weekly Summary",
        "Export Journal",
        "Admin Panel"
    ])

    # Login/Register Page
    if menu == "Login / Register":
        st.subheader("🌟 Let's Get Started")
        name = st.text_input("👤 Enter your name:")
        if st.button("Start Journal"):
            if name.strip():
                conn = sqlite3.connect('mood_journal.db')
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (name) VALUES (?)", (name.strip(),))
                    conn.commit()
                    st.session_state.user = UserProfile(name.strip())
                    st.success(f"🎉 Welcome, {name}!")
                except sqlite3.IntegrityError:
                    st.session_state.user = UserProfile(name.strip())
                    st.info(f"👋 Welcome back, {name}!")
                conn.close()
            else:
                st.error("⚠️ Name cannot be empty.")
        return

    if st.session_state.user is None:
        st.warning("Please login/register first from the sidebar.")
        return

    user = st.session_state.user
    st.sidebar.subheader(f"👋 Hello, {user.name}!")

    # Mood Entry
    if menu == "Add New Entry":
        st.subheader("📝 How are you feeling today?")
        entry = st.text_area("Write your thoughts:")

        if st.button("Submit Entry"):
            if entry.strip():
                date = datetime.datetime.now().strftime('%Y-%m-%d')
                mood = analyze_mood(entry)
                user.add_entry(date, entry, mood)
                st.success(f"{MOOD_EMOJIS[mood]} Mood recorded: {mood.capitalize()}")
                st.info(f"💡 Suggestion: {ACTIVITY_SUGGESTIONS[mood]}")
            else:
                st.error("⚠️ Entry cannot be empty.")

    # View Mood History
    elif menu == "View Mood History":
        st.subheader("📜 Your Mood History")
        history = user.get_history()
        if not history:
            st.write("😕 No entries yet.")
        else:
            df = pd.DataFrame(
                [(date, entry, mood) for date, (entry, mood) in history.items()],
                columns=["Date", "Entry", "Mood"]
            ).sort_values(by="Date", ascending=False)
            st.dataframe(df)
            mood_counts = df["Mood"].value_counts()
            st.bar_chart(mood_counts)

    # Most Common Mood
    elif menu == "Most Common Mood":
        mood = user.get_most_common_mood()
        emoji = MOOD_EMOJIS.get(mood, "")
        st.metric(label="💖 Most Frequent Mood", value=f"{mood.capitalize()} {emoji}")

    # Weekly Summary
    elif menu == "Weekly Summary":
        st.subheader("📅 Weekly Summary")
        summary = get_weekly_summary(user)
        if isinstance(summary, str):
            st.write(summary)
        else:
            df = pd.DataFrame(summary.items(), columns=['Mood', 'Count'])
            st.bar_chart(df.set_index('Mood'))

    # Export Journal
    elif menu == "Export Journal":
        st.subheader("📤 Export Your Journal")
        if st.button("Export to Text File"):
            filename = export_to_txt(user)
            if filename and os.path.exists(filename):
                with open(filename, 'rb') as file:
                    st.download_button(
                        label="⬇️ Download Journal",
                        data=file,
                        file_name=filename,
                        mime="text/plain"
                    )

    # Admin Panel
    elif menu == "Admin Panel":
        st.subheader("🛠️ Admin Panel")
        st.warning("⚠️ Use this carefully. This will delete all users and entries.")
        if st.button("Clear All Data"):
            conn = sqlite3.connect('mood_journal.db')
            c = conn.cursor()
            c.execute("DELETE FROM entries")
            c.execute("DELETE FROM users")
            conn.commit()
            conn.close()
            st.success("✅ All data has been cleared!")
            st.session_state.user = None
if __name__ == "__main__":
    main()
