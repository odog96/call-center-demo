from flask import Flask, render_template
import os

PORT = os.getenv('CDSW_APP_PORT', '8090')

app = Flask(__name__)

@app.route("/")
def main():
  
  return render_template('sko_demo_frontend.html')
    
if __name__ == '__main__':
  app.run(host='127.0.0.1', port=PORT)