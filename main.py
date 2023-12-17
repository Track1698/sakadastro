from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from final import backend_function
import traceback  # Import the traceback module
import os





    
    
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
     """Example Hello World route."""
     name = os.environ.get("NAME", "World")
     return f"Hello {name}!"
 
  @app.route("/version", methods=["GET"], strict_slashes=False)
  def version():
     response_body = {
       "success": 1,
     }
     return jsonify(response_body)


  @app.route('/api/getinformation', methods=['POST'])
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
  
  return app

app = create_app()


if __name__ == "__main__":
  #    app = create_app()
  print(" Starting app...")
  app.run(host="0.0.0.0", port=5000)




  


