from flask import Flask, render_template, request

app = Flask(__name__)
app.debug = True


@app.route('/', methods=['GET'])
def taxon_dropdown():
    taxa = ['47170 (All Fungi)', '... (Ascomycetes)', '... (Basidiomycetes)']
    return render_template('inat_vouchers.html', taxa=taxa)


@app.route('/', methods=['POST'])
def username_entry():
    if request.method == "POST":
        text = request.form['username']
        print(text)
    return text


if __name__ == "__main__":
    app.run()
