import socket
import threading

def receber_mensagem():
    global pacotes_recebidos
    while True:
        dados = conexao.recv(1024)

        if not dados:
            print("Cliente desconectou")
            break

        mensagem_recebida = dados.decode("utf8")
        pacotes_recebidos += 1

        print(f"\nCliente: {mensagem_recebida}")

        if mensagem_recebida.lower() == "sair":
            exibir_relatorio()
            print("Cliente encerrou o chat")
            break

def exibir_relatorio():
    print("\nRELATÓRIO FINAL")
    print(f"Pacotes enviados: {pacotes_enviados}")
    print(f"Pacotes recebidos: {pacotes_recebidos}")
    print(f"Total: {pacotes_enviados + pacotes_recebidos}")

pacotes_enviados = 0
pacotes_recebidos = 0

print("SERVIDOR DE CHAT TCP/IP")
print()

PORTA = int(input("Digite a porta TCP do servidor: "))

tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp.bind(("0.0.0.0", PORTA))

tcp.listen(1)

print(f"\nAguardando conexão na porta {PORTA}...")

conexao, endereco = tcp.accept()

thread_receber = threading.Thread(target=receber_mensagem, daemon=True)
thread_receber.start()

print("\n")
print(f"Cliente conectado: {endereco[0]}:{endereco[1]}")
print("Envie uma mensagem")
print("Digite 'sair' para encerrar o chat")

while True:
    mensagem_enviar = input("Você: ").strip()

    if not mensagem_enviar:
        continue

    try:
        conexao.send(bytes(mensagem_enviar, "utf8"))
        pacotes_enviados += 1
    except:
        print("Erro ao enviar mensagem")
        break

    if mensagem_enviar.lower() == "sair":
        break


conexao.close()
tcp.close()
exibir_relatorio()

print("Servidor encerrado")
