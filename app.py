from flask import Flask, request, jsonify
from flask_cors import CORS
from final import backend_function
import traceback  # Import the traceback module

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/api/your_endpoint', methods=['POST'])
def your_api_endpoint():
    try:
        data = request.get_json()
        input_kadastr = data.get('input_kadastr')
        print('Looking for:', input_kadastr)

        if input_kadastr:
            result = backend_function(input_kadastr)
            print('Success:', result)
            return jsonify(result)
        else:
            return jsonify({"error": "Missing input_kadastr"}), 400

    except Exception as e:
        print('Error:', str(e))
        traceback.print_exc()  # Print the traceback information
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
