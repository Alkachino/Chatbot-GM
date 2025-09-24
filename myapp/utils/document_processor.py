import os
from docx import Document
from typing import Tuple, Dict
import re

def get_document_path():
    """Obtiene la ruta absoluta correcta al documento"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    doc_path = os.path.join(project_root, 'myapp', 'data', 'GM-bp.docx')
    
    if not os.path.exists(doc_path):
        available_files = os.listdir(os.path.dirname(doc_path))
        raise FileNotFoundError(
            f"Documento no encontrado en: {doc_path}\n"
            f"Archivos en el directorio: {', '.join(available_files)}"
        )
    return doc_path

def load_document_contents() -> Tuple[str, Dict[str, str]]:
    """Carga y procesa el documento DOCX devolviendo texto completo y secciones indexadas"""
    try:
        doc_path = get_document_path()
        doc = Document(doc_path)
        
        full_text = []
        sections = {}
        current_section = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
                
            # Detectar Best Practices
            section_match = re.match(r'^(Best Practice \d+)[:\-]?\s*(.*)', text, re.IGNORECASE)
            if section_match:
                current_section = section_match.group(1).title()
                sections[current_section] = section_match.group(2)
                full_text.append(f"\n{current_section}:\n")
            elif current_section:
                sections[current_section] += f"\n{text}"
            
            full_text.append(text)
        
        return "\n".join(full_text), sections
    
    except Exception as e:
        raise Exception(f"Error al procesar documento: {str(e)}")