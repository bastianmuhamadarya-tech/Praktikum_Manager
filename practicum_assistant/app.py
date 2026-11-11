"""
app.py - Backend Flask untuk Praktikum Manager

Cara menjalankan (dari dalam folder practicum_assistant):
    python app.py
Lalu buka di browser:
    http://127.0.0.1:5000
"""

import json
import math
import os
import threading

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

app = Flask(__name__)
data_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data bawaan (dipakai saat data.json belum ada, rusak, atau di-reset)
# ---------------------------------------------------------------------------
def make_tasks(start_id, texts):
    return [{"id": start_id + i, "text": t, "done": False} for i, t in enumerate(texts)]


DEFAULT_TASKS = [
    "Laporan Pendahuluan",
    "Praktikum",
    "Laporan Sementara",
    "Laporan Resmi",
]

DEFAULT_DATA = {
    "courses": [
        {
            "id": 1,
            "name": "Rangkaian Listrik",
            "icon": "fa-bolt",
            "color": "text-amber-500",
            "modules": [
                {
                    "id": 101,
                    "title": "Modul 1: Hukum Ohm dan Kirchhoff",
                    "tasks": make_tasks(1001, DEFAULT_TASKS),
                }
            ],
        },
        {
            "id": 2,
            "name": "Elektronika Analog",
            "icon": "fa-microchip",
            "color": "text-emerald-500",
            "modules": [
                {
                    "id": 201,
                    "title": "Modul 1: Diode dan Penyearah Gelombang",
                    "tasks": make_tasks(
                        2001,
                        [
                            "Praktikum",
                            "Menyusun Data Hasil Praktikum",
                            "Laporan Praktikum",
                            "Melampirkan Lampiran",
                        ],
                    ),
                }
            ],
        },
        {
            "id": 3,
            "name": "Algoritma dan Pemrograman",
            "icon": "fa-code",
            "color": "text-indigo-500",
            "modules": [
                {
                    "id": 301,
                    "title": "Modul 1: Dasar Pemrograman & Algoritma",
                    "tasks": make_tasks(
                        3001,
                        [
                            "Membuat Materi",
                            "Program Scratch",
                            "Flowchart",
                            "Program Python",
                            "Take Video",
                            "Upload Youtube",
                        ],
                    ),
                }
            ],
        },
    ]
}


# ---------------------------------------------------------------------------
# Fungsi bantu: baca/tulis data.json
# ---------------------------------------------------------------------------
def save_data(data):
    """Simpan lewat file sementara supaya data.json tidak rusak kalau proses terhenti."""
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, DATA_FILE)


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("courses"), list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    data = json.loads(json.dumps(DEFAULT_DATA))
    save_data(data)
    return data


def next_id(data):
    """ID baru = ID terbesar yang ada + 1 (berlaku untuk matkul, modul, dan tugas)."""
    ids = [0]
    for course in data["courses"]:
        ids.append(course["id"])
        for module in course.get("modules", []):
            ids.append(module["id"])
            for task in module.get("tasks", []):
                ids.append(task["id"])
    return max(ids) + 1


def find_course(data, course_id):
    return next((c for c in data["courses"] if c["id"] == course_id), None)


def find_module(data, course_id, module_id):
    course = find_course(data, course_id)
    if course is None:
        return None
    return next((m for m in course.get("modules", []) if m["id"] == module_id), None)


def json_body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def get_text(payload, key):
    return str(payload.get(key, "")).strip()


def error(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Route halaman
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/praktikum")
def praktikum():
    return render_template("praktikum.html")


@app.route("/lampiran-analog")
def lampiran_analog():
    return render_template("analog.html")


# ---------------------------------------------------------------------------
# API: mata kuliah
# ---------------------------------------------------------------------------
@app.get("/api/courses")
def get_courses():
    with data_lock:
        return jsonify(load_data())


@app.post("/api/courses")
def add_course():
    name = get_text(json_body(), "name")
    if not name:
        return error("Nama mata kuliah tidak boleh kosong.")

    with data_lock:
        data = load_data()
        new_id = next_id(data)
        data["courses"].append(
            {
                "id": new_id,
                "name": name,
                "icon": "fa-book-bookmark",
                "color": "text-purple-500",
                "modules": [],
            }
        )
        save_data(data)

    data["created_id"] = new_id
    return jsonify(data), 201


# ---------------------------------------------------------------------------
# API: modul
# ---------------------------------------------------------------------------
@app.post("/api/courses/<int:course_id>/modules")
def add_module(course_id):
    title = get_text(json_body(), "title")
    if not title:
        return error("Judul modul tidak boleh kosong.")

    with data_lock:
        data = load_data()
        course = find_course(data, course_id)
        if course is None:
            return error("Mata kuliah tidak ditemukan.", 404)

        base = next_id(data)
        course.setdefault("modules", []).append(
            {
                "id": base,
                "title": title,
                "tasks": make_tasks(base + 1, DEFAULT_TASKS),
            }
        )
        save_data(data)

    return jsonify(data), 201


@app.patch("/api/courses/<int:course_id>/modules/<int:module_id>")
def update_module(course_id, module_id):
    title = get_text(json_body(), "title")
    if not title:
        return error("Judul modul tidak boleh kosong.")

    with data_lock:
        data = load_data()
        module = find_module(data, course_id, module_id)
        if module is None:
            return error("Modul tidak ditemukan.", 404)
        module["title"] = title
        save_data(data)

    return jsonify(data)


@app.delete("/api/courses/<int:course_id>/modules/<int:module_id>")
def delete_module(course_id, module_id):
    with data_lock:
        data = load_data()
        course = find_course(data, course_id)
        if course is None:
            return error("Mata kuliah tidak ditemukan.", 404)
        course["modules"] = [m for m in course.get("modules", []) if m["id"] != module_id]
        save_data(data)

    return jsonify(data)


# ---------------------------------------------------------------------------
# API: tugas (checklist)
# ---------------------------------------------------------------------------
@app.post("/api/courses/<int:course_id>/modules/<int:module_id>/tasks")
def add_task(course_id, module_id):
    text = get_text(json_body(), "text")
    if not text:
        return error("Teks tugas tidak boleh kosong.")

    with data_lock:
        data = load_data()
        module = find_module(data, course_id, module_id)
        if module is None:
            return error("Modul tidak ditemukan.", 404)
        module.setdefault("tasks", []).append(
            {"id": next_id(data), "text": text, "done": False}
        )
        save_data(data)

    return jsonify(data), 201


@app.patch("/api/courses/<int:course_id>/modules/<int:module_id>/tasks/<int:task_id>")
def update_task(course_id, module_id, task_id):
    payload = json_body()

    with data_lock:
        data = load_data()
        module = find_module(data, course_id, module_id)
        if module is None:
            return error("Modul tidak ditemukan.", 404)
        task = next((t for t in module.get("tasks", []) if t["id"] == task_id), None)
        if task is None:
            return error("Tugas tidak ditemukan.", 404)
        task["done"] = bool(payload.get("done", not task["done"]))
        save_data(data)

    return jsonify(data)


@app.delete("/api/courses/<int:course_id>/modules/<int:module_id>/tasks/<int:task_id>")
def delete_task(course_id, module_id, task_id):
    with data_lock:
        data = load_data()
        module = find_module(data, course_id, module_id)
        if module is None:
            return error("Modul tidak ditemukan.", 404)
        module["tasks"] = [t for t in module.get("tasks", []) if t["id"] != task_id]
        save_data(data)

    return jsonify(data)


# ---------------------------------------------------------------------------
# API: reset
# ---------------------------------------------------------------------------
@app.post("/api/reset")
def reset_data():
    with data_lock:
        data = json.loads(json.dumps(DEFAULT_DATA))
        save_data(data)
    return jsonify(data)


# ---------------------------------------------------------------------------
# API: kalkulator praktikum (perhitungan dilakukan di Python)
# ---------------------------------------------------------------------------
@app.post("/api/error")
def api_error():
    payload = json_body()
    try:
        teori = float(payload.get("teori"))
        ukur = float(payload.get("ukur"))
    except (TypeError, ValueError):
        return error("Nilai teori dan nilai ukur harus berupa angka.")

    if not (math.isfinite(teori) and math.isfinite(ukur)):
        return error("Nilai teori dan nilai ukur harus berupa angka yang valid.")
    if teori == 0:
        return error("Nilai teori tidak boleh 0.")

    persen = abs((teori - ukur) / teori) * 100
    return jsonify(
        {
            "persen": persen,
            "rumus": f"|(({teori:g} - {ukur:g}) / {teori:g})| × 100% = {persen:.4f}%",
        }
    )


@app.post("/api/resistansi")
def api_resistansi():
    payload = json_body()
    mode = payload.get("mode", "series")

    try:
        nilai = [float(x) for x in payload.get("resistor", [])]
    except (TypeError, ValueError):
        return error("Semua nilai resistor harus berupa angka.")

    nilai = [x for x in nilai if math.isfinite(x) and x > 0]
    if not nilai:
        return error("Masukkan minimal 1 nilai resistor yang valid.")

    if mode == "parallel":
        total = 1 / sum(1 / x for x in nilai)
    else:
        total = sum(nilai)

    return jsonify({"total": total, "kilo": total / 1_000, "mega": total / 1_000_000})


if __name__ == "__main__":
    app.run(debug=True)
