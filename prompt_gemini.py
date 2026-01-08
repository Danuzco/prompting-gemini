import argparse
from pathlib import Path
from google import genai
from google.genai import types
from docx import Document

path_cwd = Path.cwd()
images_path = path_cwd.joinpath('images')
norms_path = path_cwd.joinpath('normativas')

parser = argparse.ArgumentParser(description="Obtener parámetros")
parser.add_argument("--path", type=str, help="Image name")

selected_image_path = parser.parse_args()
selected_image_path = images_path.joinpath(selected_image_path.path)

client = genai.Client(api_key="API-KEY")

# --- Define PDF/Doc Paths ---
pdf_paths = [
    norms_path.joinpath('conceptos.txt'),
    norms_path.joinpath('Normativa_Andamios_SPDC.txt'),
    norms_path.joinpath('NCh-1258-04-2005.pdf'),
    path_cwd.joinpath('Estandar_Altura_SPDC.pdf'),
    path_cwd.joinpath('estiba_y_estrobado_de_cargas.pdf')
]

# --- Helper Functions ---
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

def prepare_image(path):
    """Prepare image file"""
    with open(path, "rb") as f:
        return types.Part.from_bytes(data=f.read(), mime_type="image/jpeg")

# --- Build the request content ---
contents = []

# 1. Add the prompt text
prompt = (
    "Analice la imagen basándose en los archivos adjuntos y las definiciones descritas en el archivo 'conceptos.txt'."
    "Diga si el (o los) trabajador(es) está(n) bajo riesgo potencial y usa(n) adecuadamente su(s) EPP, según la normativa chilena vigente. "
    "\nAdemás, ponga en formato json la siguiente información:"
    " 1. ¿El trabajador utiliza un Arnés de Cuerpo Completo que ajusta en muslos, pelvis, pecho y hombros? "
    " 2. Presencia de cabo de vida, "
    " 4. Anclado apropiadamente a la cuerda de vida, "
    " 5. score estimado entre 1 y 10 (1: no cumple, 10: cumple totalmente) de cumplimiento de normativa, "
    " usando True or False."
)
contents.append(prompt)

# 2. Add the Image
contents.append(prepare_image(selected_image_path))

# 3. Add all the Documents (PDFs/DOCX/TXT)
for path in pdf_paths:
    if path.exists():
        print(f"Adding file: {path.name}")
        contents.append(prepare_file(path))
    else:
        print(f"Warning: File not found: {path}")

# --- Generate Response ---
print("\n" + prompt + "\n\n" + "Respuesta:")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=types.GenerateContentConfig(
        response_mime_type="text/plain"
    )
)

print(response.text)