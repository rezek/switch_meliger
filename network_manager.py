"""
network_manager.py
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from netmiko import ConnectHandler
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False
    logger.warning("Netmiko não disponível — apenas modo simulação funcionará.")


# ──────────────────────────────────────────────────────────────────
#  Switch simulado
# ──────────────────────────────────────────────────────────────────

class SimulatedSwitch:
    """Emula um switch Cisco IOS em memória para testes."""

    _CONFIG_TEMPLATE = """\
Building configuration...

Current configuration : 1024 bytes
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname {hostname}
!
{vlan_block}
!
{iface_block}
end"""

    def __init__(self):
        self.hostname = "SWITCH-SIMULADO"
        self.vlans: dict[str, str] = {"1": "default"}
        self._nvram_saved = False

    def send_config(self, commands: list[str]) -> str:
        lines = []
        current_vlan: Optional[str] = None

        for raw in commands:
            cmd = raw.strip()
            if not cmd:
                continue
            lines.append(f"SW(config)#{cmd}")

            if cmd.startswith("hostname "):
                self.hostname = cmd.split(" ", 1)[1].strip()
                self._nvram_saved = False

            elif cmd.startswith("vlan "):
                vid = cmd.split(" ", 1)[1].strip()
                current_vlan = vid
                self.vlans.setdefault(vid, f"VLAN{vid}")

            elif cmd.startswith("name ") and current_vlan:
                self.vlans[current_vlan] = cmd.split(" ", 1)[1].strip()

            elif cmd in ("exit", "end"):
                current_vlan = None

            elif cmd == "write memory":
                self._nvram_saved = True
                lines.append("[OK] Building configuration... [OK]")

        return "\n".join(lines)

    def get_running_config(self) -> str:
        vlan_block = "\n".join(
            f"vlan {vid}\n name {name}"
            for vid, name in self.vlans.items() if vid != "1"
        ) or "! nenhuma VLAN extra"

        iface_block = "\n".join(
            f"interface Vlan{vid}\n description {name}\n no ip address"
            for vid, name in self.vlans.items() if vid != "1"
        ) or "! nenhuma interface VLAN extra"

        return self._CONFIG_TEMPLATE.format(
            hostname=self.hostname,
            vlan_block=vlan_block,
            iface_block=iface_block,
        )

    def get_show_vlan(self) -> str:
        header = (
            "VLAN Name                             Status    Ports\n"
            "---- -------------------------------- --------- -------------------------------\n"
            "1    default                          active    Gi0/0, Gi0/1"
        )
        rows = [
            f"{vid:<5}{name:<33}active"
            for vid, name in self.vlans.items() if vid != "1"
        ]
        return header + ("\n" + "\n".join(rows) if rows else "")

    def get_hostname(self) -> str:
        return self.hostname

    def write_memory(self) -> str:
        self._nvram_saved = True
        return "Building configuration...\n[OK]"


# ──────────────────────────────────────────────────────────────────
#  Network Manager
# ──────────────────────────────────────────────────────────────────

class NetworkManager:
    """Gerencia conexão e operações no switch (real ou simulado)."""

    def __init__(self):
        self.connection = None
        self.simulator: Optional[SimulatedSwitch] = None
        self.is_simulation = False
        self.connected = False
        self.current_host = ""
        self.current_hostname = ""
        self.connection_info: dict = {}

    # ── conexão ───────────────────────────────────────────────────

    def connect(self, host: str, username: str, password: str,
                device_type: str = "cisco_ios", simulation: bool = False) -> dict:
        self.disconnect()
        self.is_simulation = simulation
        self.current_host = host

        if simulation:
            self.simulator = SimulatedSwitch()
            self.connected = True
            self.current_hostname = self.simulator.get_hostname()
            self.connection_info = {"host": host, "mode": "Simulação", "device_type": device_type}
            return {
                "success": True,
                "message": f"Conectado ao switch SIMULADO ({host})",
                "hostname": self.current_hostname,
                "mode": "simulation",
            }

        if not NETMIKO_AVAILABLE:
            return {"success": False,
                    "message": "Netmiko não instalado. Use modo simulação ou: pip install netmiko"}

        try:
            self.connection = ConnectHandler(
                device_type=device_type, host=host,
                username=username, password=password,
                timeout=30, session_timeout=60,
            )
            self.connected = True
            self.current_hostname = (
                self.connection.find_prompt().replace("#", "").replace(">", "").strip()
            )
            self.connection_info = {"host": host, "mode": "Real", "device_type": device_type}
            return {
                "success": True,
                "message": f"Conectado ao switch {self.current_hostname} ({host})",
                "hostname": self.current_hostname,
                "mode": "real",
            }
        except Exception as exc:
            self.connected = False
            msg = str(exc)
            if "Authentication" in msg:
                msg = "Falha de autenticação: usuário ou senha incorretos"
            elif "timed out" in msg.lower():
                msg = f"Timeout: não foi possível conectar a {host}"
            return {"success": False, "message": msg}

    def disconnect(self) -> dict:
        try:
            if self.connection and not self.is_simulation:
                self.connection.disconnect()
        except Exception:
            pass
        finally:
            self.connection = None
            self.simulator = None
            self.connected = False
            self.current_host = ""
        return {"success": True, "message": "Desconectado"}

    def get_status(self) -> dict:
        return {
            "connected": self.connected,
            "host": self.current_host,
            "hostname": self.current_hostname,
            "mode": "simulation" if self.is_simulation else "real",
            "info": self.connection_info,
        }

    # ── helpers internos ──────────────────────────────────────────

    def _send_config(self, commands: list[str]) -> str:
        if self.is_simulation and self.simulator:
            return self.simulator.send_config(commands)
        return self.connection.send_config_set(commands)

    def _running_config(self) -> str:
        if self.is_simulation and self.simulator:
            return self.simulator.get_running_config()
        # Adicionar timeout para evitar travamentos em comandos longos
        try:
            return self.connection.send_command("show running-config", read_timeout=60)
        except Exception as exc:
            logger.warning(f"Erro ao executar 'show running-config': {exc}")
            raise

    def _show_vlan(self) -> str:
        if self.is_simulation and self.simulator:
            return self.simulator.get_show_vlan()
        return self.connection.send_command("show vlan brief")

    def _get_hostname(self) -> str:
        if self.is_simulation and self.simulator:
            return self.simulator.get_hostname()
        return self.connection.find_prompt().replace("#", "").replace(">", "").strip()

    def _require_connection(self):
        if not self.connected:
            raise RuntimeError("Não conectado ao switch")

    # ── operações públicas ────────────────────────────────────────

    def configure(self, hostname: str, vlans: list[dict]) -> dict:
        """Aplica hostname e VLANs no switch."""
        try:
            self._require_connection()
            commands: list[str] = []
            log: list[str] = []

            if hostname:
                commands.append(f"hostname {hostname}")
                log.append(f"✓ Hostname configurado: {hostname}")

            for vlan in vlans:
                vid = str(vlan.get("id", "")).strip()
                name = vlan.get("name", "").strip().replace(" ", "_")
                if not vid or not name:
                    continue
                commands += [f"vlan {vid}", f"name {name}", "exit"]
                log.append(f"✓ VLAN {vid} → {name}")

            if not commands:
                return {"success": False, "message": "Nenhum comando gerado"}

            output = self._send_config(commands)

            if hostname:
                self.current_hostname = hostname

            return {
                "success": True,
                "message": "Configuração aplicada com sucesso",
                "commands_sent": commands,
                "output": output,
                "log": log,
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def save_nvram(self) -> dict:
        """Salva a configuração atual na NVRAM do switch."""
        try:
            self._require_connection()
            if self.is_simulation and self.simulator:
                self.simulator.write_memory()
                return {"success": True, "message": "Configuração salva na NVRAM (simulação)"}
            self.connection.send_command("write memory")
            return {"success": True, "message": "Configuração salva na NVRAM"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def backup_config(self) -> dict:
        """Salva running-config em arquivo local com hostname + timestamp."""
        try:
            self._require_connection()
            logger.info("Iniciando backup da configuração...")

            # Obter configuração com timeout
            try:
                config = self._running_config()
                if not config or len(config.strip()) < 10:
                    return {"success": False, "message": "Configuração vazia ou muito pequena recebida do switch"}
            except Exception as config_exc:
                logger.error(f"Erro ao obter running-config: {config_exc}")
                return {"success": False, "message": f"Erro ao obter configuração: {str(config_exc)}"}

            hostname = self._get_hostname()
            if not hostname:
                hostname = "SWITCH_UNKNOWN"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{hostname}_{timestamp}.txt"
            os.makedirs("backups", exist_ok=True)
            filepath = os.path.join("backups", filename)

            header = (
                f"! {'='*60}\n"
                f"! Switch  : {hostname}\n"
                f"! Host    : {self.current_host}\n"
                f"! Data    : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"! {'='*60}\n"
            )

            try:
                with open(filepath, "w", encoding="utf-8") as fh:
                    fh.write(header + config)
            except Exception as file_exc:
                logger.error(f"Erro ao salvar arquivo de backup: {file_exc}")
                return {"success": False, "message": f"Erro ao salvar arquivo: {str(file_exc)}"}

            # Metadados JSON
            try:
                meta = {
                    "hostname": hostname, "host": self.current_host,
                    "timestamp": datetime.now().isoformat(),
                    "filename": filename, "size_bytes": os.path.getsize(filepath),
                }
                with open(filepath.replace(".txt", "_meta.json"), "w") as fh:
                    json.dump(meta, fh, indent=2)
            except Exception as meta_exc:
                logger.warning(f"Erro ao salvar metadados: {meta_exc}")
                # Não falha o backup por causa dos metadados

            logger.info(f"Backup realizado com sucesso: {filename} ({os.path.getsize(filepath)} bytes)")
            return {
                "success": True,
                "message": "Backup realizado com sucesso",
                "filename": filename,
                "filepath": filepath,
                "size": os.path.getsize(filepath),
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        except RuntimeError as rt_exc:
            logger.warning(f"Tentativa de backup sem conexão: {rt_exc}")
            return {"success": False, "message": "Não conectado ao switch"}
        except Exception as exc:
            logger.error(f"Erro inesperado no backup: {exc}")
            return {"success": False, "message": f"Erro inesperado: {str(exc)}"}

    def validate_config(self, hostname: str, vlans: list[dict]) -> dict:
        """Compara configuração desejada com a do switch. Retorna divergências."""
        try:
            self._require_connection()
            show_vlan = self._show_vlan()
            current_hostname = self._get_hostname()
            divergences: list[dict] = []
            confirmations: list[str] = []

            # Validar hostname
            if hostname:
                if current_hostname.lower() == hostname.lower():
                    confirmations.append(f"Hostname correto: {current_hostname}")
                else:
                    divergences.append({
                        "type": "hostname", "severity": "critical",
                        "message": "Hostname divergente",
                        "expected": hostname, "found": current_hostname,
                    })

            # Validar VLANs
            for vlan in vlans:
                vid = str(vlan.get("id", "")).strip()
                name = vlan.get("name", "").strip().replace(" ", "_")
                if not vid:
                    continue

                found_line = None
                for line in show_vlan.split("\n"):
                    parts = line.split()
                    if parts and parts[0] == vid:
                        found_line = parts
                        break

                if found_line is None:
                    divergences.append({
                        "type": "vlan_missing", "severity": "critical",
                        "message": f"VLAN {vid} não encontrada no switch",
                        "expected": f"VLAN {vid} ({name})", "found": "Não configurada",
                    })
                elif name and len(found_line) > 1 and found_line[1].lower() != name.lower():
                    divergences.append({
                        "type": "vlan_name", "severity": "warning",
                        "message": f"Nome incorreto na VLAN {vid}",
                        "expected": name, "found": found_line[1],
                    })
                else:
                    confirmations.append(f"VLAN {vid} ({name}) configurada corretamente")

            return {
                "success": True,
                "status": "ok" if not divergences else "divergent",
                "divergences": divergences,
                "confirmations": confirmations,
                "current_hostname": current_hostname,
                "vlan_table": show_vlan,
                "divergence_count": len(divergences),
                "confirmation_count": len(confirmations),
            }
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def get_vlans(self) -> dict:
        """Retorna lista de VLANs do switch."""
        try:
            self._require_connection()
            output = self._show_vlan()
            vlans = []
            for line in output.split("\n")[2:]:
                parts = line.split()
                if parts and parts[0].isdigit():
                    vlans.append({
                        "id": parts[0],
                        "name": parts[1] if len(parts) > 1 else "",
                        "status": parts[2] if len(parts) > 2 else "active",
                    })
            return {"success": True, "vlans": vlans, "raw_output": output}
        except Exception as exc:
            return {"success": False, "message": str(exc)}
