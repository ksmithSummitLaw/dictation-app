# streamlit_app.py

import os
import io
import streamlit as st
import openai
from docxtpl import DocxTemplate

# ─── Configuration ─────────────────────────────────────────────────────────────
# Pull your key from Streamlit Cloud Secrets
# In your Streamlit Cloud app settings → Secrets, add:
#    OPENAI_API_KEY="sk-…your-new-key…"
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Live Dictate a Letter (DOCX)", layout="wide")

# ─── UI ─────────────────────────────────────────────────────────────────────────
st.title("📄 Live Dictate Your Letter (DOCX)")

# 1) Record audio in-browser
uploaded_audio = st.audio_input("▶️ Click to record your dictation")

# 2) If we have audio, extract raw bytes and let the user play it back
if uploaded_audio:
    audio_bytes = uploaded_audio.read()
    st.audio(audio_bytes, format="audio/wav")

    # 3) Once happy, click to generate
    if st.button("Generate .docx Letter"):
        # 4) Transcribe via Whisper
        with st.spinner("📝 Transcribing via Whisper…"):
            wav_buf = io.BytesIO(audio_bytes)
            wav_buf.name = uploaded_audio.name or "speech.wav"
            transcript_resp = openai.Audio.transcribe(
                model="whisper-1",
                file=wav_buf
            )
            transcript = transcript_resp["text"]

        st.markdown(f"**Transcript:**\n> {transcript}")

        # 5) Draft the letter with GPT
        with st.spinner("🤖 Drafting letter with GPT…"):
            prompt = (
                "You are a legal assistant. Draft a formal letter based on this dictation; "
                "do not output a placeholder for the sender’s name and return address—"
                "they are included on the letterhead:\n\n"
                f"{transcript}"
            )
            chat_resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You draft formal business/legal letters."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
            )
            letter_body = chat_resp.choices[0].message.content.strip()

        st.markdown(f"**Letter Preview:**\n\n{letter_body}")

        # 6) Merge into your .docx template
        tpl_path = os.path.join("static", "letterhead.docx")
        if not os.path.exists(tpl_path):
            st.error(f"❌ Could not find template at `{tpl_path}`")
        else:
            tpl = DocxTemplate(tpl_path)
            tpl.render({"body_text": letter_body})
            out_buf = io.BytesIO()
            tpl.save(out_buf)
            out_buf.seek(0)

            st.success("✅ Your letter is ready!")
            st.download_button(
                label="Download Letter (.docx)",
                data=out_buf,
                file_name="generated_letter.docx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.wordprocessingml.document"
                ),
            )