from flask import Flask, Blueprint, jsonify
from flask_cors import CORS
from decouple import config as env_config
import psycopg2
import numpy as np
import datetime

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    SECRET_KEY = env_config('SECRET_KEY')

class DevelopmentConfig(Config):
    DEBUG = True

app.config.from_object(DevelopmentConfig)

# Date format utility
class DateFormat:
    @classmethod
    def convert_date(cls, date):
        return datetime.datetime.strftime(date, '%d/%m/%y')

# Database connection
def get_connection():
    try:
        return psycopg2.connect(
            host=env_config('PGSQL_HOST'), 
            user=env_config('PGSQL_USER'),
            password=env_config('PGSQL_PASSWORD'),
            database=env_config('PGSQL_DATABASE')
        )
    except psycopg2.DatabaseError as ex:
        raise ex

# Record entity
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

# Record model
class RecordModel:
    @classmethod
    def get_records(cls):
        try:
            connection = get_connection()
            records = []
            
            with connection.cursor() as cursor:
                cursor.execute('SELECT id, temperature, humedity, gas_level, light, createdAt FROM record')
                resultset = cursor.fetchall()
                
                for row in resultset:
                    record = Record(row[0], row[1], row[2], row[3], row[4], row[5])
                    records.append(record.to_json())
            
            connection.close()
            return records
        except Exception as ex:
            raise Exception(f"Error getting records: {ex}")
    
    @classmethod
    def get_temperature_statistics(cls):
        try:
            connection = get_connection()
            temperatures = []
            
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT temperature 
                    FROM record 
                    WHERE createdAt >= NOW() - INTERVAL '7 days'
                ''')
                resultset = cursor.fetchall()
                
                for row in resultset:
                    try:
                        temperature = float(row[0])
                        temperatures.append(temperature)
                    except ValueError:
                        # Ignorar valores que no se pueden convertir a float
                        continue
                    
            connection.close()
            
            if not temperatures:
                return {'message': 'No data available for the past week'}
            
            temperatures_array = np.array(temperatures, dtype=float)
            
            statistics = {
                'mean': float(np.mean(temperatures_array)),
                'median': float(np.median(temperatures_array)),
                'std_dev': float(np.std(temperatures_array)),
                'min': float(np.min(temperatures_array)),
                'max': float(np.max(temperatures_array))
            }
            
            return statistics
        except Exception as ex:
            raise Exception(f"Error calculating statistics: {ex}")
    
    @classmethod
    def get_gas_levels(cls):
        try:
            connection = get_connection()
            gas_levels = []
            
            with connection.cursor() as cursor:
                cursor.execute('SELECT gas_level, createdAt FROM record')
                resultset = cursor.fetchall()
                
                for row in resultset:
                    gas_levels.append({
                        'gas_level': row[0],
                        'createdAt': DateFormat.convert_date(row[1])
                    })
            
            connection.close()
            return gas_levels
        except Exception as ex:
            raise Exception(f"Error getting gas levels: {ex}")

# Blueprints
main = Blueprint('record_blueprint', __name__)

@main.route('/')
def get_records():
    try:
        records = RecordModel.get_records()
        return jsonify(records)
    except Exception as ex:
        return jsonify({'message': str(ex)}), 500

@main.route('/temperature-statistics')
def get_temperature_statistics():
    try:
        statistics = RecordModel.get_temperature_statistics()
        return jsonify(statistics)
    except Exception as ex:
        return jsonify({'message': str(ex)}), 500

@main.route('/gas-levels')
def get_gas_levels():
    try:
        gas_levels = RecordModel.get_gas_levels()
        return jsonify(gas_levels)
    except Exception as ex:
        return jsonify({'message': str(ex)}), 500

app.register_blueprint(main, url_prefix='/api/records')

# Error handling
def page_not_found(error):
    return "<h1>No encontrado</h1>", 404

app.register_error_handler(404, page_not_found)

if __name__ == "__main__":
    app.run()
