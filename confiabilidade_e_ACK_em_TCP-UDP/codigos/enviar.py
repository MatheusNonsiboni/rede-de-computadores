import socket
import hashlib
import time

TIMEOUT = 2
MAX_RETRY = 10
BATERIAS = [10, 100, 1000]

def montar_pacote(numero_pacote: int) -> bytes:
    ID = numero_pacote.to_bytes(2, byteorder='big')
    conteudo = "teste.redes.2026*" * 3
    payload = conteudo.encode('utf-8')[:40]
    checksum = hashlib.sha256(ID + payload).digest()[:8]
    pacote = ID + payload + checksum
    assert len(pacote) == 50
    return pacote

def enviar_com_ack(sock, pacote: bytes, destino=None) -> tuple[bool, int]:
    retrans = 0
    for tentativa in range(1, MAX_RETRY + 1):
        try:
            if destino:
                sock.sendto(pacote, destino)    #UDP
            else:
                sock.sendall(pacote)    #TCP

            ack = sock.recvfrom(3)[0] if destino else sock.recv(3)
            if ack == b"ACK":
                return True, retrans
        except socket.timeout:
            if tentativa < MAX_RETRY:
                retrans += 1
    return False, retrans

def rodar_tcp(ip: str, porta: int, n: int):
    perdidos = retrans = total = 0
    inicio = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, porta))
        sock.settimeout(TIMEOUT)

        for seq in range(1, n + 1):
            ok, r = enviar_com_ack(sock, montar_pacote(seq))
            total += 1 + r  #pacote original + retransmissões
            retrans += r
            if ok:
                total += 1  #ACK recebido
            else:
                perdidos += 1

    return perdidos, retrans, total, time.time() - inicio

def rodar_udp(ip: str, porta: int, n: int):
    perdidos = retrans = total = 0
    destino = (ip, porta)
    inicio = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT)

        for seq in range(1, n + 1):
            ok, r = enviar_com_ack(sock, montar_pacote(seq), destino)
            total += 1 + r
            retrans += r
            if ok:
                total += 1
            else:
                perdidos += 1

    return perdidos, retrans, total, time.time() - inicio


def main():
    ip = input("\nIP: ")
    porta = int(input("Porta: "))
    proto = int(input("Protocolo (TCP = 1, UDP = 2): "))
    nome = "TCP" if proto == 1 else "UDP"
    fn = rodar_tcp if proto == 1 else rodar_udp

    print(f"\nProtocolo: {nome} | {ip}:{porta} | timeout={TIMEOUT}s | retransmitir={MAX_RETRY}\n")

    resultados = []
    for n in BATERIAS:
        print(f"  Bateria {n} envios...", end=" ", flush=True)
        res = fn(ip, porta, n)
        resultados.append((n, *res))
        print("ok.")

    print(f"\n")
    print(f"RESULTADOS PARA PROTOCOLO {nome}")
    print(f"\n")
    print(f"{'Envios':>8} | {'Perdidos':>10} | {'Retrans':>8} | {'Total pkts':>11} | {'Tempo(s)':>9}")
    print(f"\n")
    for n, perdidos, retrans, total, tempo in resultados:
        print(f"{n:>8} | {perdidos:>10} | {retrans:>8} | {total:>11} | {tempo:>9.3f}")
    print(f"\n")

    total_geral = sum(r[3] for r in resultados)
    print(f"\nCONTABILIDADE FINAL ({nome})")
    print(f"Total de pacotes (dados + retransmissões + ACKs): {total_geral}")


if __name__ == "__main__":
    main()
