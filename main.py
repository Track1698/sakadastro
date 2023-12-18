from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from final import backend_function
import traceback  # Import the traceback module
import os
import firebase_admin
from firebase_admin import credentials, db
import traceback



cred = credentials.Certificate("ServiceAccountK.json")
firebase_admin.initialize_app(cred, {'databaseURL': 'https://sakadastro-237b3-default-rtdb.europe-west1.firebasedatabase.app/'})

# Reference to the root of your Firebase Realtime Database
db_ref = db.reference('/')
    
def create_app():
  app = Flask(__name__)
  CORS(app)  # Enable CORS for all routes
  # Error 404 handler
  @app.errorhandler(404)
  def resource_not_found(e):
    return jsonify(error=str(e)), 404
  # Error 405 handler
  @app.errorhandler(405)
  def resource_not_found(e):
    return jsonify(error=str(e)), 405
  # Error 401 handler
  @app.errorhandler(401)
  def custom_401(error):
    return Response("API Key required.", 401)
  
  @app.route("/ping")
  def hello_world():
     return "pong"
 
  @app.route("/")
  def hello_world2():
    return """
        <html>
          <head>
              <style>
                  body {
                      display: flex;
                      align-items: center;
                      justify-content: center;
                      height: 100vh;
                      margin: 0;
                      background-color: #f8f8f8;
                  }

                  h1 {
                      color: red;
                      font-size: 3em;
                      text-align: center;
                  }
              </style>
          </head>
          <body>
              <div>
                  <h1>YOU SHOULDN'T BE HERE!!! </h1>
              </div>
              <div>
                  <h1>GO AWAY OR WE HAVE YOUR IP ADDRESS!!!</h1>
              </div>
          </body>
        </html>
      """
 
  @app.route("/version", methods=["GET"], strict_slashes=False)
  def version():
     response_body = {
       "success": 1,
     }
     return jsonify(response_body)


  @app.route('/api/getinformation', methods=['POST'])
  def getinformation():
    try:
        # Continue with the existing functionality
        data = request.get_json()
        input_kadastr = data.get('input_kadastr')

        # Track the visitor
        if 'X-Forwarded-For' in request.headers:
            # The X-Forwarded-For header can contain a comma-separated list of IP addresses
            # The client's IP address is usually the first one in the list
            ip_address = request.headers['X-Forwarded-For'].split(',')[0].strip()
        else:
            # If the X-Forwarded-For header is not present, fallback to request.remote_addr
            ip_address = request.remote_addr
        visitors_ref = db_ref.child('visitors')
        visitor_snapshot = visitors_ref.order_by_child('ip_address').equal_to(ip_address).get()

        if not visitor_snapshot:
            # If the visitor doesn't exist, add a new entry
            new_visitor_ref = visitors_ref.push({
                'ip_address': ip_address,
                'request_count': 1,
                'input_kadastr_list': [input_kadastr]
            })
        else:
            # If the visitor exists, update the request count and input_kadastr_list
            visitor_key = next(iter(visitor_snapshot))
            new_visitor_ref = visitors_ref.child(visitor_key)
            new_visitor_ref.update({
                'request_count': visitor_snapshot[visitor_key]['request_count'] + 1,
                'input_kadastr_list': visitor_snapshot[visitor_key].get('input_kadastr_list', []) + [input_kadastr]
            })

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
  
  return app

app = create_app()


if __name__ == "__main__":
  #    app = create_app()
  print(" Starting app...")
  app.run(host="0.0.0.0", port=5000)




  


