import streamlit as st
import imaplib
import email
from email.header import decode_header
import openai
import time

# ---------------------- CONFIGURATION ----------------------
IMAP_SERVER = "imap.gmail.com"
EMAIL = st.secrets.get("EMAIL_ADDRESS", "").strip().strip('"')
PASSWORD = st.secrets.get("EMAIL_APP_PASSWORD", "").strip().strip('"')
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "").strip().strip('"')

# ---------------------- FETCH EMAILS USING IMAP ----------------------
def fetch_emails(query: str, max_results: int = 5):
    if not EMAIL or not PASSWORD:
        st.error("🔒 Missing Gmail credentials. Check your Streamlit secrets for EMAIL_ADDRESS and EMAIL_APP_PASSWORD.")
        return []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
    except imaplib.IMAP4.error as e:
        st.error(f"❌ IMAP login failed: {e}\nCheck your app password is 16 characters (no spaces/quotes) and IMAP is enabled in Gmail settings.")
        return []
    try:
        mail.select('inbox')
        status, data = mail.search(None, f'(SUBJECT "{query}")')
        email_ids = data[0].split()[-max_results:] if data and data[0] else []
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
        return emails
    finally:
        mail.logout()

# ---------------------- SUMMARIZE EMAIL ----------------------
def summarize_email(subject: str, body: str) -> str:
    if not OPENAI_API_KEY:
        st.error("🔒 Missing OpenAI API key. Add OPENAI_API_KEY to Streamlit secrets.")
        return ""
    openai.api_key = OPENAI_API_KEY
    prompt = f"Summarize this email for a busy parent in 2-3 bullet points:\n\nSubject: {subject}\nBody: {body}"    
    for attempt in range(2):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            if attempt == 0:
                time.sleep(5)
                continue
            st.error("⚠️ OpenAI rate limit exceeded — please try again in a minute.")
            return ""
        except Exception as e:
            st.error(f"⚠️ OpenAI API error: {e}")
            return ""
    return ""

# ---------------------- STREAMLIT UI ----------------------
st.title("📧 Parent Email Summarizer (Cloud‑Only)")
query = st.text_input("Search keyword (e.g. school, teacher):", value="school")
num = st.slider("Number of emails to summarize:", min_value=1, max_value=10, value=5)
if st.button("Fetch & Summarize"):
    with st.spinner("Fetching emails..."):
        emails = fetch_emails(query, num)
    if not emails:
        st.warning("No emails found or an error occurred.")
    else:
        for e in emails:
            st.markdown(f"**{e['subject']}** — {e['date']}")
            summary = summarize_email(e['subject'], e['body'])
            st.write(summary if summary else "Unable to summarize.")
            st.divider()

# ---------------------- SETUP INSTRUCTIONS ----------------------
st.sidebar.header("🚀 Setup for Streamlit Cloud")
st.sidebar.markdown(
    """
1️⃣ Enable 2FA on your Google Account and create a Gmail App Password (Google Account → Security → App passwords).
2️⃣ In Streamlit Cloud app settings → Secrets, add exactly (no extra spaces or quotes):
   ```
   EMAIL_ADDRESS = you@gmail.com
   EMAIL_APP_PASSWORD = your16charapppassword
   OPENAI_API_KEY = sk-...
   ```
3️⃣ Ensure your app password is exactly 16 characters (no spaces or quotes).
4️⃣ Push this script to GitHub and redeploy on Streamlit Cloud.
5️⃣ Click Fetch & Summarize — any IMAP login or API errors will now display clearly.
"""
)
