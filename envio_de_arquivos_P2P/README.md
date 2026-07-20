# Transferência P2P de Arquivos com Verificação de Integridade

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Sockets](https://img.shields.io/badge/Sockets-TCP%2FUDP-informational?style=for-the-badge)
![P2P](https://img.shields.io/badge/Arquitetura-P2P-8A2BE2?style=for-the-badge)
![SHA--256](https://img.shields.io/badge/Checksum-SHA--256-critical?style=for-the-badge)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen?style=for-the-badge)

## Descrição

Aplicação para transferência de arquivos binários entre dois computadores em arquitetura **ponto a ponto (P2P)**, sem servidor central: qualquer uma das duas pontas pode iniciar o envio. Desenvolvido para a disciplina de **Redes de Computadores** (UEL), o projeto implementa confiabilidade sobre TCP e UDP com confirmação por ACK, retransmissão automática em caso de perda de pacote e verificação de integridade fim a fim via hash SHA-256, comparando o comportamento dos dois protocolos sob diferentes tamanhos de bloco.

## Conceitos de Computação e Decisões Técnicas

- **Arquitetura P2P sem servidor central**: um único script assume o papel de emissor ou receptor conforme escolha do usuário no início da execução. Isso difere do modelo cliente-servidor tradicional, já que qualquer nó pode iniciar uma transferência para o outro.
- **Confiabilidade em nível de aplicação com ACK e retransmissão por timeout**: cada bloco de dados só é considerado entregue quando o emissor recebe de volta a confirmação `ACK`. Se o timeout (5s) expirar sem resposta — situação típica de perda de pacote em uma rede instável —, o bloco é reenviado, até um limite de 10 tentativas. O sistema contabiliza separadamente blocos lidos do disco e blocos efetivamente confirmados, permitindo identificar perdas mesmo quando a retransmissão resolve o problema.
- **Verificação de integridade fim a fim com SHA-256**: o emissor calcula o hash do arquivo completo antes de iniciar a transferência e o envia junto aos metadados iniciais. O receptor recalcula o hash a partir dos bytes efetivamente gravados em disco e compara com o hash de origem, atestando que a cópia é idêntica ao original, byte a byte.
- **Sinalização de metadados antes da transferência**: antes de enviar os blocos de dados, o emissor transmite um pacote de metadados (nome do arquivo, tamanho total e hash) prefixado por 4 bytes indicando seu tamanho. Isso permite ao receptor alocar corretamente o arquivo de saída e saber exatamente quando a transferência está completa, sem depender de um marcador de fim de arquivo.
- **Leitura em blocos (streaming) em vez de carregar o arquivo inteiro em memória**: tanto a leitura para envio quanto a escrita em disco no receptor são feitas incrementalmente, bloco a bloco, permitindo transferir arquivos maiores que a memória disponível sem carregá-los por completo de uma vez.
- **Framing manual sobre TCP**: como TCP é um protocolo de fluxo contínuo de bytes, sem preservar limites de mensagem, cada bloco enviado por TCP é prefixado por 4 bytes indicando seu tamanho. O receptor usa uma função de leitura em laço (`receber_exato`) que acumula bytes do socket até atingir exatamente o tamanho esperado, independentemente de como o sistema operacional fragmentou a entrega.
- **TCP vs. UDP sobre o mesmo protocolo de aplicação**: a mesma lógica de metadados, ACK e retransmissão roda sobre os dois protocolos de transporte, isolando a variável de interesse do experimento e permitindo comparar diretamente o overhead e a taxa de sucesso de cada um sob as mesmas condições de rede.

## Tecnologias Utilizadas

**Linguagens**
- Python 3

**Bibliotecas**
- `socket` (nativa) — comunicação via TCP (`SOCK_STREAM`) e UDP (`SOCK_DGRAM`)
- `hashlib` (nativa) — cálculo do hash SHA-256 para verificação de integridade
- `struct` (nativa) — empacotamento e desempacotamento binário de metadados e prefixos de tamanho
- `os` (nativa) — resolução de caminhos de arquivo
- `time` (nativa) — medição do tempo de transferência

**Protocolos**
- TCP/IP e UDP/IP

## Funcionalidades

- **Transferência de arquivos binários** de qualquer tipo (imagens, PDFs, executáveis, etc.) entre dois nós, sem necessidade de um servidor intermediário.
- **Escolha de papel interativa**: cada execução do script pergunta se aquele nó vai enviar ou receber, e qual protocolo (TCP ou UDP) utilizar.
- **Tamanho de bloco configurável** pelo usuário no momento do envio (500, 1000 ou 1500 bytes), permitindo comparar o desempenho da transferência sob diferentes granularidades.
- **Múltiplas baterias de teste em uma única sessão**: o emissor pode repetir o envio do mesmo arquivo com tamanhos de bloco diferentes sem reiniciar o programa, consolidando um relatório comparativo ao final.
- **Confirmação por ACK com retransmissão automática**, contabilizando blocos lidos versus blocos efetivamente confirmados em cada bateria.
- **Verificação de integridade automática** via SHA-256, comparando o hash do arquivo original com o hash do arquivo recebido e reportando o resultado (`INTEGRIDADE_OK` ou `INTEGRIDADE_FALHOU`).
- **Relatórios de execução detalhados** em ambos os lados (origem e destino), com contagem de blocos, tempo de transferência e velocidade média em bit/s, com formatação numérica de milhar e decimal (ex: `7.000,00`).
- **Modo de recepção contínuo**: o nó receptor permanece disponível para aceitar novas transferências após concluir a anterior, sem precisar ser reiniciado.

### Exemplo de execução

Resultado de uma bateria de testes real, transferindo um arquivo de 16.061 bytes via TCP e UDP, com blocos de 500, 1000 e 1500 bytes:

**Relatório de recepção (TCP, bloco de 1000 bytes):**

```
RELATORIO DE RECEPCAO — DESTINO — PROTOCOLO TCP
Arquivo salvo: C:\Users\marod\Downloads\recebido_longday.jpg
Tamanho total: 16.061 bytes
Blocos recebidos: 17
Blocos gravados: 17
Tempo de recepcao: 3.982 s
Velocidade media: 32.269,77 bit/s
Hash origem: e99da5beb74b82d66ec33cb05172e0400ce75601f853b062bc508c790ce5e121
Hash destino: e99da5beb74b82d66ec33cb05172e0400ce75601f853b062bc508c790ce5e121
Integridade: INTEGRIDADE_OK
```

**Relatório final de execução consolidando as três baterias (TCP):**

```
RELATORIO DE EXECUCAO — ORIGEM — PROTOCOLO TCP
Arquivo: longday.jpg
Tamanho: 16.061 bytes

 Bloco(B) | Bl.Lidos | Bl.Enviados | Tempo(s) | Veloc.(bit/s) | Integridade
-----------------------------------------------------------------------------
      500 |       33 |          33 |   12.280 |     10.462,00 | OK
    1.000 |       17 |          17 |    4.921 |     26.111,86 | OK
    1.500 |       11 |          11 |    2.938 |     43.739,08 | OK

Total de blocos enviados (todas as baterias): 61
```

O mesmo teste, repetido sobre UDP com os mesmos três tamanhos de bloco, também confirmou integridade em todas as baterias, totalizando seis execuções bem-sucedidas (três em TCP e três em UDP).

## Instalação e Execução

### Pré-requisitos

- **Python 3** instalado (não há dependências externas — o projeto usa apenas bibliotecas nativas: `socket`, `hashlib`, `struct`, `os` e `time`).

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/p2p-transferencia-arquivos.git
cd p2p-transferencia-arquivos
```

### 2. Instalar dependências

Não há dependências para instalar — todas as bibliotecas usadas já vêm com o Python.

### 3. Executar

O arquivo a ser transferido deve estar salvo na **mesma pasta do script** (`p2p.py`) no nó que vai enviá-lo. Como a arquitetura é P2P, o mesmo script é usado nas duas pontas — a diferença está apenas na escolha de papel feita durante a execução.

**No nó que vai receber:**

```bash
python3 p2p.py
```

Responda às perguntas:
- `Protocolo (TCP=1, UDP=2):` — escolha o protocolo desejado.
- `Porta:` — porta em que este nó vai escutar (ex: `5000`).
- `Este nó vai (E)nviar ou (R)eceber?` — digite `R`.

**No nó que vai enviar:**

```bash
python3 p2p.py
```

Responda às perguntas:
- `Protocolo (TCP=1, UDP=2):` — deve ser **o mesmo protocolo** escolhido no receptor.
- `Porta:` — deve ser **a mesma porta** em que o receptor está escutando.
- `Este nó vai (E)nviar ou (R)eceber?` — digite `E`.
- `IP do destino:` — endereço IP da máquina receptora (use `127.0.0.1` se estiver testando na mesma máquina).
- `Nome do arquivo:` — nome do arquivo a ser transferido (deve estar na pasta do script).
- `Tamanho do bloco (500 / 1000 / 1500 bytes):` — tamanho do bloco desejado para essa bateria.
- `Realizar outra bateria? (s/n):` — permite repetir o envio do mesmo arquivo com um tamanho de bloco diferente, útil para comparar desempenho, sem reiniciar o programa.

O arquivo recebido é salvo na pasta do script do receptor com o prefixo `recebido_` (ex: `recebido_longday.jpg`). Ao final de cada bateria, ambos os lados exibem seus respectivos relatórios de execução.
