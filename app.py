import requests
from flask import Flask, request, render_template
ON_HEROKU = os.environ.get('ON_HEROKU')

@app.route('/') 
def hello_world():
  return "Hello World"

if __name__ == '__main__':
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    if ON_HEROKU:
      port = int(os.environ.get('PORT', 5000))  # as per OP comments default is 17995 
    else:
      #port = 3000
      port = 8080
    app.run(debug=True, port = port)
