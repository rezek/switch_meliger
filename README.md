# Switch Meliger

Sistema de automação de switches Cisco via interface web.
Permite configurar VLANs e hostname, realizar backup da configuração e validar divergências.
---

## Descrição Geral

O **Switch Meligger** é composto por:

| Camada | Arquivo | Responsabilidade |
|---|---|---|
| Frontend | `templates/index.html` | Interface web |
| Backend | `app.py` | API REST Flask (8 endpoints) |
| Automação | `network_manager.py` | Netmiko (SSH real) + switch simulado |

### Funcionalidades

- **Conexão SSH** com switch Cisco real via Netmiko, ou **modo simulação** (switch simulado em memória)
- **Configuração de VLANs** com ID e nome editáveis (padrão: 10/20/50)
- **Configuração de hostname**
- **Salvar na NVRAM** execução do comando (`write memory`) para salvar a config atual.
- **Backup** da running-config em arquivo local: `backup_<hostname>_<YYYYMMDD_HHMMSS>.txt`
- **Validação** com detecção e exibição de divergências (hostname e VLANs)
- **Terminal** integrado com log colorido em tempo real
- **Alerta visual** no topo da tela quando divergências são detectadas

---

## Instalação e Execução

### Pré-requisitos

- Python 3.10 ou superior
- pip

### Passo a passo

```bash
# 1. Clonar / entrar na pasta
git clone <repo-url>
cd switch-meliger

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar
python app.py
```

Acesse **http://localhost:5000** no navegador.

---

## Como Usar o Frontend

### 1. Conexão

| Campo | Descrição |
|---|---|
| Host / IP | Endereço IP de gerência do switch |
| Usuário | Usuário SSH do switch |
| Senha | Senha do usuário SSH |
| Tipo de Acesso | SSH ou Telnet |
| Modo Simulação | ✅ Marcado = inicia simulação em memória ignorando os dados preenchidos |

Clique em **CONECTAR**. O badge no topo indicará quando conectado.

### 2. Configurar VLANs

As VLANs padrão já aparecem preenchidas:

| VLAN ID | Nome |
|---|---|
| 10 | VLAN_DADOS |
| 20 | VLAN_VOZ |
| 50 | VLAN_SEGURANCA |

- Use **+ ADICIONAR** para incluir novas VLANs
- Clique em **✕** para remover VLANs adicionadas

### 3. Configurar Hostname

Preencha o campo **Nome do Switch** na sidebar (ex: `SW-CORE-01`).

### 4. Aplicar

Clique em **▶ APLICAR**. O sistema irá:
1. Enviar os comandos de configuração ao switch
2. Exibir cada comando no terminal

### 5. Validar

Clique em **✅ VALIDAR** para comparar o estado atual do switch com a configuração desejada.

- Se tudo estiver correto: banner **verde** com confirmação
- Se houver divergências: banner **vermelho** com alerta no topo da tela, listando cada divergência com severidade (`critical` ou `warning`)

### 6. Salvar NVRAM

Clique em **✏️ SALVAR NVRAM** para copyar a running-config para NVRAM do switch, garantindo configuração persistente.
O comando usado é `write memory`.

### 7. Backup

Clique em **💾 BACKUP** para salvar a running-config localmente.
O arquivo é gravado em `backups/backup_<hostname>_<timestamp>.txt`.
Ao gerar um backup, na aba BACKUPS, é exibida a opção para baixar o arquivo .txt.

### 8. Ver VLANs

Clique em **📋 VER VLANs** para exibir a tabela de VLANs atuais do switch.
O comando usado é `show vlan brief`.

---

## API REST

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/connect` | Conectar ao switch |
| `POST` | `/api/disconnect` | Desconectar |
| `GET` | `/api/status` | Status da conexão |
| `POST` | `/api/configure` | Aplicar VLANs e hostname |
| `POST` | `/api/backup` | Realizar backup |
| `POST` | `/api/validate` | Validar configuração |
| `GET` | `/api/vlans` | Listar VLANs do switch |
| `GET` | `/api/logs` | Logs recentes |

---

## Notas de Implementação

- **Modo simulação**: o `SimulatedSwitch` emula um switch IOS em memória, processando os mesmos comandos Cisco reais. Ideal para desenvolvimento e demonstrações sem hardware.
- **Validação**: usa `show vlan brief` para verificar IDs e nomes de VLANs, e o prompt do switch para verificar o hostname.
- **Backup**: além do `.txt`, um arquivo `_meta.json` com metadados (hostname, timestamp, tamanho) é salvo no mesmo diretório.
- **Nome**: é uma brincadeira com palavra MANAGER.
