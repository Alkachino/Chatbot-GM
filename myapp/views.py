import os
import json
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from .utils.document_processor import load_document_contents

load_dotenv()

# Cargar el documento al iniciar
try:
    DOCUMENT_CONTEXT, DOCUMENT_SECTIONS = load_document_contents()
    PRACTICES_LIST = list(DOCUMENT_SECTIONS.keys())
    print(f"Documento cargado. Prácticas encontradas: {PRACTICES_LIST}")
except Exception as e:
    print(f"Error al cargar documento: {str(e)}")
    DOCUMENT_CONTEXT, DOCUMENT_SECTIONS = "", {}

@csrf_exempt
def get_bot_response(request):
    global DOCUMENT_CONTEXT, DOCUMENT_SECTIONS, PRACTICES_LIST
    
    if request.method == 'POST':
        try:
            # Verificar configuración
            hf_token = os.getenv('HF_API_TOKEN')
            if not hf_token:
                return JsonResponse({'response': "Error: Token de API no configurado"})

            # Recargar documento si es necesario
            if not DOCUMENT_CONTEXT:
                try:
                    DOCUMENT_CONTEXT, DOCUMENT_SECTIONS = load_document_contents()
                    PRACTICES_LIST = list(DOCUMENT_SECTIONS.keys())
                except Exception as e:
                    return JsonResponse({
                        'response': "Error: No puedo acceder al documento. Por favor verifica que el archivo esté correctamente ubicado."
                    })

            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'response': "Por favor ingresa una pregunta."})

            # Manejar solicitudes de listado
            if re.search(r'\b(lista|practicas|prácticas|available|help)\b', user_message, re.IGNORECASE):
                return JsonResponse({
                    'response': f"Puedo responder sobre estas Best Practices: {', '.join(PRACTICES_LIST)}\n"
                               f"Puedes preguntar por una específica o hacer una pregunta general."
                })

            # Identificar si menciona una Best Practice específica
            practice_match = re.search(r'\b(Best Practice \d+)\b', user_message, re.IGNORECASE)
            specific_practice = practice_match.group(1).title() if practice_match else None

            # Construir prompt según el tipo de pregunta
            if specific_practice and specific_practice in PRACTICES_LIST:
                # Pregunta sobre una práctica específica
                context = f"{specific_practice}:\n{DOCUMENT_SECTIONS[specific_practice]}"
                instruction = f"Responde únicamente basado en el contenido de {specific_practice}."
            else:
                # Pregunta general - usar todo el documento
                context = DOCUMENT_CONTEXT
                instruction = "Analiza todo el documento y responde basándote en la información más relevante."
                
                if specific_practice:  # Mencionó una práctica que no existe
                    return JsonResponse({
                        'response': f"No encuentro {specific_practice}. Prácticas disponibles: {', '.join(PRACTICES_LIST)}"
                    })

            # Generar respuesta con el modelo
            client = InferenceClient(provider="nebius", api_key=hf_token)
            
            # List of available images for the LLM to use
            image_files = [f for f in os.listdir(os.path.join('static', 'images', 'BP')) if f.endswith('.png')]
            
            prompt = f"""Instrucciones:
            1. {instruction}
            2. Tu respuesta DEBE ser un objeto JSON con la estructura: {{"texto": "...", "imagenes": [...]}}.
            3. En la clave "texto", pon tu respuesta en lenguaje natural.
            4. En la clave "imagenes", pon una lista de los nombres de archivo de imagen más relevantes para la respuesta. Las imágenes disponibles son: {image_files}. Si ninguna es relevante, deja la lista vacía.
            5. Si la información no está en el documento, el "texto" debe ser "No encuentro esta información en las Best Practices" y las "imagenes" una lista vacía.

            CONTENIDO DEL DOCUMENTO:
            {context}

            PREGUNTA:
            {user_message}

            RESPUESTA JSON:"""
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
                top_p=0.9
            )
            
            llm_output_str = response.choices[0].message.content
            
            # Parse the JSON response from the LLM
            try:
                # The model might wrap the JSON in ```json ... ```, so we clean it
                if llm_output_str.strip().startswith('```json'):
                    clean_json_str = llm_output_str.strip().replace('```json', '').replace('```', '')
                else:
                    clean_json_str = llm_output_str
                
                response_data = json.loads(clean_json_str)
                text_response = response_data.get("texto", "No se pudo parsear la respuesta del modelo.")
                image_filenames = response_data.get("imagenes", [])

                # Build full static URLs for the images
                from django.templatetags.static import static
                image_urls = [static(f"images/BP/{filename}") for filename in image_filenames if isinstance(filename, str)]

            except (json.JSONDecodeError, AttributeError) as e:
                # Fallback if the LLM fails to produce valid JSON
                text_response = llm_output_str
                image_urls = []

            return JsonResponse({'text_response': text_response, 'image_urls': image_urls})
            
        except json.JSONDecodeError:
            return JsonResponse({'response': "Error: Formato de solicitud inválido."})
        except Exception as e:
            return JsonResponse({'response': f"Error: {str(e)}"})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def chat_view(request):
    return render(request, 'index.html')