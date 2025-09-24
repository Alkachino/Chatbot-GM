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
            
            prompt = f"""Instrucciones:
            1. {instruction}
            2. Si la información no está en el documento, di "No encuentro esta información en las Best Practices".
            3. Sé preciso y cita las secciones relevantes cuando sea posible.

            CONTENIDO DEL DOCUMENTO:
            {context}

            PREGUNTA:
            {user_message}

            RESPUESTA:"""
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.4,
                top_p=0.9
            )
            
            # Post-procesamiento para mejorar la respuesta
            response_text = response.choices[0].message.content
            
            # Asegurar que no halle respuestas cuando no hay información
            if "no encuentro" in response_text.lower() or "no está en el documento" in response_text.lower():
                response_text = "No encuentro información específica sobre esto en las Best Practices."
            
            return JsonResponse({'response': response_text})
            
        except json.JSONDecodeError:
            return JsonResponse({'response': "Error: Formato de solicitud inválido."})
        except Exception as e:
            return JsonResponse({'response': f"Error: {str(e)}"})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def chat_view(request):
    return render(request, 'index.html')