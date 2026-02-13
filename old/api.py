"""
Backend API for face enrollment operations
"""

import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Data paths
DATA_DIR = Path("data")
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
METADATA_DIR = DATA_DIR / "metadata"


def load_embeddings():
    """Load embeddings from JSON file"""
    embeddings_file = EMBEDDINGS_DIR / "embeddings.json"
    if embeddings_file.exists():
        with open(embeddings_file, "r") as f:
            return json.load(f)
    return {"students": {}}


def load_metadata():
    """Load student metadata from JSON file"""
    metadata_file = METADATA_DIR / "student_info.json"
    if metadata_file.exists():
        with open(metadata_file, "r") as f:
            return json.load(f)
    return {}


@app.route("/api/check-enrollment", methods=["GET"])
def check_enrollment():
    """Check if a student ID or name already exists"""
    student_id = request.args.get("student_id", "").strip()
    student_name = request.args.get("student_name", "").strip()

    if not student_id and not student_name:
        return jsonify({"error": "Please provide student_id or student_name"}), 400

    embeddings_data = load_embeddings()
    metadata_data = load_metadata()

    # Normalize name for comparison
    normalized_name = " ".join(student_name.lower().split()) if student_name else ""

    # Check for duplicate ID in embeddings
    if student_id:
        if student_id in embeddings_data.get("students", {}):
            return jsonify(
                {
                    "exists": True,
                    "duplicate_id": True,
                    "message": f"Student ID '{student_id}' is already registered",
                }
            )
        if student_id in metadata_data:
            return jsonify(
                {
                    "exists": True,
                    "duplicate_id": True,
                    "message": f"Student ID '{student_id}' is already registered",
                }
            )

    # Check for duplicate name
    if normalized_name:
        # Check in embeddings
        for student in embeddings_data.get("students", {}).values():
            if isinstance(student, dict) and student.get("name"):
                existing_name = " ".join(student["name"].lower().split())
                if existing_name == normalized_name:
                    return jsonify(
                        {
                            "exists": True,
                            "duplicate_name": True,
                            "message": f"Name '{student_name}' is already enrolled",
                        }
                    )

        # Check in metadata
        for student in metadata_data.values():
            if isinstance(student, dict) and student.get("name"):
                existing_name = " ".join(student["name"].lower().split())
                if existing_name == normalized_name:
                    return jsonify(
                        {
                            "exists": True,
                            "duplicate_name": True,
                            "message": f"Name '{student_name}' is already enrolled",
                        }
                    )

    return jsonify({"exists": False, "message": "Student ID and name are available"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
