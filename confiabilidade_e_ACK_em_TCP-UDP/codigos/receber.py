import socket
import hashlib

def validar(pacote: bytes) -> tuple[bool, int, str]:
    if len(pacote) != 50:
        return False, -1, ""

    ID = pacote[0:2]
    payload = pacote[2:42]
    chk_recv = pacote[42:50]
    chk_calc = hashlib.sha256(ID + payload).digest()[:8]

    if chk_recv != chk_calc:
        return False, -1, ""

    ID_decodificado = int.from_bytes(ID, byteorder='big')
    payload_decodificado = payload.decode('utf-8')
    return True, ID_decodificado, payload_decodificado

def tcp(porta: int):
    print(f"[TCP] Aguardando na porta {porta}...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", porta))
        srv.listen(1)

        try:
            while True:
                soquete, addr = srv.accept()
                print(f"[TCP] Conectado: {addr}\n")

                ultimo = recebidos = dups = corrompidos = 0

                with soquete:
                    while True:
                        try:
                            dados = b""
                            while len(dados) < 50:
                                chunk = soquete.recv(50 - len(dados))
                                if not chunk:
                                    raise ConnectionResetError
                                dados += chunk

                            ok, ID_decodificado, payload_decodificado = validar(dados)

                            if not ok:
                                corrompidos += 1
                                print(f"Corrompido -> descartado")
                                continue

                            if ID_decodificado == 1:
                                ultimo = 0
                                
                            if ID_decodificado <= ultimo:
                                dups += 1
                                print(f"Duplicado -> sequencia={ID_decodificado}")
                            else:
                                ultimo = ID_decodificado
                                recebidos += 1
                                print(f"sequencia={ID_decodificado:5d} | {payload_decodificado[:20]}...")

                            soquete.sendall(b"ACK")

                        except ConnectionResetError:
                            break

                print(f"[TCP] Conexão encerrada. recebidos={recebidos} duplicados={dups} corrompidos={corrompidos}\n")
                print(f"[TCP] Aguardando próxima conexão...")

        except KeyboardInterrupt:
            print(f"\n[TCP] Servidor encerrado.")

def udp(porta: int):
    print(f"[UDP] Aguardando na porta {porta}...")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", porta))

        ultimo = recebidos = dups = corrompidos = 0

        try:
            while True:
                dados, origem = sock.recvfrom(50)
                ok, ID_decodificado, payload_decodificado = validar(dados)

                if not ok:
                    corrompidos += 1
                    print(f"Corrompido de {origem} —> descartado")
                    continue

                if ID_decodificado <= ultimo:
                    dups += 1
                    print(f"Duplicado -> sequencia={ID_decodificado} de {origem}")
                else:
                    ultimo = ID_decodificado
                    recebidos += 1
                    print(f"sequencia={ID_decodificado:5d} de {origem} | {payload_decodificado[:20]}...")

                sock.sendto(b"ACK", origem)

        except KeyboardInterrupt:
            pass

    print(f"\n[UDP] Fim. recebidos={recebidos} duplicados={dups} corrompidos={corrompidos}")

def main():
    entrada = input(f"\nPorta: ").strip()
    porta = int(entrada)
    proto = int(input("Protocolo (TCP = 1, UDP = 2): "))

    if proto == 1:
        tcp(porta)
    elif proto == 2:
        udp(porta)
    else:
        print("Protocolo inválido.")

if __name__ == "__main__":
    main()