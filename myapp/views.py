from django.shortcuts import render
from django.http import JsonResponse
from huggingface_hub import InferenceClient
from django.views.decorators.csrf import csrf_exempt
import json

client = InferenceClient(
    provider="nebius",
    api_key="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",
)

def chat_view(request):
    return render(request, 'index.html')

@csrf_exempt
def get_bot_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            completion = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": user_message}],
                max_tokens=512,
            )
            
            response = completion.choices[0].message.content
            return JsonResponse({'response': response})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)