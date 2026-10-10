'''
python3 -m venv .venv
source .venv/bin/activate #whenever you open new terminal
python -m pip install -r requirements.txt
'''

from flask import Flask, render_template

app = Flask(
    __name__,
    template_folder = "web",
    static_folder="web",
    static_url_path="/static"
)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)