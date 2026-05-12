# Plano de Automação: VPN IPSec entre Fortigate e Palo Alto

> **Versão:** 1.0 | **Data:** Maio 2026 |

---

## Sumário

1. [Definição de Parâmetros](#1-definição-de-parâmetros)
2. [Ferramentas e APIs](#2-ferramentas-e-apis)
3. [Passos de Automação](#3-passos-de-automação)
4. [Considerações Específicas](#4-considerações-específicas)
5. [Validação e Alertas](#5-validação-e-alertas)
6. [Referências](#6-referências)

---

## 1. Definição de Parâmetros

### 1.1 Topologia Geral

```
[ Rede Interna FGT ]──[ Fortigate FW ]──(Internet)──[ Palo Alto FW ]──[ Rede Interna PA ]
   10.10.0.0/24          WAN: 203.0.113.1              WAN: 198.51.100.1    192.168.20.0/24
                              │                               │
                         Túnel: 169.255.1.1/30 ←──────► 169.255.1.2/30
```

### 1.2 Tabela de Parâmetros

| Parâmetro                  | Fortigate (Site A)          | Palo Alto (Site B)          |
|----------------------------|-----------------------------|-----------------------------|
| **Endereço WAN**           | `203.0.113.1`               | `198.51.100.1`              |
| **Rede Local (LAN)**       | `10.10.0.0/24`              | `192.168.20.0/24`           |
| **IP do Túnel**            | `169.255.1.1/30`            | `169.255.1.2/30`            |
| **Rede do Túnel**          | `169.255.1.0/30`            | `169.255.1.0/30`            |
| **Nome do Túnel**          | `VPN-PA-SITE-B`             | `VPN-FGT-SITE-A`            |
| **Interface de Saída**     | `wan1`                      | `ethernet1/1`               |
| **Zona de Destino**        | `vpn-zone`                  | `vpn`                   |

### 1.3 Propostas Phase 1 (IKE)

| Parâmetro          | Valor                          |
|--------------------|--------------------------------|
| **Versão IKE**     | IKEv2                          |
| **Modo**           | Main Mode (Aggressive desativado) |
| **Autenticação**   | Pre-Shared Key                 |
| **PSK**            | `S3cr3t@VPN#2026` *(gerada via secret manager)* |
| **Encriptação**    | AES-256-CBC                    |
| **Integridade**    | SHA-256                        |
| **DH Group**       | Group 14(2048-bit MODP)        |
| **Lifetime**       | 86400 segundos (24h)           |
| **Dead Peer Detection** | Habilitado (DPD)          |

### 1.4 Propostas Phase 2 (IPSec)

| Parâmetro          | Valor                          |
|--------------------|--------------------------------|
| **Protocolo**      | ESP                            |
| **Encriptação**    | AES-256-CBC                    |
| **Integridade**    | SHA-256                        |
| **PFS**            | Group 14 (2048-bit MODP)       |
| **Lifetime**       | 3600 segundos (1h)             |
| **Replay Protection** | Habilitado                 |
| **Anti-Replay Window** | 64 pacotes                |

### 1.5 Redes de Interesse (Selectors)

| Selector | Fortigate                        | Palo Alto                        |
|----------|----------------------------------|----------------------------------|
| **Local** | `10.10.0.0/24`                  | `192.168.20.0/24`                |
| **Remoto**| `192.168.20.0/24`               | `10.10.0.0/24`                   |

---

## 2. Ferramentas e APIs

### 2.1 Fortigate

#### API REST (FortiOS REST API)
- **Base URL:** `https://<ip-fortigate>/api/v2/`
- **Autenticação:** Token via header `Authorization: Bearer <token>` ou cookie de sessão
- **Principais endpoints:**
  - `POST /api/v2/cmdb/vpn.ipsec/phase1-interface` — cria a Fase 1
  - `POST /api/v2/cmdb/vpn.ipsec/phase2-interface` — cria a Fase 2
  - `POST /api/v2/cmdb/firewall/address` — cria objetos de endereço
  - `POST /api/v2/cmdb/firewall/policy` — cria políticas de firewall
  - `GET  /api/v2/monitor/vpn/ipsec` — verifica status do túnel
- **Alternativa CLI:** Paramiko (SSH) para envio de comandos CLI via `config vpn ipsec phase1-interface`

#### Ansible
- Collection: `fortinet.fortios`
- Módulos relevantes: `fortios_vpn_ipsec_phase1_interface`, `fortios_vpn_ipsec_phase2_interface`, `fortios_firewall_policy`

### 2.2 Palo Alto Networks

#### PAN-OS REST API / XML API
- **Base URL:** `https://<ip-panorama-ou-firewall>/restapi/v10.2/`  
- **Autenticação:** API Key via header `X-PAN-KEY: <api_key>` (obtida com `GET /api/?type=keygen`)
- **Principais endpoints:**
  - `/restapi/v10.2/Network/IKEGateways` — cria o IKE Gateway (Phase 1)
  - `/restapi/v10.2/Network/IPSecTunnels` — cria o IPSec tunnel (Phase 2)
  - `/restapi/v10.2/Network/IKECryptoProfiles` — define proposta de criptografia IKE
  - `/restapi/v10.2/Network/IPSecCryptoProfiles` — define proposta de criptografia IPSec
  - `/restapi/v10.2/Policies/SecurityRules` — cria regras de segurança
  - `/api/?type=op&cmd=<show><vpn><ike-sa></ike-sa></vpn></show>` — verifica SAs ativas
- **Biblioteca Python recomendada:** `pan-python` ou `panos` (Palo Alto Networks SDK)
- **Panorama:** Para ambientes multi-device, usar a API do Panorama com `device-group` e `template`

#### Ansible
- Collection: `paloaltonetworks.panos`
- Módulos relevantes: `panos_ike_gateway`, `panos_ipsec_tunnel`, `panos_security_rule`

### 2.3 Ferramentas de Orquestração

| Ferramenta          | Uso Recomendado                                      |
|---------------------|------------------------------------------------------|
| **Ansible**         | Automação declarativa com playbooks                  |
| **Terraform**       | Infraestrutura como código (providers oficiais disponíveis) |
| **Python**          | Script customizado com lógica condicional            |
| **HashiCorp Vault** | Gerenciamento seguro de PSK e tokens de API          |
| **GitLab CI/CD**    | Pipeline de automação com revisão e aprovação        |
| **Netmiko**         | Fallback SSH para ambos os dispositivos              |

---

## 3. Passos de Automação

### 3.1 Fluxo Geral

```
┌─────────────────────────────────────────────────────────┐
│                  PIPELINE DE AUTOMAÇÃO                   │
│                                                         │
│  1. Validação de Parâmetros de Entrada                  │
│       ↓                                                 │
│  2. Obtenção de Credenciais (Vault)                     │
│       ↓                                                 │
│  3. Configuração do Fortigate (Site A)                  │
│       ↓                                                 │
│  4. Configuração do Palo Alto (Site B)                  │
│       ↓                                                 │
│  5. Verificação de Consistência                         │
│       ↓                                                 │
│  6. Testes de Conectividade                             │
│       ↓                                                 │
│  7. Geração de Relatório e Alertas                      │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Validação de Parâmetros de Entrada

Antes de qualquer chamada à API, o script deve:

- Verificar que todos os parâmetros obrigatórios estão definidos (IPs WAN, redes LAN, PSK)
- Validar o formato CIDR das redes e IPs WAN
- Confirmar que os IPs WAN estão dentro da sub-rede e são utilizáveis
- Checar que as propostas de Fase 1 e Fase 2 são simétricas entre os dois lados

### 3.3 Obtenção de Credenciais

- Obter PSK e tokens de API do HashiCorp Vault
- Não armazenar credenciais em texto claro no código ou no repositório
- Validar conectividade com ambos os dispositivos antes de prosseguir

### 3.4 Configuração Fortigate

#### 3.4.1 Criar Objeto de Endereço (Rede Remota)

#### 3.4.2 Criar Fase 1 (IKE Gateway)

#### 3.4.3 Criar Fase 2

#### 3.4.4 Adicionar Rota Estática para o Túnel

#### 3.4.5 Criar Políticas de Firewall

# Política: LAN → VPN

# Política: VPN → LAN (tráfego de retorno)

### 3.5 Configuração Palo Alto

#### 3.5.1 Criar Perfil de Criptografia IKE

#### 3.5.2 Criar Perfil de Criptografia IPSec

#### 3.5.3 Criar Interface de Túnel

#### 3.5.4 Criar IKE Gateway (Fase 1)

#### 3.5.5 Criar IPSec Tunnel (Fase 2)

#### 3.5.6 Adicionar Rota estática para o Túnel no Virtual Router

#### 3.5.7 Criar Zonas e Regras de Segurança

#### 3.5.8 Fazer Commit das Configurações

---

## 4. Considerações Específicas

### 4.1 Diferenças de Paradigma entre Fabricantes

| Aspecto                    | Fortigate                              | Palo Alto                                 |
|----------------------------|----------------------------------------|-------------------------------------------|
| **Modelo de configuração** | Aplica imediatamente via API           | Requer commit explícito após mudanças     |
| **Proxy-IDs**              | Definidos na Fase 2 como `src/dst-subnet` | Configurados como `proxy-id` separado no túnel |
| **Interface de túnel**     | Interface lógica criada automaticamente | Necessário criar `tunnel.X` manualmente  |
| **Rotas**                  | Rota estática com device = nome do túnel | Rota no Virtual Router com interface de túnel |
| **Logging**                | Por política de firewall               | Por política + log profile separado       |
| **Zonas**                  | Conceito de VDOM e zone menos rígido   | Zonas são obrigatórias nas políticas      |

### 4.2 Gerenciamento de PSK

- A PSK deve ser gerada com entropia adequada (mínimo 32 caracteres aleatórios)
- Armazenar exclusivamente no Vault/Manager
- Considerar migração para autenticação por certificado (PKI)

### 4.3 Idempotência

- O script deve verificar se os objetos já existem antes de criá-los (`GET` antes do `POST`)
- Em caso de objeto existente com configuração divergente, decidir entre `PUT` (atualização) ou abortar com alerta

### 4.4 Tratamento de Erros e Rollback

- Implementar rollback automático: se a configuração do Palo Alto falhar após o Fortigate já ter sido configurado, desfazer as mudanças no Fortigate
- Usar transações ou snapshots de configuração onde disponível
- No Palo Alto, usar `revert to running config` via API se o commit falhar
- No Fortigate, manter backup da configuração anterior via `GET /api/v2/monitor/system/config/backup`

### 4.5 Compatibilidade de Propostas

- Ambos os dispositivos devem ter exatamente as mesmas propostas (IKE e IPSec)
- Testar com `ike-version 2` explícito nos dois lados
- O Palo Alto por padrão pode aceitar múltiplas propostas. Garantir que a proposta preferida seja listada primeiro

---

## 5. Validação e Alertas

### 5.1 Estratégia de Validação em Camadas

```
┌────────────────────────────────────────────────────┐
│  CAMADA 1: Validação de Configuração               │
│  Verificar se objetos foram criados corretamente   │
├────────────────────────────────────────────────────┤
│  CAMADA 2: Validação do Estado do Túnel            │
│  Verificar se IKE Phase 1 e Phase 2 subiram        │
├────────────────────────────────────────────────────┤
│  CAMADA 3: Teste de Conectividade Fim a Fim        │
│  Ping / traceroute entre as redes                  │
├────────────────────────────────────────────────────┤
│  CAMADA 4: Monitoramento Contínuo                  │
│  Polling periódico do estado do túnel              │
└────────────────────────────────────────────────────┘
```

### 5.2 Camada 1 — Validação de Configuração

Após cada chamada de criação, verificar com `GET` se o objeto existe e os atributos conferem:

# Verificar Fase 1 no Fortigate

# Verificar IKE Gateway no Palo Alto

### 5.3 Camada 2 — Validação do Estado do Túnel

Via API
Via CLI (SSH/Netmiko)

### 5.4 Camada 3 — Teste de Conectividade Fim a Fim

Ping originado da interface LAN
Via API Fortigate
Palo Alto: ping via operational command

### 5.5 Camada 4 — Monitoramento Contínuo

Implementar polling periódico com os seguintes checks:

### 5.6 Geração de Alertas

#### 5.6.1 Tipos de Alertas

| Severidade | Condição                                              | Ação                                     |
|------------|-------------------------------------------------------|------------------------------------------|
| **CRÍTICO**| Túnel caiu (IKE SA ou IPSec SA down)                  | Alerta imediato push + e-mail + ticket   |
| **ALTO**   | Falha durante a configuração automatizada             | Rollback + e-mail + ticket               |
| **MÉDIO**  | Divergência de configuração detectada (drift)         | E-mail + ticket para revisão manual      |
| **BAIXO**  | Lifetime do túnel < 10% para expirar                  | E-mail preventivo                        |
| **INFO**   | Túnel configurado e estabelecido com sucesso          | Log + e-mail                             |

#### 5.6.2 Canais de Notificação

```python
# Exemplo de função de alerta
def send_alert(severity: str, message: str, details: dict):
    payload = {
        "severity": severity,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details
    }
    # Webhook para Slack/Teams
    requests.post(SLACK_WEBHOOK_URL, json={"text": f"[{severity}] {message}"})
    # API do sistema de tickets (ServiceNow, Jira, etc.)
    if severity in ("CRÍTICO", "ALTO"):
        requests.post(TICKETING_API_URL, json=payload, headers=AUTH_HEADERS)
    # Log estruturado (ELK, Splunk, etc.)
    logging.error(json.dumps(payload)) if severity == "CRÍTICO" else logging.warning(json.dumps(payload))
```

#### 5.6.3 Verificação de Drift de Configuração

Após o deploy inicial, executar periodicamente uma comparação entre a configuração desejada e a configuração atual

### 5.7 Relatório de Execução

Ao final do pipeline de automação, gerar um relatório com:

- Status de cada etapa de configuração (sucesso/falha)
- Timestamp de início e conclusão
- Hash da configuração aplicada (para auditoria)
- Estado atual do túnel (UP/DOWN) em ambos os dispositivos
- Resultado dos testes de conectividade
- Link para o ticket gerado (se aplicável)

```
┌─────────────────────────────────────────────────────┐
│         RELATÓRIO DE CONFIGURAÇÃO VPN               │
│                                                     │
│ Execução: 2026-05-11T14:32:00Z                      │
│ Status Geral: ✅ SUCESSO                            │
│                                                     │
│ Fortigate:                                          │
│   ✅ Fase 1 criada           ✅ Fase 2 criada       │
│   ✅ Rotas configuradas      ✅ Políticas criadas   │
│   ✅ Túnel: UP               Bytes TX: 2048         │
│                                                     │
│ Palo Alto:                                          │
│   ✅ IKE Profile criado      ✅ IPSec Profile criado│
│   ✅ IKE Gateway criado      ✅ Túnel criado        │
│   ✅ Commit: Sucesso         ✅ IKE SA: Active      │
│                                                     │
│ Conectividade:                                      │
│   ✅ 10.10.0.1 → 192.168.20.1: OK (RTT: 12ms)     │
│   ✅ 192.168.20.1 → 10.10.0.1: OK (RTT: 11ms)     │
└─────────────────────────────────────────────────────┘
```

---

## 6. Referências

- [FortiOS REST API Reference](https://fndn.fortinet.net/index.php?/fortiapi/1-fortios/)
- [PAN-OS REST API Reference](https://docs.paloaltonetworks.com/pan-os/10-2/pan-os-panorama-api)
- [Fortinet Ansible Collection](https://galaxy.ansible.com/fortinet/fortios)
- [Palo Alto Ansible Collection](https://galaxy.ansible.com/paloaltonetworks/panos)
- [RFC 7296 — IKEv2](https://datatracker.ietf.org/doc/html/rfc7296)
- [RFC 4301 — IPSec Architecture](https://datatracker.ietf.org/doc/html/rfc4301)
- [HashiCorp Vault Secrets Management](https://developer.hashicorp.com/vault/docs)

---