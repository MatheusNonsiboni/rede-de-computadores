import socket
import hashlib
import os
import struct
import time

TIMEOUT = 5
MAX_RETRY = 10

def fmt(n: float, decimais: int = 2) -> str:
    inteiro = int(n)
    s = f"{inteiro:,}".replace(",", ".")
    if decimais > 0:
        frac = round(abs(n - inteiro), decimais)
        frac_str = f"{frac:.{decimais}f}"[1:]
        s += frac_str.replace(".", ",")
    return s

def montar_metadados(nome: str, tamanho: int, hash_hex: str) -> bytes:
    corpo = f"{nome}|{tamanho}|{hash_hex}".encode("utf-8")
    return struct.pack(">I", len(corpo)) + corpo

def parsear_metadados(dados: bytes) -> tuple[str, int, str]:
    tam = struct.unpack(">I", dados[:4])[0]
    corpo = dados[4:4 + tam].decode("utf-8")
    nome, tamanho, hash_hex = corpo.split("|")
    return nome, int(tamanho), hash_hex

def receber_exato(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionResetError("Conexão encerrada prematuramente.")
        buf += chunk
    return buf

def enviar_bloco_com_ack(sock, bloco: bytes, destino=None) -> bool:
    for _ in range(MAX_RETRY):
        try:
            if destino:
                sock.sendto(bloco, destino)
            else:
                sock.sendall(struct.pack(">I", len(bloco)) + bloco)
            ack = sock.recvfrom(3)[0] if destino else sock.recv(3)
            if ack == b"ACK":
                return True
        except socket.timeout:
            continue
    return False

def _enviar_sessao_tcp(ip, porta, caminho, tam_bloco) -> dict:
    nome_arquivo = os.path.basename(caminho)
    tamanho_total = os.path.getsize(caminho)

    hash_obj = hashlib.sha256()
    with open(caminho, "rb") as f:
        for pedaco in iter(lambda: f.read(tam_bloco), b""):
            hash_obj.update(pedaco)
    hash_hex = hash_obj.hexdigest()

    blocos_lidos = blocos_enviados = 0
    inicio = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, porta))
        sock.settimeout(TIMEOUT)

        sock.sendall(montar_metadados(nome_arquivo, tamanho_total, hash_hex))
        if receber_exato(sock, 3) != b"ACK":
            raise RuntimeError("Receptor não confirmou metadados.")

        with open(caminho, "rb") as f:
            while True:
                bloco = f.read(tam_bloco)
                if not bloco:
                    break
                blocos_lidos += 1
                if enviar_bloco_com_ack(sock, bloco):
                    blocos_enviados += 1

        resultado = receber_exato(sock, 20).decode("utf-8", errors="ignore").strip()

    return {
        "protocolo": "TCP", "nome": nome_arquivo,
        "tamanho_total": tamanho_total, "tam_bloco": tam_bloco,
        "blocos_lidos": blocos_lidos, "blocos_enviados": blocos_enviados,
        "duracao": time.time() - inicio,
        "hash_origem": hash_hex, "integridade": resultado,
    }

def _enviar_sessao_udp(ip, porta, caminho, tam_bloco) -> dict:
    nome_arquivo = os.path.basename(caminho)
    tamanho_total = os.path.getsize(caminho)
    destino = (ip, porta)

    hash_obj = hashlib.sha256()
    with open(caminho, "rb") as f:
        for pedaco in iter(lambda: f.read(tam_bloco), b""):
            hash_obj.update(pedaco)
    hash_hex = hash_obj.hexdigest()

    blocos_lidos = blocos_enviados = 0
    inicio = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.settimeout(TIMEOUT)

        meta = montar_metadados(nome_arquivo, tamanho_total, hash_hex)
        for t in range(MAX_RETRY):
            sock.sendto(meta, destino)
            try:
                if sock.recvfrom(3)[0] == b"ACK":
                    break
            except socket.timeout:
                if t == MAX_RETRY - 1:
                    raise RuntimeError("Receptor não confirmou metadados (UDP).")

        with open(caminho, "rb") as f:
            while True:
                bloco = f.read(tam_bloco)
                if not bloco:
                    break
                blocos_lidos += 1
                if enviar_bloco_com_ack(sock, bloco, destino):
                    blocos_enviados += 1

        try:
            sock.settimeout(3)
            resultado = sock.recvfrom(64)[0].decode("utf-8", errors="ignore").strip()
        except socket.timeout:
            resultado = "TIMEOUT_INTEGRIDADE"

    return {
        "protocolo": "UDP", "nome": nome_arquivo,
        "tamanho_total": tamanho_total, "tam_bloco": tam_bloco,
        "blocos_lidos": blocos_lidos, "blocos_enviados": blocos_enviados,
        "duracao": time.time() - inicio,
        "hash_origem": hash_hex, "integridade": resultado,
    }

def imprimir_relatorio_envio(resultados: list[dict]):
    proto = resultados[0]["protocolo"]
    nome = resultados[0]["nome"]

    print(f"\nRELATORIO DE EXECUCAO — ORIGEM — PROTOCOLO {proto}")
    print(f"Arquivo: {nome}")
    print(f"Tamanho: {fmt(resultados[0]['tamanho_total'], 0)} bytes\n")
    print(f"{'Bloco(B)':>10} | {'Bl.Lidos':>10} | {'Bl.Enviados':>12} | {'Tempo(s)':>10} | {'Veloc.(bit/s)':>15} | Integridade")
    print("-" * 85)

    for r in resultados:
        vel = (r["tamanho_total"] * 8) / r["duracao"] if r["duracao"] > 0 else 0
        status = "OK" if "OK" in r["integridade"] else "FALHOU"
        print(
            f"{fmt(r['tam_bloco'], 0):>10} | "
            f"{fmt(r['blocos_lidos'], 0):>10} | "
            f"{fmt(r['blocos_enviados'], 0):>12} | "
            f"{r['duracao']:>10.3f} | "
            f"{fmt(vel):>15} | "
            f"{status}"
        )

    total = sum(r["blocos_enviados"] for r in resultados)
    print(f"\nTotal de blocos enviados (todas as baterias): {fmt(total, 0)}\n")

def modo_envio(ip, porta, proto):
    fn_sessao = _enviar_sessao_tcp if proto == 1 else _enviar_sessao_udp

    nome = input("\nNome do arquivo: ").strip()
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome)
    if not os.path.isfile(caminho):
        print("Arquivo não encontrado na pasta do script.")
        return

    resultados = []
    bateria = 1

    while True:
        tam_raw = input(f"\n[Bateria {bateria}] Tamanho do bloco (500 / 1000 / 1500 bytes): ").strip()
        try:
            tam_bloco = int(tam_raw)
            if tam_bloco not in (500, 1000, 1500):
                print("Valor invalido. Use 500, 1000 ou 1500.")
                continue
        except ValueError:
            print("Digite um numero.")
            continue

        print(f"Enviando com bloco de {fmt(tam_bloco, 0)} bytes...", end=" ", flush=True)
        try:
            res = fn_sessao(ip, porta, caminho, tam_bloco)
            resultados.append(res)
            print("concluido.")
        except Exception as e:
            print(f"\nErro: {e}")

        continuar = input("\nRealizar outra bateria? (s/n): ").strip().lower()
        if continuar != "s":
            break
        bateria += 1

    if resultados:
        imprimir_relatorio_envio(resultados)

def _receber_sessao_tcp(conn) -> dict:
    tam_prefixo = struct.unpack(">I", receber_exato(conn, 4))[0]
    corpo = receber_exato(conn, tam_prefixo).decode("utf-8")
    nome, tamanho_total, hash_origem = corpo.split("|")
    tamanho_total = int(tamanho_total)

    print(f"\nArquivo: {nome}")
    print(f"Tamanho: {fmt(tamanho_total, 0)} bytes")
    conn.sendall(b"ACK")

    nome_saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recebido_" + nome)
    hash_destino = hashlib.sha256()
    blocos_recebidos = blocos_gravados = bytes_recebidos = 0
    inicio = time.time()

    with open(nome_saida, "wb") as f:
        while bytes_recebidos < tamanho_total:
            tam_bloco = struct.unpack(">I", receber_exato(conn, 4))[0]
            bloco = receber_exato(conn, tam_bloco)
            blocos_recebidos += 1
            f.write(bloco)
            hash_destino.update(bloco)
            bytes_recebidos += len(bloco)
            blocos_gravados += 1
            conn.sendall(b"ACK")
            print(f"bloco {blocos_recebidos:>6,} | {bytes_recebidos:>12,} / {tamanho_total:>12,} bytes")

    hash_final = hash_destino.hexdigest()
    status = "INTEGRIDADE_OK" if hash_final == hash_origem else "INTEGRIDADE_FALHOU"
    duracao = time.time() - inicio
    conn.sendall(status.ljust(20).encode("utf-8"))

    return {
        "nome": nome_saida, "tamanho_total": tamanho_total,
        "blocos_recebidos": blocos_recebidos, "blocos_gravados": blocos_gravados,
        "hash_origem": hash_origem, "hash_destino": hash_final,
        "integridade": status, "duracao": duracao,
    }

def _receber_sessao_udp(sock) -> dict:
    while True:
        dados, origem = sock.recvfrom(65536)
        try:
            nome, tamanho_total, hash_origem = parsear_metadados(dados)
            break
        except Exception:
            continue

    print(f"\nArquivo: {nome}")
    print(f"Tamanho: {fmt(tamanho_total, 0)} bytes")
    sock.sendto(b"ACK", origem)

    nome_saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recebido_" + nome)
    hash_destino = hashlib.sha256()
    blocos_recebidos = blocos_gravados = bytes_recebidos = 0
    inicio = time.time()

    with open(nome_saida, "wb") as f:
        while bytes_recebidos < tamanho_total:
            bloco, origem = sock.recvfrom(65536)
            blocos_recebidos += 1
            f.write(bloco)
            hash_destino.update(bloco)
            bytes_recebidos += len(bloco)
            blocos_gravados += 1
            sock.sendto(b"ACK", origem)
            print(f"bloco {blocos_recebidos:>6,} | {bytes_recebidos:>12,} / {tamanho_total:>12,} bytes")

    hash_final = hash_destino.hexdigest()
    status = "INTEGRIDADE_OK" if hash_final == hash_origem else "INTEGRIDADE_FALHOU"
    duracao = time.time() - inicio
    sock.sendto(status.encode("utf-8"), origem)

    return {
        "nome": nome_saida, "tamanho_total": tamanho_total,
        "blocos_recebidos": blocos_recebidos, "blocos_gravados": blocos_gravados,
        "hash_origem": hash_origem, "hash_destino": hash_final,
        "integridade": status, "duracao": duracao,
    }

def imprimir_relatorio_recepcao(resultado: dict, proto: str):
    bits = resultado["tamanho_total"] * 8
    vel = bits / resultado["duracao"] if resultado["duracao"] > 0 else 0

    print(f"\nRELATORIO DE RECEPCAO — DESTINO — PROTOCOLO {proto}")
    print(f"Arquivo salvo: {resultado['nome']}")
    print(f"Tamanho total: {fmt(resultado['tamanho_total'], 0)} bytes")
    print(f"Blocos recebidos: {fmt(resultado['blocos_recebidos'], 0)}")
    print(f"Blocos gravados: {fmt(resultado['blocos_gravados'], 0)}")
    print(f"Tempo de recepcao: {resultado['duracao']:.3f} s")
    print(f"Velocidade media: {fmt(vel)} bit/s")
    print(f"Hash origem: {resultado['hash_origem']}")
    print(f"Hash destino: {resultado['hash_destino']}")
    print(f"Integridade: {resultado['integridade']}\n")

def modo_recepcao(porta, proto):
    nome_proto = "TCP" if proto == 1 else "UDP"

    if proto == 1:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", porta))
            srv.listen(1)
            print(f"\n[{nome_proto}] Aguardando conexoes na porta {porta}...")

            try:
                while True:
                    conn, addr = srv.accept()
                    print(f"Conexao de: {addr}")
                    with conn:
                        resultado = _receber_sessao_tcp(conn)
                    imprimir_relatorio_recepcao(resultado, nome_proto)
                    print(f"[{nome_proto}] Aguardando proxima bateria...\n")
            except KeyboardInterrupt:
                print(f"\n[{nome_proto}] Encerrado.")
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.bind(("0.0.0.0", porta))
            print(f"\n[{nome_proto}] Aguardando datagramas na porta {porta}...")

            try:
                while True:
                    resultado = _receber_sessao_udp(sock)
                    imprimir_relatorio_recepcao(resultado, nome_proto)
                    print(f"[{nome_proto}] Aguardando proxima bateria...\n")
            except KeyboardInterrupt:
                print(f"\n[{nome_proto}] Encerrado.")

def main():
    print("\nTRANSFERÊNCIA P2P DE ARQUIVOS\n")

    try:
        proto = int(input("Protocolo (TCP=1, UDP=2): ").strip())
        if proto not in (1, 2):
            raise ValueError
    except ValueError:
        print("Protocolo invalido.")
        return

    porta = int(input("Porta: ").strip())
    papel = input("Este no vai (E)nviar ou (R)eceber? ").strip().upper()

    if papel == "E":
        ip = input("IP do destino: ").strip()
        modo_envio(ip, porta, proto)
    elif papel == "R":
        modo_recepcao(porta, proto)
    else:
        print("Opcao invalida. Use E ou R.")

if __name__ == "__main__":
    main()