import streamlit as st
from PIL import Image
import io
import os
import requests

st.title("Construction Plan Q&A (VLM)")

uploaded_file = st.file_uploader(
    "Upload a construction plan image or PDF",
    type=["png", "jpg", "jpeg", "gif", "pdf"]
)

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

# Display image or PDF page images above the question box
if uploaded_file:
    filetype = uploaded_file.type
    if filetype == "application/pdf":
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        page_images = split_pdf_to_pages(pdf_bytes)
        st.write(f"PDF has {len(page_images)} pages.")
        for idx, img_bytes in enumerate(page_images):
            st.image(img_bytes, caption=f"Page {idx+1}", width='stretch')
    else:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption="Uploaded Plan", width='stretch')

question = st.text_input("Ask a question about the plan (for images only):")

# Call FastAPI VLM backend
VLM_API_URL = os.environ.get("VLM_API_URL", "http://localhost:8080/describe-image/")

def call_vlm_api(image_bytes, question):
    files = {"image": ("image.png", image_bytes, "image/png")}
    data = {"question": question}
    try:
        response = requests.post(VLM_API_URL, files=files, data=data)
        if response.status_code == 200:
            return response.json().get("answer", "No answer returned.")
        else:
            return f"API Error: {response.status_code} {response.text}"
    except Exception as e:
        return f"API Error: {e}"

if uploaded_file and question:
    filetype = uploaded_file.type
    if filetype == "application/pdf":
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        page_images = split_pdf_to_pages(pdf_bytes)
        st.write(f"PDF has {len(page_images)} pages.")
        for idx, img_bytes in enumerate(page_images):
            st.image(img_bytes, caption=f"Page {idx+1}", width='stretch')
            if question:
                st.write(f"Processing your question for page {idx+1}...")
                answer = call_vlm_api(img_bytes, question)
                st.success(f"Answer for Page {idx+1}:")
                st.write(answer)
    else:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read()
        if question:
            st.write("Processing your question...")
            answer = call_vlm_api(image_bytes, question)
            st.success("Answer:")
            st.write(answer)
