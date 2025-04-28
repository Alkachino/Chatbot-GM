from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="nebius",
    api_key="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",
)

completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3-0324",
    messages=[
        {
            "role": "user",
            "content": "dime las 7 maravillas del mundo antigu"
        }
    ],
    max_tokens=512,
)

print(completion.choices[0].message)