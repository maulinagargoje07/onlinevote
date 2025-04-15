from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'mauli_secret_key'  # Needed for flashing messages

# DB connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Mauli@10",
    database="voting_system1"
)
cursor = db.cursor(buffered=True)

# ---------- Voter Registration ----------
@app.route('/')
def register():
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    return render_template('register.html', elections=elections)

@app.route('/submit', methods=['POST'])
def submit():
    voter_id = request.form['voter_id']
    name = request.form['name']
    email = request.form['email']
    age = request.form['age']
    election_id = request.form['election']

    cursor.execute("INSERT INTO voters (id, name, email, age, election_id) VALUES (%s, %s, %s, %s, %s)",
                   (voter_id, name, email, age, election_id))
    db.commit()

    flash("✅ Registration Successful!")
    return redirect(url_for('register'))


# ---------- Voting ----------
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        candidate_id = request.form['candidate_id']

        # Check if this voter has already voted in the same election
        cursor.execute("""
            SELECT c.election_id 
            FROM candidates c 
            WHERE c.id = %s
        """, (candidate_id,))
        election_id = cursor.fetchone()[0]

        cursor.execute("""
            SELECT v.id 
            FROM votes v 
            JOIN candidates c ON v.candidate_id = c.id 
            WHERE v.voter_id = %s AND c.election_id = %s
        """, (voter_id, election_id))
        vote_exists = cursor.fetchone()

        if vote_exists:
            flash("⚠️ You have already voted in this election.")
        else:
            cursor.execute("INSERT INTO votes (voter_id, candidate_id) VALUES (%s, %s)", (voter_id, candidate_id))
            db.commit()
            flash("✅ Vote cast successfully!")

        return redirect(url_for('vote'))

    # For GET request
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    cursor.execute("SELECT * FROM candidates")
    candidates = cursor.fetchall()
    cursor.execute("SELECT * FROM voters")
    voters = cursor.fetchall()

    return render_template('vote.html', elections=elections, candidates=candidates, voters=voters)


# ---------- Admin Panel ----------
@app.route('/admin')
def admin():
    return render_template('admin.html')

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

@app.route('/admin/voters')
def view_voters():
    cursor.execute("""
        SELECT voters.id, voters.name, voters.email, voters.age, elections.name
        FROM voters
        JOIN elections ON voters.election_id = elections.id
    """)
    voters = cursor.fetchall()
    return render_template('voters.html', voters=voters)

# View Election Results
@app.route('/results')
def results():
    cursor.execute("""
        SELECT elections.name AS election_name,
               candidates.name AS candidate_name,
               COUNT(votes.id) AS vote_count
        FROM candidates
        LEFT JOIN votes ON candidates.id = votes.candidate_id
        JOIN elections ON candidates.election_id = elections.id
        GROUP BY candidates.id, elections.name
        ORDER BY elections.name, vote_count DESC;
    """)
    results = cursor.fetchall()
    return render_template('results.html', results=results)

# --- Candidate Management ---

@app.route('/admin/candidates')
def view_candidates():
    cursor.execute("""
        SELECT candidates.id, candidates.name, elections.name 
        FROM candidates 
        JOIN elections ON candidates.election_id = elections.id
    """)
    candidates = cursor.fetchall()
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    return render_template('candidates.html', candidates=candidates, elections=elections)

@app.route('/admin/candidates/add', methods=['POST'])
def add_candidate():
    name = request.form['name']
    election_id = request.form['election_id']
    cursor.execute("INSERT INTO candidates (name, election_id) VALUES (%s, %s)", (name, election_id))
    db.commit()
    return redirect(url_for('view_candidates'))

@app.route('/admin/candidates/delete/<int:id>')
def delete_candidate(id):
    cursor.execute("DELETE FROM candidates WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('view_candidates'))

@app.route('/admin/candidates/edit/<int:id>', methods=['GET', 'POST'])
def edit_candidate(id):
    if request.method == 'POST':
        name = request.form['name']
        election_id = request.form['election_id']
        cursor.execute("UPDATE candidates SET name=%s, election_id=%s WHERE id=%s", (name, election_id, id))
        db.commit()
        return redirect(url_for('view_candidates'))
    else:
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,))
        candidate = cursor.fetchone()
        cursor.execute("SELECT * FROM elections")
        elections = cursor.fetchall()
        return render_template('edit_candidate.html', candidate=candidate, elections=elections)


if __name__ == '__main__':
    app.run(debug=True)
