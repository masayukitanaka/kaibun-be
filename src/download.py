import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

download_bp = Blueprint("download", __name__)


@download_bp.route("/download")
def download():
    filename = request.args.get("file", "").strip()
    if not filename:
        return jsonify(error="file パラメータが必要です"), 400

    if "/" in filename or "\\" in filename:
        return jsonify(error="不正なファイル名です"), 400

    file_dir = os.environ.get("FILE_DIR", "/tmp")
    file_path = Path(file_dir) / "kaibun" / filename

    if not file_path.is_file():
        return jsonify(error="ファイルが見つかりません"), 404

    return send_file(file_path, mimetype="text/csv", as_attachment=True,
                     download_name=filename)
