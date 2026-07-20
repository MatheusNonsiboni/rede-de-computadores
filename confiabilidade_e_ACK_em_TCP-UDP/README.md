# Confiabilidade e Retransmissão com ACK sobre TCP e UDP

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Sockets](https://img.shields.io/badge/Sockets-TCP%2FUDP-informational?style=for-the-badge)
![SHA--256](https://img.shields.io/badge/Checksum-SHA--256-blueviolet?style=for-the-badge)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen?style=for-the-badge)

## Descrição

Ferramenta de benchmark que implementa um mecanismo de **confiabilidade sobre a camada de transporte**, comparando na prática como TCP e UDP se comportam sob o mesmo protocolo de aplicação com confirmação (ACK), checksum e retransmissão por timeout. Desenvolvido para a disciplina de **Redes de Computadores**, o projeto envia baterias de 10, 100 e 1000 pacotes por protocolo e mede pacotes perdidos, retransmissões e tempo total de execução — permitindo visualizar de forma concreta a diferença entre um protocolo com confiabilidade nativa (TCP) e um protocolo que precisa de confiabilidade implementada manualmente na aplicação (UDP).

## Conceitos de Computação e Decisões Técnicas

- **Confiabilidade em nível de aplicação com ACK e timeout**: independentemente do protocolo de transporte usado, o emissor só considera um pacote entregue quando recebe de volta os 3 bytes `ACK`. Se o timeout (2s) expirar sem resposta, o pacote é reenviado, até um limite de 10 tentativas (`MAX_RETRY`) — um modelo clássico de *retransmissão por timeout* (stop-and-wait), útil especialmente sobre UDP, que não garante entrega por conta própria.
- **Checksum de integridade com SHA-256**: cada pacote carrega um checksum de 8 bytes, calculado como `sha256(ID + payload)[:8]`. O receptor recalcula o hash sobre os dados recebidos e descarta o pacote (sem confirmar) se não bater — protegendo contra corrupção de dados em trânsito, de forma independente da verificação de integridade que o próprio TCP já faz em nível de transporte.
- **Detecção de duplicatas por número de sequência**: cada pacote carrega um ID de 2 bytes que funciona como número de sequência. O receptor mantém o último número de sequência aceito e descarta (mas ainda confirma com ACK) qualquer pacote com sequência menor ou igual à última recebida — simulando o problema real de ACKs perdidos, onde o emissor reenvia um pacote que na verdade já havia chegado.
- **Framing manual sobre TCP**: como TCP é um protocolo de fluxo contínuo de bytes (sem preservar limites de mensagem), o receptor usa um laço de leitura (`while len(dados) < 50`) para garantir que sempre acumula exatamente os 50 bytes de um pacote completo antes de processá-lo, mesmo que o SO entregue os dados fragmentados em pedaços menores.
- **TCP vs. UDP no mesmo protocolo de aplicação**: optou-se por implementar a mesma lógica de ACK/checksum/sequência rodando sobre os dois protocolos de transporte, isolando a variável de interesse do experimento — assim as baterias de teste mostram a diferença de desempenho e overhead entre um transporte orientado a conexão e um transporte não orientado a conexão sob as mesmas condições.
- **Empacotamento binário determinístico**: o pacote é montado com `int.to_bytes`/`from_bytes` para o ID (garantindo tamanho fixo de 2 bytes, *big-endian*) e um payload truncado para exatamente 40 bytes, resultando em um pacote de tamanho fixo (50 bytes) — o que simplifica tanto o framing em TCP quanto a leitura em UDP (`recvfrom(50)`).

## Tecnologias Utilizadas

**Linguagens**
- Python 3

**Bibliotecas**
- `socket` (nativa) — comunicação via TCP (`SOCK_STREAM`) e UDP (`SOCK_DGRAM`)
- `hashlib` (nativa) — cálculo do checksum SHA-256 dos pacotes
- `time` (nativa) — medição do tempo de execução de cada bateria

**Protocolos**
- TCP/IP e UDP/IP

## Funcionalidades

- **Envio em baterias configuráveis** (10, 100 e 1000 pacotes) para os dois protocolos, com relatório comparativo ao final de cada execução.
- **Confirmação por ACK** com retransmissão automática em caso de timeout (até 10 tentativas por pacote).
- **Verificação de integridade** via checksum SHA-256, com descarte de pacotes corrompidos no receptor.
- **Detecção de pacotes duplicados**, com contagem separada de recebidos, duplicados e corrompidos.
- **Relatório de desempenho por bateria**: pacotes perdidos, número de retransmissões, total de pacotes trafegados (dados + retransmissões + ACKs) e tempo de execução.
- **Escolha interativa de protocolo** (TCP ou UDP) tanto no emissor quanto no receptor, via terminal.

### Fluxograma do sistema

O projeto inclui um fluxograma completo (`_Fluxograma.pdf`) detalhando a lógica de cada função, tanto do lado de quem envia quanto de quem recebe:

![Fluxograma do sistema — lado do envio, detalhando montar_pacote, enviar_com_ack, rodar_tcp e rodar_udp](fluxograma_envio.png)

![Fluxograma do sistema — lado do recebimento, detalhando as funções tcp, udp e validar](fluxograma_recebimento.png)

### Exemplo de execução

**Lado de quem envia (`enviar.py`), via TCP:**

```
IP: 127.0.0.1
Porta: 6001
Protocolo (TCP = 1, UDP = 2): 1

Protocolo: TCP | 127.0.0.1:6001 | timeout=2s | retransmitir=10

  Bateria 10 envios... ok.
  Bateria 100 envios... ok.
  Bateria 1000 envios... ok.


RESULTADOS PARA PROTOCOLO TCP


  Envios |   Perdidos |  Retrans |  Total pkts |  Tempo(s)


      10 |          0 |        0 |          20 |     0.009
     100 |          0 |        0 |         200 |     0.008
    1000 |          0 |        0 |        2000 |     0.041



CONTABILIDADE FINAL (TCP)
Total de pacotes (dados + retransmissões + ACKs): 2220
```

**Lado de quem recebe (`receber.py`), via TCP:**

```
[TCP] Aguardando na porta 6001...
[TCP] Conectado: ('127.0.0.1', 49668)

sequencia=    1 | teste.redes.2026*tes...
sequencia=    2 | teste.redes.2026*tes...
...
sequencia=   10 | teste.redes.2026*tes...
[TCP] Conexão encerrada. recebidos=10 duplicados=0 corrompidos=0

[TCP] Aguardando próxima conexão...
[TCP] Conectado: ('127.0.0.1', 49674)
...
```

## Instalação e Execução

### Pré-requisitos

- **Python 3** instalado (não há dependências externas — o projeto usa apenas bibliotecas nativas: `socket`, `hashlib` e `time`).

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/confiabilidade-ack-tcp-udp.git
cd confiabilidade-ack-tcp-udp/codigos
```

### 2. Instalar dependências

Não há dependências para instalar — todas as bibliotecas usadas já vêm com o Python.

### 3. Executar

O receptor precisa estar rodando **antes** do emissor iniciar o envio. Abra dois terminais:

**Terminal 1 — iniciar o receptor:**

```bash
python3 receber.py
```

Será solicitada a porta em que vai escutar (ex: `6001`) e o protocolo (`1` para TCP, `2` para UDP).

**Terminal 2 — iniciar o emissor:**

```bash
python3 enviar.py
```

Serão solicitados o IP do receptor (use `127.0.0.1` se estiver testando na mesma máquina), a porta escolhida no receptor e o protocolo (`1` para TCP, `2` para UDP — **deve ser o mesmo escolhido no receptor**).

O emissor então dispara automaticamente as três baterias de teste (10, 100 e 1000 pacotes) e imprime o relatório comparativo ao final. Para testar os dois protocolos, repita o processo escolhendo `2` (UDP) em vez de `1` (TCP) nos dois lados.

> **Nota:** o receptor via TCP volta a aguardar uma nova conexão após o emissor encerrar (por isso o emissor abre uma conexão nova para cada bateria de teste). Já o receptor via UDP fica escutando continuamente na mesma porta até ser interrompido com `Ctrl+C`.

## Autores

Essa aplicação foi desenvolvida em conjunto com Marcela de Oliveira Dorigão.
