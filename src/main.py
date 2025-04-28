import tkinter as tk
from tkinter import scrolledtext, messagebox
from huggingface_hub import InferenceClient

class ChatBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ChatBot con DeepSeek-V3")
        self.root.geometry("600x700")
        
        # Configurar el cliente de HuggingFace (igual que en tu código)
        self.client = InferenceClient(
            provider="nebius",
            api_key="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",
        )
        
        self.setup_ui()
    
    def setup_ui(self):
        # Área de chat
        self.chat_display = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, width=70, height=25,
            state='disabled', font=('Arial', 10)
        )
        self.chat_display.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Frame para entrada de usuario
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Campo de entrada
        self.user_input = tk.Entry(
            input_frame, font=('Arial', 12)
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.user_input.bind("<Return>", lambda e: self.send_message())
        
        # Botón de enviar
        send_btn = tk.Button(
            input_frame, text="Enviar", command=self.send_message,
            bg="#4CAF50", fg="white", font=('Arial', 10)
        )
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Mensaje inicial
        self.display_message("ChatBot: Hola, soy un asistente basado en DeepSeek-V3. ¿En qué puedo ayudarte?")
    
    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def send_message(self):
        user_message = self.user_input.get()
        if not user_message.strip():
            messagebox.showwarning("Advertencia", "Por favor escribe un mensaje")
            return
        
        self.display_message(f"Tú: {user_message}")
        self.user_input.delete(0, tk.END)
        
        # Mostrar "ChatBot: Pensando..." mientras se genera la respuesta
        thinking_msg = self.chat_display.get("1.0", tk.END)
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, "ChatBot: Pensando...\n\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
        self.root.update()
        
        try:
            # Llamada a la API (igual que en tu código original)
            completion = self.client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3-0324",
                messages=[{"role": "user", "content": user_message}],
                max_tokens=512,
            )
            
            # Eliminar el mensaje "Pensando..." y mostrar la respuesta real
            self.chat_display.config(state='normal')
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.insert(tk.END, thinking_msg)
            response = completion.choices[0].message.content
            self.display_message(f"ChatBot: {response}")
        except Exception as e:
            self.display_message(f"ChatBot: Error al procesar la solicitud: {str(e)}")

def main():
    root = tk.Tk()
    app = ChatBotApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()