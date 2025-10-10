import streamlit as st
from PIL import Image
import openai
import io
import os

st.title("Construction Plan Q&A (VLM)")

# Get API key from environment variable or Streamlit secrets
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your OpenAI API Key", type="password")


uploaded_file = st.file_uploader(
    "Upload a construction plan image or PDF",
    type=["png", "jpg", "jpeg", "gif", "pdf"]
)


# Display image or PDF page images above the question box
if uploaded_file:
    filetype = uploaded_file.type
    if filetype == "application/pdf":
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        page_images = split_pdf_to_pages(pdf_bytes)
        st.write(f"PDF has {len(page_images)} pages.")
        for idx, img_bytes in enumerate(page_images):
            st.image(img_bytes, caption=f"Page {idx+1}", use_container_width=True)
    else:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption="Uploaded Plan", use_container_width=True)

question = st.text_input("Ask a question about the plan (for images only):")


# PDF handling
def split_pdf_to_pages(pdf_bytes):
    import fitz  # PyMuPDF
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i in range(len(pdf_doc)):
        page = pdf_doc.load_page(i)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        pages.append(img_bytes)
    return pages

def call_openai_gpt4v(image_bytes, question, api_key):
    import base64
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    openai.api_key = api_key
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]}
            ],
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API Error: {e}"

if uploaded_file and api_key:
    filetype = uploaded_file.type
    if filetype == "application/pdf":
        # PDF: split into page images
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        page_images = split_pdf_to_pages(pdf_bytes)
        st.write(f"PDF has {len(page_images)} pages.")
        for idx, img_bytes in enumerate(page_images):
                st.image(img_bytes, caption=f"Page {idx+1}", use_container_width=True)
                if question:
                    st.write(f"Processing your question for page {idx+1}...")
                    answer = call_openai_gpt4v(img_bytes, question, api_key)
                    st.success(f"Answer for Page {idx+1}:")
                    st.write(answer)
    else:
        # Image file
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        if question:
              st.write("Processing your question...")
              answer = call_openai_gpt4v(image_bytes, question, api_key)
              st.success("Answer:")
              st.write(answer)
elif uploaded_file and question and not api_key:
    st.warning("Please provide your OpenAI API key.")
