from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from database import init_db

app = Flask(__name__)
app.secret_key = "hospital_secret"

def get_db():
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    total_patients = conn.execute("SELECT COUNT(*) as count FROM patients").fetchone()["count"]
    todays_appointments = conn.execute("SELECT COUNT(*) as count FROM appointments WHERE DATE(appointment_date) = DATE('now')").fetchone()["count"]
    appointments = conn.execute("SELECT * FROM appointments WHERE status = 'pending'").fetchall()
    patients = conn.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("home.html", total_patients=total_patients, todays_appointments=todays_appointments, appointments=appointments, patients=patients)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect(url_for("login"))
        except:
            return render_template("register.html", error="Username already exists")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/patients")
def patients():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    query = request.args.get("query", "")
    if query:
        all_patients = conn.execute("SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ?", (f"%{query}%", f"%{query}%")).fetchall()
    else:
        all_patients = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("patients.html", patients=all_patients, query=query)

@app.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        phone = request.form["phone"]
        address = request.form["address"]
        conn = get_db()
        conn.execute("INSERT INTO patients (name, age, phone, address) VALUES (?, ?, ?, ?)", (name, age, phone, address))
        conn.commit()
        conn.close()
        return redirect(url_for("patients"))
    return render_template("add_patient.html")

@app.route("/edit_patient/<int:id>", methods=["GET", "POST"])
def edit_patient(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        phone = request.form["phone"]
        address = request.form["address"]
        conn.execute("UPDATE patients SET name=?, age=?, phone=?, address=? WHERE id=?", (name, age, phone, address, id))
        conn.commit()
        conn.close()
        return redirect(url_for("patients"))
    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("edit_patient.html", patient=patient)

@app.route("/delete_patient/<int:id>")
def delete_patient(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM patients WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("patients"))

@app.route("/appointments")
def appointments():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    all_appointments = conn.execute("""
        SELECT a.*, p.name as patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        ORDER BY a.appointment_date DESC
    """).fetchall()
    conn.close()
    return render_template("appointments.html", appointments=all_appointments)

@app.route("/add_appointment", methods=["GET", "POST"])
def add_appointment():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        patient_id = request.form["patient_id"]
        doctor_name = request.form["doctor_name"]
        appointment_date = request.form["appointment_date"]
        appointment_time = request.form["appointment_time"]
        reason = request.form["reason"]
        conn.execute("INSERT INTO appointments (patient_id, doctor_name, appointment_date, appointment_time, reason) VALUES (?, ?, ?, ?, ?)",
                     (patient_id, doctor_name, appointment_date, appointment_time, reason))
        conn.commit()
        conn.close()
        return redirect(url_for("appointments"))
    patients = conn.execute("SELECT * FROM patients").fetchall()
    conn.close()
    return render_template("add_appointment.html", patients=patients)

@app.route("/edit_appointment/<int:id>", methods=["GET", "POST"])
def edit_appointment(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        doctor_name = request.form["doctor_name"]
        appointment_date = request.form["appointment_date"]
        appointment_time = request.form["appointment_time"]
        reason = request.form["reason"]
        status = request.form["status"]
        conn.execute("UPDATE appointments SET doctor_name=?, appointment_date=?, appointment_time=?, reason=?, status=? WHERE id=?",
                     (doctor_name, appointment_date, appointment_time, reason, status, id))
        conn.commit()
        conn.close()
        return redirect(url_for("appointments"))
    appointment = conn.execute("SELECT * FROM appointments WHERE id = ?", (id,)).fetchone()
    patients = conn.execute("SELECT * FROM patients").fetchall()
    conn.close()
    return render_template("edit_appointment.html", appointment=appointment, patients=patients)
@app.route("/complete_appointment/<int:id>")
def complete_appointment(id):
    conn = get_db()
    conn.execute("UPDATE appointments SET status='completed' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("appointments"))

@app.route("/delete_appointment/<int:id>")
def delete_appointment(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM appointments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("appointments"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)