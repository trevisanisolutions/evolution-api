from dotenv import load_dotenv

from dao.firebase_client import init_firebase, FirebaseClient
from services.core.whatsapp_service import WhatsappService

# Carrega .env e inicializa Firebase
load_dotenv(override=True)
init_firebase()

print("🔧 Modo Desenvolvedor Inicializado (sem FastAPI, sem BufferCollector)\n")

COLORS = {
    "Reset": "\033[0m",
    "Preto": "\033[30m",
    "Vermelho": "\033[31m",
    "Verde": "\033[32m",
    "Amarelo": "\033[33m",
    "Azul": "\033[34m",
    "Magenta": "\033[35m",
    "Ciano": "\033[36m",
    "Branco": "\033[37m",
    "Cinza claro": "\033[90m"
}

business_phone = "555181216156"
instance_name = "dev_instance"

# Input inicial do telefone
user_phone = input(f"{COLORS['Azul']}Digite o número do usuário (ex: 5551XXXXXXXX): {COLORS['Reset']}").strip()

print(
    f"\n📲 Chat com {user_phone} iniciado. Digite 'sair' para encerrar ou '/change 5551XXXXXXX' para trocar de usuário.\n")

while True:
    msg = input(f"{COLORS['Verde']}Você ({user_phone}): {COLORS['Reset']}").strip()

    if msg.lower() in {"sair", "exit", "quit"}:
        print("Encerrando chat...")
        break

    if msg.lower().startswith("/change "):
        novo_telefone = msg.split(" ", 1)[1].strip()
        if novo_telefone:
            user_phone = novo_telefone
            print(f"\n🔁 Usuário alterado para {user_phone}.")
        else:
            print("⚠️ Número inválido para troca.")
        continue

    if msg.lower() == "reset":
        FirebaseClient.delete_data(f"establishments/{business_phone}/users/{user_phone}")
        FirebaseClient.delete_data(f"message_buffers/{user_phone}")
        print("🗑️ Dados resetados com sucesso.")
        continue

    print("➡️ Processando")

    try:
        response = WhatsappService.process_user_message(business_phone, msg, user_phone, instance_name)
        print(f"🤖 {COLORS['Amarelo']}IA: {COLORS['Ciano']}{response}{COLORS['Reset']}")
    except Exception as e:
        print(f"❌ Erro ao processar: {str(e)}")
