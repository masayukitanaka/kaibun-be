import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

download_bp = Blueprint("download", __name__)


@download_bp.route("/download")
def download():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify(error="keyword パラメータが必要です"), 400

    file_dir = os.environ.get("FILE_DIR", "/tmp")
    file_path = Path(file_dir) / "kaibun" / f"{keyword}.jsonl"

    if not file_path.is_file():
        return jsonify(error="ファイルが見つかりません"), 404

    return send_file(file_path, mimetype="application/x-ndjson", as_attachment=True,
                     download_name=f"{keyword}.jsonl")
