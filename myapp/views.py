import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.templatetags.static import static
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from .utils.rag_service import RAGService

IMAGE_METADATA = {
    "bp1_map_pocket_clearance.png": {
        "title": "Espacio entre Portaobjetos y Controles del Asiento",
        "description": "Ilustra el espacio libre requerido entre el portaobjetos de la puerta y el asiento, destacando la holgura necesaria para acceder a los controles del asiento."
    },
    "bp2_trim_foot_zones.png": {
        "title": "Zonas de Interfaz del 'Trim Foot'",
        "description": "Modelo CAD que muestra las 3 zonas de la interfaz 'Trim Foot' y sus medidas requeridas: Zona 1 (0mm), Transición (1.5mm) y Zona 2 (3mm)."
    },
    "bp3_scope.png": {
        "title": "Alcance - Manijas 'Pull Handle' vs. 'Pull Cup'",
        "description": "Ejemplos visuales que diferencian las manijas 'Pull Handle' (cubiertas por esta práctica) de las 'Pull Cup' (excluidas de esta práctica)."
    },
    "bp3_handle_zone.png": {
        "title": "Zona de 360° de la Manija 'Pull Handle'",
        "description": "Detalle fotográfico de una 'Pull Handle' que resalta su zona de agarre e interfaz completa de 360° con el panel de la puerta."
    },
    "bp3_attachment.png": {
        "title": "Ubicación de Sujetadores de la Manija",
        "description": "Vista CAD de la estructura de la manija, señalando las ubicaciones de los puntos de anclaje usados para fijarla a la lámina de la puerta con al menos dos sujetadores."
    },
    "bp4_pull_cup.png": {
        "title": "Ejemplo de Manija 'Pull Cup'",
        "description": "Ejemplo de un diseño 'Pull Cup', el cual se integra en el panel y se sujeta a la lámina metálica con un solo tornillo."
    },
    "bp5_buckle_location.png": {
        "title": "Tipos de Anclaje de Hebilla (Asiento vs. Carrocería)",
        "description": "Diagrama que compara las dos configuraciones de anclaje de la hebilla del cinturón: fijada al asiento o fijada a la carrocería del vehículo."
    },
    "bp5_latch_gap.png": {
        "title": "Espacio Requerido entre Pestaña (Latch) y Panel",
        "description": "Detalle que muestra el espacio libre (gap) requerido entre la pestaña (latch) del cinturón y el panel de la puerta para evitar daños."
    },
    "bp6_label_location.png": {
        "title": "Ubicación y Guía para Colocación de Etiqueta",
        "description": "Ubicación designada en el panel de la puerta para la etiqueta de información. Debe ser un área plana y se recomienda una línea guía para su colocación."
    },
    "bp7_rack_transport.png": {
        "title": "Cinta de Protección para Transporte en Racks",
        "description": "Indica la colocación de cinta protectora (100x100mm) en las esquinas superiores del panel para evitar daños durante el transporte en racks."
    },
    "bp7_export_coverage.png": {
        "title": "Cobertura de Cinta para Vehículos de Exportación",
        "description": "Zonas de cobertura de cinta protectora (Superior, Reposabrazos e Inferior) que se requieren específicamente para vehículos de exportación."
    }
}

load_dotenv()

# Initialize RAG service
rag_service = None
try:
    rag_service = RAGService()
    rag_service.initialize_vector_store()
    print("RAG service initialized successfully")
except Exception as e:
    print(f"Error initializing RAG service: {str(e)}")

@csrf_exempt
def get_bot_response(request):
    global rag_service
    
    if request.method == 'POST':
        try:
            # Verificar configuración
            hf_token = os.getenv('HF_API_TOKEN')
            if not hf_token:
                return JsonResponse({'response': "Error: Token de API no configurado"})

            # Initialize RAG service if not already done
            if rag_service is None:
                try:
                    rag_service = RAGService()
                    rag_service.initialize_vector_store()
                except Exception as e:
                    return JsonResponse({
                        'response': "Error: No puedo acceder a los documentos. Por favor verifica que los archivos PDF estén correctamente ubicados."
                    })

            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'response': "Por favor ingresa una pregunta."})

            # Use RAG to get relevant context
            try:
                context, retrieved_docs = rag_service.get_relevant_context(user_message, k=3)
                print(f"Retrieved {len(retrieved_docs)} relevant chunks for query: {user_message}")
            except Exception as e:
                return JsonResponse({'response': f"Error al buscar información: {str(e)}"})

            # Generar respuesta con el modelo
            client = InferenceClient(provider="nebius", api_key=hf_token)
            
            # List of available images for the LLM to use
            image_files = [f for f in os.listdir(os.path.join('static', 'images', 'BP')) if f.endswith('.png')]
            
            # Optimized prompt - reduced from ~150 tokens to ~50 tokens
            prompt = f"""Responde en JSON: {{"texto": "...", "imagenes": [...]}}
- texto: respuesta basada SOLO en el contexto
- imagenes: nombres de archivos relevantes de {image_files} (vacío si no aplica)
- Si no hay info: {{"texto": "No encuentro esta información", "imagenes": []}}

CONTEXTO:
{context}

PREGUNTA: {user_message}

JSON:"""
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,  # Reduced from 800
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

                images_with_metadata = []
                for filename in image_filenames:
                    if isinstance(filename, str):
                        metadata = IMAGE_METADATA.get(filename, {})
                        images_with_metadata.append({
                            "url": static(f"images/BP/{filename}"),
                            "title": metadata.get("title", ""),
                            "description": metadata.get("description", "")
                        })

            except (json.JSONDecodeError, AttributeError) as e:
                # Fallback if the LLM fails to produce valid JSON
                text_response = llm_output_str
                images_with_metadata = []

            return JsonResponse({'text_response': text_response, 'images': images_with_metadata})
            
        except json.JSONDecodeError:
            return JsonResponse({'response': "Error: Formato de solicitud inválido."})
        except Exception as e:
            return JsonResponse({'response': f"Error: {str(e)}"})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def chat_view(request):
    return render(request, 'index.html')