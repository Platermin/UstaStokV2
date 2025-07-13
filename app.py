from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Veritabanı Yolu (Render ortamında kalıcı depolama için aynı dizinde)
DATABASE = 'ustastok.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spare_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_code TEXT UNIQUE NOT NULL,
            part_name TEXT NOT NULL,
            brand TEXT,
            model_compatibility TEXT,
            category TEXT,
            purchase_price REAL,
            sale_price REAL,
            current_stock INTEGER DEFAULT 0,
            min_stock_level INTEGER DEFAULT 0,
            supplier TEXT,
            location TEXT,
            last_purchase_date TEXT,
            last_purchase_quantity INTEGER
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_plate TEXT UNIQUE NOT NULL,
            make TEXT,
            model TEXT,
            year INTEGER,
            chassis_number TEXT,
            engine_number TEXT,
            owner_name TEXT,
            owner_phone TEXT
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            service_date TEXT NOT NULL,
            mileage INTEGER NOT NULL,
            diagnosis TEXT,
            performed_actions TEXT,
            notes TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS used_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_record_id INTEGER NOT NULL,
            part_id INTEGER NOT NULL,
            quantity_used INTEGER NOT NULL,
            FOREIGN KEY (service_record_id) REFERENCES service_records(id),
            FOREIGN KEY (part_id) REFERENCES spare_parts(id)
        );
    ''')

    conn.commit()
    conn.close()
    print("Veritabanı başlatıldı veya zaten mevcut.")

# Yedek Parça Fonksiyonları
def add_spare_part(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO spare_parts (part_code, part_name, brand, model_compatibility, category, purchase_price, sale_price, current_stock, min_stock_level, supplier, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', (data['part_code'], data['part_name'], data.get('brand'), data.get('model_compatibility'), data.get('category'), data.get('purchase_price'), data.get('sale_price'), data.get('current_stock', 0), data.get('min_stock_level', 0), data.get('supplier'), data.get('location')))
    conn.commit()
    part_id = cursor.lastrowid
    conn.close()
    return part_id

def get_spare_parts(search_query=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        search_query = '%' + search_query + '%'
        cursor.execute('''
            SELECT * FROM spare_parts
            WHERE part_code LIKE ? OR part_name LIKE ? OR brand LIKE ?
        ''', (search_query, search_query, search_query))
    else:
        cursor.execute('SELECT * FROM spare_parts')
    parts = cursor.fetchall()
    conn.close()
    return [dict(part) for part in parts]

def update_spare_part(part_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE spare_parts
        SET part_code=?, part_name=?, brand=?, model_compatibility=?, category=?,
            purchase_price=?, sale_price=?, current_stock=?, min_stock_level=?,
            supplier=?, location=?
        WHERE id=?;
    ''', (data['part_code'], data['part_name'], data.get('brand'), data.get('model_compatibility'), data.get('category'),
        data.get('purchase_price'), data.get('sale_price'), data.get('current_stock'), data.get('min_stock_level'),
        data.get('supplier'), data.get('location'), part_id))
    conn.commit()
    conn.close()

def get_spare_part_by_id(part_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM spare_parts WHERE id = ?', (part_id,))
    part = cursor.fetchone()
    conn.close()
    return dict(part) if part else None

# Araç Fonksiyonları
def add_vehicle(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vehicles (license_plate, make, model, year, chassis_number, engine_number, owner_name, owner_phone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    ''', (data['license_plate'], data.get('make'), data.get('model'), data.get('year'), data.get('chassis_number'), data.get('engine_number'), data.get('owner_name'), data.get('owner_phone')))
    conn.commit()
    vehicle_id = cursor.lastrowid
    conn.close()
    return vehicle_id

def get_vehicles(license_plate=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if license_plate:
        cursor.execute('SELECT * FROM vehicles WHERE license_plate = ?', (license_plate,))
    else:
        cursor.execute('SELECT * FROM vehicles')
    vehicles = cursor.fetchall()
    conn.close()
    return [dict(vehicle) for vehicle in vehicles]

# Servis Kaydı Fonksiyonları
def add_service_record(data):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO service_records (vehicle_id, service_date, mileage, diagnosis, performed_actions, notes)
        VALUES (?, ?, ?, ?, ?, ?);
    ''', (data['vehicle_id'], data['service_date'], data['mileage'], data.get('diagnosis'), data.get('performed_actions'), data.get('notes')))
    service_record_id = cursor.lastrowid

    if 'used_parts' in data and isinstance(data['used_parts'], list):
        for part in data['used_parts']:
            part_id = part['part_id']
            quantity_used = part['quantity_used']

            cursor.execute('''
                INSERT INTO used_parts (service_record_id, part_id, quantity_used)
                VALUES (?, ?, ?);
            ''', (service_record_id, part_id, quantity_used))

            cursor.execute('''
                UPDATE spare_parts
                SET current_stock = current_stock - ?
                WHERE id = ?;
            ''', (quantity_used, part_id))

    conn.commit()
    conn.close()
    return service_record_id

def get_service_records(vehicle_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if vehicle_id:
        cursor.execute('SELECT * FROM service_records WHERE vehicle_id = ? ORDER BY service_date DESC', (vehicle_id,))
    else:
        cursor.execute('SELECT * FROM service_records ORDER BY service_date DESC')
    records = cursor.fetchall()
    conn.close()
    return [dict(record) for record in records]

def get_used_parts_for_service(service_record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM used_parts WHERE service_record_id = ?', (service_record_id,))
    parts = cursor.fetchall()
    conn.close()
    return [dict(part) for part in parts]


# API Endpoints
@app.route('/api/spare_parts', methods=['POST'])
def create_spare_part_api():
    data = request.json
    if not data.get('part_code') or not data.get('part_name'):
        return jsonify({"message": "Parça kodu ve Parça adı boş bırakılamaz."}), 400
    try:
        part_id = add_spare_part(data)
        return jsonify({"message": "Yedek parça başarıyla eklendi", "id": part_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "Bu parça kodu zaten mevcut. Lütfen farklı bir kod girin."}), 409
    except Exception as e:
        return jsonify({"message": f"Bir hata oluştu: {str(e)}"}), 500

@app.route('/api/spare_parts', methods=['GET'])
def list_spare_parts_api():
    search_query = request.args.get('search')
    parts = get_spare_parts(search_query)
    return jsonify(parts)

@app.route('/api/spare_parts/<int:part_id>', methods=['GET'])
def get_spare_part_api(part_id):
    part = get_spare_part_by_id(part_id)
    if part:
        return jsonify(part), 200
    return jsonify({"message": "Parça bulunamadı."}), 404

@app.route('/api/spare_parts/<int:part_id>', methods=['PUT']) # Güncelleme
def update_spare_part_api(part_id):
    data = request.json
    existing_part = get_spare_part_by_id(part_id)
    if not existing_part:
        return jsonify({"message": "Güncellenecek parça bulunamadı."}), 404

    if 'part_code' in data and data['part_code'] != existing_part['part_code']:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM spare_parts WHERE part_code = ? AND id != ?', (data['part_code'], part_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"message": "Bu parça kodu zaten başka bir parça tarafından kullanılıyor."}), 409
        conn.close()

    try:
        update_spare_part(part_id, data)
        return jsonify({"message": "Parça başarıyla güncellendi."}), 200
    except Exception as e:
        return jsonify({"message": f"Parça güncellenirken bir hata oluştu: {str(e)}"}), 500


@app.route('/api/vehicles', methods=['POST'])
def create_vehicle_api():
    data = request.json
    if not data.get('license_plate'):
        return jsonify({"message": "Plaka numarası boş bırakılamaz."}), 400
    try:
        vehicle_id = add_vehicle(data)
        return jsonify({"message": "Araç başarıyla kaydedildi", "id": vehicle_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "Bu plaka numarası zaten mevcut. Lütfen farklı bir plaka girin."}), 409
    except Exception as e:
        return jsonify({"message": f"Bir hata oluştu: {str(e)}"}), 500

@app.route('/api/vehicles', methods=['GET'])
def list_vehicles_api():
    license_plate = request.args.get('license_plate')
    vehicles = get_vehicles(license_plate)
    return jsonify(vehicles)

@app.route('/api/service_records', methods=['POST'])
def create_service_record_api():
    data = request.json
    if not data.get('vehicle_id') or not data.get('service_date') or not data.get('mileage'):
        return jsonify({"message": "Araç ID, Servis Tarihi ve Kilometre boş bırakılamaz."}), 400
    try:
        record_id = add_service_record(data)
        return jsonify({"message": "Servis kaydı başarıyla eklendi", "id": record_id}), 201
    except Exception as e:
        return jsonify({"message": f"Servis kaydı eklenirken bir hata oluştu: {str(e)}"}), 500

@app.route('/api/service_records', methods=['GET'])
def list_service_records_api():
    vehicle_id = request.args.get('vehicle_id')
    records = get_service_records(vehicle_id)
    return jsonify(records)

@app.route('/api/used_parts', methods=['GET'])
def list_used_parts_api():
    service_record_id = request.args.get('service_record_id')
    if not service_record_id:
        return jsonify({"message": "service_record_id parametresi gerekli."}), 400
    parts = get_used_parts_for_service(service_record_id)
    return jsonify(parts)


# Frontend Yönlendirmeleri
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stok-ekle.html')
def stok_ekle():
    return render_template('stok-ekle.html')

@app.route('/stok-listesi.html')
def stok_listesi():
    return render_template('stok-listesi.html')

@app.route('/stok-duzenle.html')
def stok_duzenle():
    return render_template('stok-duzenle.html')

@app.route('/arac-kayit.html')
def arac_kayit():
    return render_template('arac-kayit.html')

@app.route('/arac-gecmisi.html')
def arac_gecmisi():
    return render_template('arac-gecmisi.html')

@app.route('/istatistikler.html')
def istatistikler():
    return render_template('istatistikler.html')

@app.route('/kullanicilar.html')
def kullanicilar():
    return render_template('kullanicilar.html')

@app.route('/ayarlar.html')
def ayarlar():
    return render_template('ayarlar.html')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
