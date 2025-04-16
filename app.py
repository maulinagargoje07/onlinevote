from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.secret_key = 'mauli_secret_key'  # For sessions and flash messages

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Mauli@10",
    database="voting_system1"
)
cursor = db.cursor(buffered=True)

# -------- Admin Auth Decorator --------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            flash("🔒 Admin login required.")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------- Admin Login ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'Mauli' and password == 'Mauli@10':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash("❌ Invalid credentials.")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("✅ Logged out successfully.")
    return redirect(url_for('admin_login'))


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
        voter_id = request.form.get('voter_id')
        candidate_id = request.form.get('candidate_id')

        if not voter_id or not candidate_id:
            flash("⚠️ Both Voter ID and Candidate must be selected.")
            return redirect(url_for('vote', voter_id=voter_id))

        # Check if the voter exists and get their election_id
        cursor.execute("SELECT election_id FROM voters WHERE id = %s", (voter_id,))
        result = cursor.fetchone()

        if not result:
            flash("⚠️ Invalid Voter ID or voter not enrolled in any election.")
            return redirect(url_for('vote'))

        election_id = result[0]

        # Check if candidate belongs to the same election
        cursor.execute("SELECT * FROM candidates WHERE id = %s AND election_id = %s", (candidate_id, election_id))
        valid_candidate = cursor.fetchone()

        if not valid_candidate:
            flash("⚠️ You cannot vote for a candidate in another election.")
            return redirect(url_for('vote', voter_id=voter_id))

        # Check if voter already voted
        cursor.execute("SELECT * FROM votes WHERE voter_id = %s AND candidate_id = %s", (voter_id, candidate_id))
        vote_exists = cursor.fetchone()
        if vote_exists:
            flash("⚠️ You have already voted in this election.")
        else:
            cursor.execute("INSERT INTO votes (voter_id, candidate_id) VALUES (%s, %s)", (voter_id, candidate_id))
            db.commit()
            flash("✅ Vote cast successfully!")

        return redirect(url_for('vote'))

    # GET request: Show form and candidates if voter ID is present
    voter_id = request.args.get('voter_id')
    candidates = []
    voter_found = False

    if voter_id:
        cursor.execute("SELECT election_id FROM voters WHERE id = %s", (voter_id,))
        result = cursor.fetchone()
        if result:
            voter_found = True
            election_id = result[0]
            cursor.execute("SELECT id, name FROM candidates WHERE election_id = %s", (election_id,))
            candidates = cursor.fetchall()

    return render_template('vote.html', candidates=candidates, voter_id=voter_id, voter_found=voter_found)




# ---------- Admin Dashboard ----------
@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')


# ---------- Election Management ----------
@app.route('/admin/elections')
@admin_required
def admin_elections():
    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()
    return render_template('elections.html', elections=elections)

@app.route('/admin/elections/add', methods=['POST'])
@admin_required
def add_election():
    name = request.form['name']
    cursor.execute("INSERT INTO elections (name) VALUES (%s)", (name,))
    db.commit()
    return redirect(url_for('admin_elections'))

@app.route('/admin/elections/delete/<int:id>')
@admin_required
def delete_election(id):
    cursor.execute("DELETE FROM elections WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('admin_elections'))

@app.route('/admin/elections/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
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


# ---------- Voter Viewing ----------
# ---------- Voter Viewing and Deletion ----------
@app.route('/admin/voters')
def view_voters():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor.execute("""
        SELECT voters.id, voters.name, voters.email, voters.age, elections.name
        FROM voters
        JOIN elections ON voters.election_id = elections.id
    """)
    voters = cursor.fetchall()
    return render_template('voters.html', voters=voters)

@app.route('/admin/voters/delete/<int:id>')
def delete_voter(id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor.execute("DELETE FROM voters WHERE id = %s", (id,))
    db.commit()
    flash("✅ Voter deleted successfully!")
    return redirect(url_for('view_voters'))



# ---------- View Election Results ----------
@app.route('/results', methods=['GET', 'POST'])
@admin_required
def results():
    selected_election = None
    if request.method == 'POST':
        selected_election = request.form['election_id']

    cursor.execute("SELECT * FROM elections")
    elections = cursor.fetchall()

    if selected_election:
        cursor.execute("""
            SELECT elections.name AS election_name,
                   candidates.name AS candidate_name,
                   COUNT(votes.id) AS vote_count
            FROM candidates
            LEFT JOIN votes ON candidates.id = votes.candidate_id
            JOIN elections ON candidates.election_id = elections.id
            WHERE elections.id = %s
            GROUP BY candidates.id, elections.name
            ORDER BY vote_count DESC;
        """, (selected_election,))
    else:
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
    return render_template('results.html', results=results, elections=elections, selected_election=selected_election)

# ---------- Reset All Results ----------
@app.route('/admin/results/reset', methods=['POST'])
def reset_results():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    cursor.execute("DELETE FROM votes")
    db.commit()
    flash("✅ All results have been reset successfully.")
    return redirect(url_for('results'))



# ---------- Candidate Management ----------
@app.route('/admin/candidates')
@admin_required
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
@admin_required
def add_candidate():
    name = request.form['name']
    election_id = request.form['election_id']
    cursor.execute("INSERT INTO candidates (name, election_id) VALUES (%s, %s)", (name, election_id))
    db.commit()
    return redirect(url_for('view_candidates'))

@app.route('/admin/candidates/delete/<int:id>')
@admin_required
def delete_candidate(id):
    cursor.execute("DELETE FROM candidates WHERE id = %s", (id,))
    db.commit()
    return redirect(url_for('view_candidates'))

@app.route('/admin/candidates/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
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


# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)
