from fastapi import FastAPI, File, UploadFile, Form
from google import genai
from pathlib import Path
from google.genai import types
from docx import Document
from PIL import Image
import io

app = FastAPI()
client = genai.Client(api_key="AIzaSyAlgoMcdo7eY08mRhuQetODlrynNwNU7ns")

path_cwd = Path.cwd()
norms_path = path_cwd.joinpath('normativas')

pdf_paths = [
    norms_path.joinpath('conceptos.txt'),
    norms_path.joinpath('Normativa_Andamios_SPDC.txt'),
    norms_path.joinpath('NCh-1258-04-2005.pdf'),
    path_cwd.joinpath('Estandar_Altura_SPDC.pdf'),
    path_cwd.joinpath('estiba_y_estrobado_de_cargas.pdf')
]

def convert_docx_to_text(docx_path):
    """Extract text from DOCX file"""
    doc = Document(docx_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

def prepare_file(path):
    """Prepare file based on extension with encoding fallback"""
    if path.suffix == ".pdf":
        with open(path, "rb") as f:
            return types.Part.from_bytes(data=f.read(), mime_type="application/pdf")
    elif path.suffix == ".docx":
        text_content = convert_docx_to_text(path)
        return text_content  # Return text directly
    elif path.suffix == ".txt":
        # Try multiple encodings (common for Spanish text)
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as f:
                    text_content = f.read()
                print(f"  ✓ Read with {encoding} encoding")
                return text_content  # Return text directly
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode {path.name} with any common encoding")
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


@app.post("/analyze-image")
async def analyze_image(
        prompt: str = Form(...),
        image_file: UploadFile = File(...)
):
    image_bytes = await image_file.read()

    # 1. Create the base contents list starting with the prompt (text)
    # The SDK accepts a mix of strings and Part objects
    contents = [prompt]

    # 2. Properly format the image as a Part object
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=image_file.content_type or "image/jpeg"
    )
    contents.append(image_part)

    # 3. Add the normative files (already formatted as text or Part by prepare_file)
    for path in pdf_paths:
        if path.exists():
            print(f"Adding file: {path.name}")
            file_data = prepare_file(path)
            # if prepare_file returns text, it adds a string.
            # If it returns types.Part (for PDFs), it adds a Part.
            contents.append(file_data)
        else:
            print(f"Warning: File not found: {path}")

    # 4. Generate content
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="text/plain"
            )
        )
        return {
            "analysis": response.text,
            "filename": image_file.filename
        }
    except Exception as e:
        return {"error": str(e)}