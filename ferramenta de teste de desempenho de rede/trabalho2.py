import socket
import struct
import time
import threading

DURACAO = 20
NUM_SOCKETS = 4
PORTA = 5000
TAM_PACOTE = 500
STRING_BASE = "teste de rede 2026"

BUF_SIZE = 4 * 1024 * 1024
LOTE = 64     

def fmt_milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")

def fmt_bits(bps: float) -> str:
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.2f} Kbps"
    return f"{bps:.2f} bps"

def montar_pacote(sid: int, seq: int) -> bytes:
    header = struct.pack(">BI", sid, seq)
    payload = (STRING_BASE * 30).encode()[:495]
    return header + payload

def montar_lote(sid: int, seq_inicio: int, n: int) -> bytes:
    partes = []
    for i in range(n):
        partes.append(montar_pacote(sid, seq_inicio + i))
    return b"".join(partes)

class Contadores:
    def __init__(self):
        self._lock = threading.Lock()
        self.enviados = 0
        self.bytes_tx = 0

    def add(self, enviados=0, bytes_tx=0):
        with self._lock:
            self.enviados += enviados
            self.bytes_tx += bytes_tx

class ContadoresRx:
    def __init__(self):
        self._lock = threading.Lock()
        self.recebidos = 0
        self.perdidos = 0
        self.bytes_rx = 0

    def add(self, recebidos=0, perdidos=0, bytes_rx=0):
        with self._lock:
            self.recebidos += recebidos
            self.perdidos += perdidos
            self.bytes_rx += bytes_rx

def _worker_tcp(sid: int, ip: str, porta: int, fim: float, cnt: Contadores):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUF_SIZE)
            s.connect((ip, porta))
            seq = 0
            while time.time() < fim:
                lote = montar_lote(sid, seq, LOTE)
                s.sendall(lote)
                cnt.add(enviados=LOTE, bytes_tx=len(lote))
                seq += LOTE
    except Exception:
        pass

def _worker_udp(sid: int, ip: str, porta: int, fim: float, cnt: Contadores):
    destino = (ip, porta)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUF_SIZE)
            seq = 0
            while time.time() < fim:
                pacote = montar_pacote(sid, seq)
                s.sendto(pacote, destino)
                cnt.add(enviados=1, bytes_tx=TAM_PACOTE)
                seq += 1
    except Exception:
        pass

def modo_sender(ip: str, porta: int, proto: int):
    nome = "TCP" if proto == 1 else "UDP"
    worker = _worker_tcp if proto == 1 else _worker_udp

    print(f"\n[{nome}] Sender → {ip}:{porta}\n")

    cnt = Contadores()
    fim = time.time() + DURACAO
    inicio = time.time()

    threads = [threading.Thread(target=worker, args=(sid, ip, porta, fim, cnt), daemon=True)
               for sid in range(NUM_SOCKETS)]
    for t in threads: t.start()
    for t in threads: t.join()

    duracao = time.time() - inicio
    bps = (cnt.bytes_tx * 8) / duracao
    pps = cnt.enviados / duracao
    print("\n")
    print(f"  RELATÓRIO {nome}")
    print("\n")
    print(f"Pacotes enviados: {fmt_milhar(cnt.enviados)}")
    print(f"Bytes trafegados: {fmt_milhar(cnt.bytes_tx)}")
    print(f"Velocidade (pkt/s): {fmt_milhar(int(pps))}")
    print(f"Velocidade (bit/s): {fmt_bits(bps)}")
    print(f"Duração real: {duracao:.3f} s")

def _sessao_tcp_rx(conn: socket.socket, cnt: ContadoresRx, fim_event: threading.Event):
    ultimo: dict[int, int] = {}
    buf = b""
    try:
        conn.settimeout(2.0)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUF_SIZE)
        while not fim_event.is_set():
            try:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= TAM_PACOTE:
                    pacote = buf[:TAM_PACOTE]
                    buf = buf[TAM_PACOTE:]
                    sid, seq = struct.unpack(">BI", pacote[:5])
                    ant = ultimo.get(sid, -1)
                    perdidos = max(0, seq - ant - 1)
                    cnt.add(recebidos=1, perdidos=perdidos, bytes_rx=TAM_PACOTE)
                    ultimo[sid] = seq
            except socket.timeout:
                continue
    except Exception:
        pass
    finally:
        conn.close()

def modo_receiver_tcp(porta: int):
    cnt = ContadoresRx()
    fim_event = threading.Event()
    inicio = None

    print(f"\n[TCP] Receiver escutando na porta {porta}...\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUF_SIZE)
        srv.bind(("0.0.0.0", porta))
        srv.listen(NUM_SOCKETS * 2)
        srv.settimeout(2.0)

        sessoes = []
        try:
            while not fim_event.is_set():
                try:
                    conn, addr = srv.accept()
                    if inicio is None:
                        inicio = time.time()
                        def _timer():
                            time.sleep(DURACAO + 3)
                            fim_event.set()
                        threading.Thread(target=_timer, daemon=True).start()
                    print(f"Conexão de {addr}")
                    t = threading.Thread(target=_sessao_tcp_rx,
                                        args=(conn, cnt, fim_event), daemon=True)
                    t.start()
                    sessoes.append(t)
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            fim_event.set()

    for t in sessoes:
        t.join(timeout=3)

    duracao = time.time() - (inicio or time.time())
    _relatorio_rx(cnt, "TCP", duracao)

def modo_receiver_udp(porta: int):
    cnt = ContadoresRx()
    fim_event = threading.Event()
    inicio = None
    ultimo: dict[int, int] = {}

    print(f"\n[UDP] Receiver escutando na porta {porta}...\n")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUF_SIZE)
        s.bind(("0.0.0.0", porta))
        s.settimeout(1.0)

        try:
            while not fim_event.is_set():
                try:
                    dados, _ = s.recvfrom(TAM_PACOTE + 10)
                    if len(dados) != TAM_PACOTE:
                        continue

                    if inicio is None:
                        inicio = time.time()
                        def _timer():
                            time.sleep(DURACAO + 3)
                            fim_event.set()
                        threading.Thread(target=_timer, daemon=True).start()

                    sid, seq = struct.unpack(">BI", dados[:5])
                    ant = ultimo.get(sid, -1)
                    perdidos = max(0, seq - ant - 1)
                    cnt.add(recebidos=1, perdidos=perdidos, bytes_rx=TAM_PACOTE)
                    ultimo[sid] = seq

                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            fim_event.set()

    duracao = time.time() - (inicio or time.time())
    _relatorio_rx(cnt, "UDP", duracao)

def _relatorio_rx(cnt: ContadoresRx, proto: str, duracao: float):
    total = cnt.recebidos + cnt.perdidos
    perda_pct = (cnt.perdidos / total * 100) if total > 0 else 0.0
    bps = (cnt.bytes_rx * 8) / duracao if duracao > 0 else 0
    pps = cnt.recebidos / duracao if duracao > 0 else 0

    print("\n")
    print(f"   RELATÓRIO {proto}")
    print("\n")
    print(f"Pacotes recebidos: {fmt_milhar(cnt.recebidos)}")
    print(f"Pacotes perdidos: {fmt_milhar(cnt.perdidos)}  ({perda_pct:.2f}%)")
    print(f"Bytes trafegados: {fmt_milhar(cnt.bytes_rx)}")
    print(f"Velocidade (pkt/s): {fmt_milhar(int(pps))}")
    print(f"Velocidade (bit/s): {fmt_bits(bps)}")
    print(f"Duração real: {duracao:.3f} s")

def main():
    print(f"\nFERRAMENTA DE TESTE DE DESEMPENHO DE REDE")
    print(f"Sockets paralelos: {NUM_SOCKETS} | Duração: {DURACAO}s | Pacote: {TAM_PACOTE} bytes\n")

    try:
        proto = int(input("Protocolo (TCP=1, UDP=2): ").strip())
        if proto not in (1, 2):
            raise ValueError
    except ValueError:
        print("Protocolo inválido.")
        return

    porta = int(input("Porta: ").strip())
    papel = input("Este nó vai (S)ender ou (R)eceiver? ").strip().upper()

    if papel == "S":
        ip = input("IP do destino: ").strip()
        modo_sender(ip, porta, proto)
    elif papel == "R":
        if proto == 1:
            modo_receiver_tcp(porta)
        else:
            modo_receiver_udp(porta)
    else:
        print("Opção inválida. Use S ou R.")

if __name__ == "__main__":
    main()
