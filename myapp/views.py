import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from huggingface_hub import InferenceClient
import json

@csrf_exempt
def get_bot_response(request):
    if request.method == 'POST':
        try:
            # Obtener token de variables de entorno
            hf_token = os.getenv('HF_API_TOKEN')
            if not hf_token:
                return JsonResponse({
                    'error': 'Configuración faltante: HF_API_TOKEN no está definido'
                }, status=500)

            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            client = InferenceClient(
                provider="nebius",
                api_key=hf_token  # Token desde variable de entorno
            )
            
            completion = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": user_message}],
                max_tokens=512,
            )
            
            return JsonResponse({
                'response': completion.choices[0].message.content
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f"Error al procesar la solicitud: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def chat_view(request):
    return render(request, 'index.html')