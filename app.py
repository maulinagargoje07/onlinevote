from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# DB connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Mauli@10",  # <-- Change this
    database="voting_system1"
)
cursor = db.cursor()

# Voter Registration Page
@app.route('/')
def register():
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    return render_template('register.html', elections=elections)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    age = request.form['age']
    election_id = request.form['election']
    
    cursor.execute("INSERT INTO voters (name, email, age, election_id) VALUES (%s, %s, %s, %s)",
                   (name, email, age, election_id))
    db.commit()
    
    return "✅ Registration Successful!"


# ---------- Admin Panel ----------

@app.route('/admin')
def admin():
    return render_template('admin.html')

# Elections Management
@app.route('/admin/elections')
def admin_elections():
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    return render_template('elections.html', elections=elections)

@app.route('/admin/elections/add', methods=['POST'])
def add_election():
    name = request.form['name']
    cursor.execute("INSERT INTO elections (name) VALUES (%s)", (name,))
    db.commit()
    return redirect(url_for('admin_elections'))

@app.route('/admin/elections/delete/<int:id>')
def delete_election(id):
    cursor.execute("DELETE FROM elections WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('admin_elections'))

@app.route('/admin/elections/edit/<int:id>', methods=['GET', 'POST'])
def edit_election(id):
    if request.method == 'POST':
        new_name = request.form['name']
        cursor.execute("UPDATE elections SET name = %s WHERE id = %s", (new_name, id))
        db.commit()
        return redirect(url_for('admin_elections'))
    else:
        cursor.execute("SELECT * FROM elections WHERE id = %s", (id,))
        election = cursor.fetchone()
        return render_template('edit_election.html', election=election)

# View Registered Voters
@app.route('/admin/voters')
def view_voters():
    cursor.execute("""
        SELECT voters.id, voters.name, voters.email, voters.age, elections.name
        FROM voters
        JOIN elections ON voters.election_id = elections.id
    """)
    voters = cursor.fetchall()
    return render_template('voters.html', voters=voters)

if __name__ == '__main__':
    app.run(debug=True)
