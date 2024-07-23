from flask import Flask, jsonify, Blueprint
from flask_cors import CORS
from decouple import config as decouple_config
import datetime
import numpy as np
import pymysql

# Configuración
class Config:
    SECRET_KEY = decouple_config('SECRET_KEY')

class DevelopmentConfig(Config):
    DEBUG = True

config = {
    'development': DevelopmentConfig
}

# Conexión a la base de datos
def get_connection():
    return pymysql.connect(
        host=decouple_config('DB_HOST'),
        user=decouple_config('DB_USER'),
        password=decouple_config('DB_PASSWORD'),
        db=decouple_config('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor
    )

# Formateo de Fechas
class DateFormat:
    @classmethod
    def convert_date(cls, date):
        return datetime.datetime.strftime(date, '%d/%m/%y')

# Modelo de Registro
class Record:
    def __init__(self, id, temperature=None, humedity=None, gas_level=None, light=None, createdAt=None):
        self.id = id
        self.temperature = temperature
        self.humedity = humedity
        self.gas_level = gas_level
        self.light = light
        self.createdAt = createdAt
        
    def to_json(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'humedity': self.humedity,
            'gas_level': self.gas_level,
            'light': self.light,
            'createdAt': DateFormat.convert_date(self.createdAt)
        }

class RecordModel:
    @classmethod
    def get_records(cls):
        connection = get_connection()
        try:
            records = []
            with connection.cursor() as cursor:
                cursor.execute('SELECT id, temperature, humedity, gas_level, light, createdAt FROM record')
                resultset = cursor.fetchall()
                for row in resultset:
                    record = Record(row['id'], row['temperature'], row['humedity'], row['gas_level'], row['light'], row['createdAt'])
                    records.append(record.to_json())
            return records
        except Exception as ex:
            raise Exception(f"Error getting records: {ex}")
        finally:
            connection.close()
    
    @classmethod
    def get_temperature_statistics(cls):
        connection = get_connection()
        try:
            temperatures = []
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT temperature 
                    FROM record 
                    WHERE createdAt >= NOW() - INTERVAL 7 DAY
                ''')
                resultset = cursor.fetchall()
                for row in resultset:
                    temperatures.append(row['temperature'])
                    
            if not temperatures:
                return {'message': 'No data available for the past week'}
            
            temperatures_array = np.array(temperatures, dtype=float)
            counts = np.bincount(temperatures_array.astype(int))
            mode = np.argmax(counts)
            
            statistics = {
                'mean': float(np.mean(temperatures_array)),
                'median': float(np.median(temperatures_array)),
                'std_dev': float(np.std(temperatures_array)),
                'min': float(np.min(temperatures_array)),
                'max': float(np.max(temperatures_array)),
                'mode': float(mode)
            }
            return statistics
        except Exception as ex:
            raise Exception(f"Error calculating statistics: {ex}")
        finally:
            connection.close()

# Aplicación Flask
app = Flask(__name__)
CORS(app)

# Rutas
record_routes = Blueprint('record_blueprint', __name__)

@record_routes.route('/')
def get_records():
    try:
        records = RecordModel.get_records()
        return jsonify(records)
    except Exception as ex:
        return jsonify({'message': str(ex)}), 500

@record_routes.route('/temperature-statistics')
def get_temperature_statistics():
    try:
        statistics = RecordModel.get_temperature_statistics()
        return jsonify(statistics)
    except Exception as ex:
        return jsonify({'message': str(ex)}), 500

# Registro de Blueprints y configuración de errores
app.config.from_object(config['development'])
app.register_blueprint(record_routes, url_prefix='/api/records')

@app.errorhandler(404)
def page_not_found(error):
    return "<h1>No encontrado</h1>", 404

# Inicio de la aplicación
if __name__ == "__main__":
    app.run()
