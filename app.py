"""
app.py
Switch MELIger — Flask Backend
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from network_manager import NetworkManager

# ── Logging ───────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("backups", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "switch-meliger-2024")
nm = NetworkManager()


# ── Rotas de página ───────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Conexão ──────────────────────────────────────────────────

@app.route("/api/connect", methods=["POST"])
def api_connect():
    d = request.get_json(force=True)
    host       = d.get("host", "").strip()
    username   = d.get("username", "").strip()
    password   = d.get("password", "")
    dtype      = d.get("device_type", "cisco_ios")
    simulation = bool(d.get("simulation", False))

    if not all([host, username, password]):
        return jsonify({"success": False, "message": "Host, usuário e senha são obrigatórios"}), 400

    result = nm.connect(host, username, password, dtype, simulation)
    logger.info("connect → %s", result["message"])
    return jsonify(result)


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    result = nm.disconnect()
    logger.info("disconnect")
    return jsonify(result)


@app.route("/api/status")
def api_status():
    return jsonify(nm.get_status())


# ── API: Configuração ─────────────────────────────────────────────

@app.route("/api/configure", methods=["POST"])
def api_configure():
    d        = request.get_json(force=True)
    hostname = d.get("hostname", "").strip()
    vlans    = d.get("vlans", [])

    if not vlans:
        return jsonify({"success": False, "message": "Nenhuma VLAN fornecida"}), 400

    result = nm.configure(hostname, vlans)
    logger.info("configure → success=%s", result["success"])
    return jsonify(result)


@app.route("/api/save_nvram", methods=["POST"])
def api_save_nvram():
    result = nm.save_nvram()
    logger.info("save_nvram → %s", result.get("message"))
    return jsonify(result)


@app.route("/api/backup", methods=["POST"])
def api_backup():
    result = nm.backup_config()
    logger.info("backup → %s", result.get("filename", result.get("message")))
    return jsonify(result)


@app.route("/api/backup/download", methods=["GET"])
def api_backup_download():
    filename = request.args.get("filename", "").strip()
    fmt = request.args.get("format", "txt").strip()

    if not filename or fmt not in ("txt", "meta"):
        return jsonify({"success": False, "message": "Parâmetros inválidos"}), 400

    if fmt == "meta":
        filepath = os.path.join("backups", filename.replace(".txt", "_meta.json"))
        download_name = filename.replace(".txt", "_meta.json")
    else:
        filepath = os.path.join("backups", filename)
        download_name = filename

    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        logger.warning(f"Tentativa de download de arquivo inexistente: {filepath}")
        return jsonify({"success": False, "message": "Arquivo não encontrado"}), 404

    try:
        logger.info(f"Download de backup: {download_name}")
        return send_file(filepath, as_attachment=True, download_name=download_name)
    except Exception as exc:
        logger.error(f"Erro ao fazer download: {exc}")
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/validate", methods=["POST"])
def api_validate():
    d        = request.get_json(force=True)
    hostname = d.get("hostname", "").strip()
    vlans    = d.get("vlans", [])
    result   = nm.validate_config(hostname, vlans)
    logger.info("validate → status=%s divergences=%d",
                result.get("status"), result.get("divergence_count", 0))
    return jsonify(result)


@app.route("/api/vlans")
def api_vlans():
    return jsonify(nm.get_vlans())


@app.route("/api/logs")
def api_logs():
    try:
        with open("logs/app.log", encoding="utf-8") as fh:
            lines = fh.readlines()
        return jsonify({"success": True, "logs": [l.rstrip() for l in lines[-60:]]})
    except FileNotFoundError:
        return jsonify({"success": True, "logs": []})


# ── Main ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Switch MELIger iniciando em http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
