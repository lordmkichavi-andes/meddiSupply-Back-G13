from flask import Flask, jsonify, request, make_response
from functools import wraps
import os
import json



app = Flask(__name__)

# Registro de blueprints
from src.blueprints.sales_plans import sales_plans_bp
app.register_blueprint(sales_plans_bp)




@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
