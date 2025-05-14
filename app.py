from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_mysqldb import MySQL
from recommender import get_recommendation
from werkzeug.utils import secure_filename  
from sqlalchemy import create_engine
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'rahasia123'

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Ganti dengan password MySQL Anda
app.config['MYSQL_DB'] = 'db_coba'

mysql = MySQL(app)

# Folder upload
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# Fungsi cek file pdf
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#------------------------------------------[Admin]----------------------------------


@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Route input mahasiswa

@app.route('/tambah_mahasiswa', methods=['GET', 'POST'])
def tambah_mahasiswa():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        nim = request.form['nim']
        bidang_minat = request.form['bidang_minat']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO mahasiswa (username, nim, bidang_minat) VALUES (%s, %s, %s)", (username, nim, bidang_minat))
        mysql.connection.commit()
        cur.close()
        flash('Data mahasiswa berhasil ditambahkan.')
        return redirect(url_for('daftar_mahasiswa'))

    return render_template('tambah_mahasiswa.html')


# Route menampilkan daftar mahasiswa

@app.route('/daftar_mahasiswa')
def daftar_mahasiswa():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM mahasiswa")
    data = cur.fetchall()
    cur.close()

    return render_template('daftar_mahasiswa.html', mahasiswa=data)

# Tambah Jurnal

@app.route('/tambah_jurnal', methods=['GET', 'POST'])
def tambah_jurnal():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        judul = request.form['judul']
        author = request.form['author']
        abstract = request.form['abstract']
        bidang_minat = request.form['bidang_minat']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO jurnal_files (judul, author, abstract, bidang_minat, filename) VALUES (%s, %s, %s, %s, %s)", 
                        (judul, author, abstract, bidang_minat, filename))
            mysql.connection.commit()
            cur.close()

            flash('Jurnal berhasil diunggah.')
            return redirect(url_for('tambah_jurnal'))
        else:
            flash('Format file tidak valid. Harus PDF.')

    return render_template('tambah_jurnal.html')

# Daftar Jurnal
@app.route('/daftar_jurnal')
def daftar_jurnal():
    if 'username' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM jurnal_files ORDER BY upload_time DESC")
    pdfs = cur.fetchall()
    cur.close()

    return render_template('daftar_jurnal.html', pdfs=pdfs)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


#------------------------------------------[Mahasiswa]----------------------------------


@app.route('/dashboard_mahasiswa', methods=["GET", "POST"])
def dashboard_mahasiswa():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    input_text = ""
    results_bidang_minat = []
    results_rekomendasi = []
    is_recommendation = False
    selected_bidang_minat = ""
    bidang_minat_tersedia = []

    engine = create_engine("mysql+mysqlconnector://root:@localhost/db_coba")

    # Ambil bidang minat user
    query_user = "SELECT bidang_minat FROM mahasiswa WHERE username = %s"
    bidang_minat_df = pd.read_sql(query_user, con=engine, params=(username,))
    if bidang_minat_df.empty:
        return "Data mahasiswa tidak ditemukan.", 404

    bidang_minat = bidang_minat_df.iloc[0]['bidang_minat']

    # Ambil jurnal sesuai bidang minat user
    query_jurnal = "SELECT judul, bidang_minat, fileName FROM jurnal_files WHERE bidang_minat = %s"
    results_bidang_minat = pd.read_sql(query_jurnal, con=engine, params=(bidang_minat,)).to_dict(orient='records')

    if request.method == "POST":
        input_text = request.form.get("judul", "").strip()
        action = request.form.get("action")
        selected_bidang_minat = request.form.get("filter_bidang_minat", "")

        if input_text:
            rekomendasi_raw = get_recommendation(input_text)
            is_recommendation = True
            bidang_minat_tersedia = sorted(set(r['bidang_minat'] for r in rekomendasi_raw))

            if action == "filter" and selected_bidang_minat:
                rekomendasi_raw = [r for r in rekomendasi_raw if r['bidang_minat'] == selected_bidang_minat]

            results_rekomendasi = [
                r for r in rekomendasi_raw
                if isinstance(r, dict) and 'judul' in r and 'fileName' in r and 'bidang_minat' in r
            ]

    return render_template(
        'mahasiswa/dashboard.html',
        username=username,
        results_bidang_minat=results_bidang_minat,
        results_rekomendasi=results_rekomendasi,
        input_text=input_text,
        is_recommendation=is_recommendation,
        bidang_minat_tersedia=bidang_minat_tersedia,
        selected_bidang_minat=selected_bidang_minat
    )







        

    

@app.route('/login_mahasiswa', methods=['GET', 'POST'])
def login_mahasiswa():
    if request.method == 'POST':
        username = request.form['username']
        nim = request.form['nim']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM mahasiswa WHERE username=%s AND nim=%s", (username, nim))
        user = cur.fetchone()
        cur.close()

        if user:
            session['username'] = username
            return redirect(url_for('dashboard_mahasiswa'))
        else:
            flash('username atau password salah!')

    return render_template('/mahasiswa/login.html')

@app.route('/logout_mahasiswa')
def logout_mahasiswa():
    session.pop('username', None)
    return redirect(url_for('login_mahasiswa'))

if __name__ == '__main__':
    app.run(debug=True)