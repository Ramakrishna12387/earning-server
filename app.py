from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "My Server is Working!"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)