import streamlit as st
import imaplib
import email
from email.header import decode_header
import openai

# ---------------------- CONFIGURATION ----------------------
IMAP_SERVER = "imap.gmail.com"
EMAIL = st.secrets["EMAIL_ADDRESS"]
PASSWORD = st.secrets["EMAIL_APP_PASSWORD"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# ---------------------- FETCH EMAILS USING IMAP ----------------------
def fetch_emails(query: str, max_results: int = 5):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select('inbox')
    status, data = mail.search(None, f'(SUBJECT "{query}")')
    email_ids = data[0].split()[-max_results:]
    emails = []
    for eid in reversed(email_ids):
        _, msg_data = mail.fetch(eid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_header(msg['Subject'])[0][0]
        date = msg['Date']
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        emails.append({'subject': subject, 'date': date, 'body': body})
    mail.logout()
    return emails

# ---------------------- SUMMARIZE EMAIL ----------------------
def summarize_email(subject: str, body: str) -> str:
    openai.api_key = OPENAI_API_KEY
    prompt = f"Summarize this email for a busy parent in 2-3 bullet points:\n\nSubject: {subject}\nBody: {body}"    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

# ---------------------- STREAMLIT UI ----------------------
st.title("📧 Parent Email Summarizer (Cloud‑Only)")
query = st.text_input("Search keyword (e.g. school, teacher):", value="school")
num = st.slider("Number of emails to summarize:", min_value=1, max_value=10, value=5)

if st.button("Fetch & Summarize"):
    with st.spinner("Fetching emails..."):
        emails = fetch_emails(query, num)
    if not emails:
        st.warning("No emails found matching query.")
    else:
        for e in emails:
            st.markdown(f"**{e['subject']}** — {e['date']}")
            st.write(summarize_email(e['subject'], e['body']))
            st.divider()

# ---------------------- SETUP INSTRUCTIONS ----------------------
st.sidebar.header("🚀 Setup for Streamlit Cloud")
st.sidebar.markdown(
    """
1️⃣ Create a Gmail App Password (Google Account → Security → App passwords).
2️⃣ In Streamlit Cloud app settings → Secrets, add:
   ```
   EMAIL_ADDRESS = "you@gmail.com"
   EMAIL_APP_PASSWORD = "your-app-password"
   OPENAI_API_KEY = "sk-..."
   ```
3️⃣ Push this script to a GitHub repo and connect it in Streamlit Cloud → Deploy.
4️⃣ Done! Your email summarizer runs entirely in the browser.
"""
)
