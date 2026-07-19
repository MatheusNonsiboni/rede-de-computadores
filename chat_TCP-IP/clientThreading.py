import socket
import threading

def receber_mensagem():
    global pacotes_recebidos
    while True:
        dados = tcp.recv(1024)
        if not dados:
            break

        mensagem_recebida = dados.decode("utf8")
        pacotes_recebidos += 1
        print(f"\nServidor: {mensagem_recebida}", end="")

        if mensagem_recebida.lower() == "sair":
            exibir_relatorio()
            print("Servidor encerrou o chat")
            break

def exibir_relatorio():
    print("\nRELATÓRIO FINAL")
    print(f"Pacotes enviados: {pacotes_enviados}")
    print(f"Pacotes recebidos: {pacotes_recebidos}")
    print(f"Total: {pacotes_enviados + pacotes_recebidos}")

pacotes_enviados = 0
pacotes_recebidos = 0

print("CLIENTE DE CHAT TCP/IP")

IP = input("\nDigite o IP do servidor: ").strip()
PORTA = int(input("Digite a porta TCP: "))

tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"\nConectando em {IP}:{PORTA}...")

try:
    tcp.connect((IP, PORTA))
except Exception as e:
    print(f"Erro ao conectar: {e}")
    tcp.close()
    exit()

print("Conectado! Envie uma mensagem\n")
print("Digite 'sair' para encerrar o chat")

thread_receber = threading.Thread(target=receber_mensagem, daemon=True)
thread_receber.start()

while True:

    mensagem_enviar = input("Você: ").strip()
    tcp.send(bytes(mensagem_enviar, "utf8"))
    pacotes_enviados += 1

    if mensagem_enviar.lower() == "sair":
        break

tcp.close()


print("\nRELATÓRIO FINAL")
print(f"Pacotes enviados: {pacotes_enviados}")
print(f"Pacotes recebidos: {pacotes_recebidos}")
print(f"Total: {pacotes_enviados + pacotes_recebidos}")
print("Cliente encerrado")
