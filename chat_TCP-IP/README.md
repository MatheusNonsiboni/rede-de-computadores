# Chat TCP/IP com Threading

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Sockets](https://img.shields.io/badge/Sockets-TCP%2FIP-informational?style=for-the-badge)
![Threading](https://img.shields.io/badge/Threading-Concurrent-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen?style=for-the-badge)

## Descrição

Chat bidirecional em tempo real entre dois processos (servidor e cliente), desenvolvido para a disciplina de **Redes de Computadores**. O projeto implementa comunicação full-duplex sobre TCP/IP: cada ponta consegue enviar e receber mensagens simultaneamente, sem que o envio bloqueie o recebimento (e vice-versa), graças ao uso de uma thread dedicada para escuta em cada processo.

## Conceitos de Computação e Decisões Técnicas

- **Sockets TCP (`SOCK_STREAM`)**: optou-se pelo protocolo TCP em vez de UDP para garantir entrega confiável e ordenada das mensagens digitadas, sem se preocupar com perda ou reordenação de pacotes — características essenciais para uma conversa legível.
- **Arquitetura cliente-servidor**: o servidor abre um socket, faz `bind` em uma porta e fica em `listen`/`accept` aguardando conexão; o cliente inicia a conversa com `connect`. É o modelo mais direto para uma comunicação ponto a ponto entre duas máquinas.
- **Multithreading para comunicação full-duplex**: como `input()` (para digitar) e `socket.recv()` (para receber) são ambas operações bloqueantes, uma única thread não consegue fazer as duas ao mesmo tempo. A solução foi rodar `receber_mensagem()` em uma **thread separada e daemon**, enquanto a thread principal cuida da leitura do teclado e do envio — assim, uma mensagem pode chegar a qualquer momento sem travar a digitação, e vice-versa.
- **Sincronização entre threads com `join(timeout=...)`**: como a thread receptora roda em paralelo, ela pode não ter processado a última mensagem (nem incrementado o contador de pacotes) no exato instante em que a thread principal decide encerrar o programa. Por isso, antes de fechar a conexão e exibir o relatório final, a thread principal aguarda a thread receptora com `join(timeout=2)` — dando a ela a chance de terminar o processamento pendente, mas sem travar indefinidamente caso a outra ponta já tenha desconectado.
- **`SO_REUSEADDR` no servidor**: evita o erro `Address already in use` ao reiniciar o servidor rapidamente na mesma porta (comum durante testes), já que sem essa opção o sistema operacional mantém a porta reservada por um tempo após o encerramento do processo anterior.
- **Threads `daemon=True`**: garantem que, se o processo principal terminar, a thread de escuta não impeça o programa de encerrar (ela é finalizada junto, sem precisar de tratamento explícito de shutdown).

## Tecnologias Utilizadas

**Linguagens**
- Python 3

**Bibliotecas**
- `socket` (nativa) — criação e gerenciamento das conexões TCP
- `threading` (nativa) — execução concorrente do envio e recebimento de mensagens

**Protocolos**
- TCP/IP

## Funcionalidades

- Comunicação **bidirecional em tempo real**: é possível enviar e receber mensagens simultaneamente, sem que uma ação bloqueie a outra.
- **Configuração interativa** de porta (servidor) e IP/porta de destino (cliente) via terminal, sem necessidade de editar o código.
- **Comando de encerramento** (`sair`): ao ser digitado por qualquer uma das partes, encerra o chat dos dois lados de forma coordenada.
- **Detecção de desconexão**: se uma ponta perde a conexão sem avisar (`recv()` retorna vazio), a outra ponta é avisada no terminal (`"Cliente desconectou"`).
- **Relatório final de pacotes**: ao encerrar, cada processo exibe um resumo com a quantidade de pacotes enviados, recebidos e o total trafegado na sessão.

### Exemplo de execução

Cenário: cliente envia "Oi servidor", servidor responde "Oi cliente", cliente digita `sair` primeiro, servidor digita `sair` em seguida.

**Lado do servidor:**

```
SERVIDOR DE CHAT TCP/IP

Digite a porta TCP do servidor: 5000

Aguardando conexão na porta 5000...

Cliente conectado: 127.0.0.1:51502
Envie uma mensagem
Digite 'sair' para encerrar o chat
Você: 
Cliente: Oi servidor
Você: Oi cliente
Cliente: sair

RELATÓRIO FINAL
Pacotes enviados: 1
Pacotes recebidos: 2
Total: 3
Cliente encerrou o chat
Você: sair

RELATÓRIO FINAL
Pacotes enviados: 2
Pacotes recebidos: 2
Total: 4
Servidor encerrado
```

**Lado do cliente:**

```
CLIENTE DE CHAT TCP/IP

Digite o IP do servidor: 127.0.0.1
Digite a porta TCP: 5000

Conectando em 127.0.0.1:5000...
Conectado! Envie uma mensagem

Digite 'sair' para encerrar o chat
Você: Oi servidor
Você: sair
Servidor: Oi cliente
Servidor: sair

RELATÓRIO FINAL
Pacotes enviados: 2
Pacotes recebidos: 2
Total: 4
Cliente encerrado
```

> **Nota:** repare que o relatório aparece **duas vezes** no lado que recebe o "sair" primeiro. Isso acontece porque `exibir_relatorio()` é chamada tanto de dentro da thread receptora (assim que ela identifica a mensagem "sair" vinda da outra ponta) quanto no final do script principal (quando o próprio usuário digita "sair" para sair do seu loop de envio). Não chega a ser um bug — os números batem certinho nas duas chamadas — mas é uma duplicação de saída que vale sua atenção caso queira deixar o encerramento mais "limpo" no futuro.

## Instalação e Execução

### Pré-requisitos

- **Python 3** instalado (não há dependências externas — o projeto usa apenas bibliotecas nativas da linguagem).

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/chat-tcp-ip.git
cd chat-tcp-ip
```

### 2. Instalar dependências

Não há dependências para instalar — `socket` e `threading` já vêm com o Python.

### 3. Executar

O servidor precisa estar rodando **antes** do cliente tentar se conectar. Abra dois terminais:

**Terminal 1 — iniciar o servidor:**

```bash
python3 serverThreading.py
```

Será solicitada a porta em que o servidor vai escutar (ex: `5000`).

**Terminal 2 — iniciar o cliente:**

```bash
python3 clientThreading.py
```

Serão solicitados o IP do servidor (use `127.0.0.1` se estiver testando na mesma máquina) e a mesma porta escolhida no servidor.

A partir daí, basta digitar mensagens em qualquer um dos dois terminais e pressionar Enter para enviá-las. Digite `sair` em qualquer lado para encerrar a conversa nos dois processos.
