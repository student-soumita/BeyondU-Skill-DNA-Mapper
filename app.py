import sqlite3
import os
import datetime
import json
import smtplib
import ssl
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, render_template_string
from functools import wraps
import random
from io import BytesIO
from reportlab.platypus import Image
from flask import send_file
from werkzeug.utils import secure_filename

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from chatbot import PathOracleBot

app = Flask(__name__)
app.secret_key = 'beyondu_super_secret_key' 

# --- EMAIL CONFIGURATION ---
# (Kept for other potential uses, but bypassed for local password resets)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'      
app.config['MAIL_PASSWORD'] = 'your_app_password_here'    

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

try:
    with open('bot_config.json', 'r') as config_file:
        bot_config = json.load(config_file)
except Exception as e:
    print(f"Warning: Could not load bot_config.json: {e}")
    bot_config = {}

bot = PathOracleBot()

DATABASE = "beyondu.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE,
                reset_token TEXT,
                bio TEXT,
                target_role TEXT,
                profile_photo TEXT,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                career_dna_score INTEGER DEFAULT 0
            )
        """)

        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]

        if "profile_photo" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
        if "xp" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
        if "streak" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
        if "career_dna_score" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN career_dna_score INTEGER DEFAULT 0")
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT ")
        if "reset_token" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                category TEXT NOT NULL,
                current_level INTEGER NOT NULL,
                target_level INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                role_name TEXT NOT NULL,
                required_score INTEGER NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                xp_reward INTEGER NOT NULL,
                explanation TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_challenges_completed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                challenge_id INTEGER NOT NULL,
                completed_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (challenge_id) REFERENCES challenges(id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                project_description TEXT NOT NULL,
                technologies TEXT NOT NULL,
                github_link TEXT,
                difficulty TEXT,
                resume_score INTEGER,
                interview_score INTEGER,
                overall_score REAL,
                strengths TEXT,
                weaknesses TEXT,
                recommendations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        count = conn.execute("SELECT COUNT(*) FROM company_roles").fetchone()[0]
        if count == 0:
            companies = [
                ("Google", "Software Engineer", 90), ("Google", "AI Engineer", 92),
                ("Microsoft", "Software Engineer", 85), ("Microsoft", "Cloud Engineer", 86),
                ("Amazon", "SDE", 88), ("Amazon", "Data Engineer", 87),
                ("Meta", "Frontend Engineer", 86), ("Meta", "Backend Engineer", 90),
                ("Netflix", "Backend Engineer", 92), ("Adobe", "Software Engineer", 82),
                ("Apple", "iOS Engineer", 91), ("NVIDIA", "AI Engineer", 94),
                ("Tesla", "Software Engineer", 89), ("IBM", "AI Engineer", 80),
                ("Oracle", "Database Engineer", 81), ("Intel", "Embedded Engineer", 83),
                ("Infosys", "Software Engineer", 65), ("TCS", "Software Engineer", 60),
                ("Wipro", "Software Engineer", 60), ("Accenture", "Software Engineer", 68),
                ("Capgemini", "Analyst", 63), ("Deloitte", "Technology Consultant", 72)
            ]
            conn.executemany("""
                INSERT INTO company_roles (company_name, role_name, required_score)
                VALUES (?, ?, ?)
            """, companies)

        count_challenges = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
        if count_challenges == 0:
            challenges_deck = [
                ("Technical Skill", "What is the primary performance benefit of implementing database indexing?", "Reduces physical storage space requirements", "Decreases response latency for data retrieval search queries", "Automatically normalizes relational tables", "Prevents SQL Injection attacks implicitly", "B", 25, "Indexing structures accelerate search operations by preventing costly sequential full-table scans."),
                ("Creative Skill", "When designing high-accessibility Dark Mode interfaces, how is extreme visual fatigue prevented?", "Using absolute pure pitch black #000000 background cards against stark neon text elements", "Utilizing soft, high-range desaturated dark gray hues to reduce high contrast strain", "Increasing global text scale sizing to structural headers only", "Inverting standard imagery palettes automatically across components", "B", 30, "Desaturated dark grays reduce the high contrast emission glare that causes visual fatigue over long usage periods."),
                ("Soft Skill", "An internal stakeholder complains loudly during an cross-functional sync about project delays. How should you respond?", "Defend operations immediately by shifting blame factors to unexpected external API downtime vectors", "Acknowledge structural frustration, document baseline issues calmly, and isolate a precise troubleshooting sequence offline", "Ignore individual commentary to maintain momentum through slated presentation slides", "Escalate individual behavior parameters directly to system management human resources components", "B", 20, "Active de-escalation validates stakeholder impact concerns while maintaining group meeting velocity and structure."),
                ("Technical Skill", "Which structural design paradigm guarantees distributed network infrastructure resilience against centralized failures?", "Monolithic Architecture Design", "Microservices Deployment Topologies", "Single Database Reference Hubs", "Synchronous Sequential Process Pipelines", "B", 25, "Isolating service domain scopes into microservices nodes stops localized faults from crashing the entire system."),
                ("Creative Skill", "In UI design, what functional objective does proper composition hierarchy layout execute?", "Maximizing raw structural pixel density grids", "Guiding user optical focus naturally toward intended focal action sequences", "Forcing explicit balance across asymmetry coordinates", "Reducing global image asset scaling requirements", "B", 30, "Visual hierarchy controls relative element importance using scale, color weight, and spacing configurations to capture user focus.")
            ]
            conn.executemany("""
                INSERT INTO challenges (category, question, option_a, option_b, option_c, option_d, correct_option, xp_reward, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, challenges_deck)

        conn.commit()

# =====================================================================
# EMAIL UTILITY
# =====================================================================
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], context=context) as server:
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.sendmail(app.config['MAIL_USERNAME'], to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

# =====================================================================
# SYSTEM HOOKS & GUARDS
# =====================================================================
@app.before_request
def initialize_database_before_first_request():
    init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    profile_photo = None
    if 'user_id' in session:
        try:
            with get_db() as conn:
                user = conn.execute(
                    "SELECT profile_photo FROM users WHERE id = ?",
                    (session['user_id'],)
                ).fetchone()
                if user:
                    profile_photo = user["profile_photo"]
        except sqlite3.OperationalError:
            session.clear()
    return dict(current_username=session.get('username', 'Profile'), current_profile_photo=profile_photo)


# =====================================================================
# AUTHENTICATION ROUTING SYSTEM
# =====================================================================
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/intro')

@app.route('/intro')
def intro():
    return render_template('intro.html')

@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    email = data.get('email', '').strip()
    action = data.get('action', 'login')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400

    with get_db() as conn:
        if action == 'register':
            if not email:
                return jsonify({'success': False, 'message': 'Email is strictly required for registration.'}), 400
                
            user_by_name = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user_by_name:
                return jsonify({'success': False, 'message': 'Username is already taken.'}), 400
                
            user_by_email = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            if user_by_email:
                return jsonify({'success': False, 'message': 'Email is already registered.'}), 400
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password, email, bio, target_role) 
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password, email, 'Customize your professional biography statement...', 'Unassigned Focus Path'))
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Registration successful! You can now log in.'})
            
        else: # Regular Login
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                return jsonify({'success': True, 'redirect': url_for('dashboard_page')})
            else:
                return jsonify({'success': False, 'message': 'Invalid credentials provided.'}), 401

@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password are required."
        }), 400

    with get_db() as conn:

        user = conn.execute(
            "SELECT id FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Username not found."
            }), 404

        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (password, user["id"])
        )

        conn.commit()

    return jsonify({
        "success": True,
        "message": "Password updated successfully."
    })

@app.route('/logout')
def logout_action():
    session.clear()
    return redirect(url_for('login_page'))

# =====================================================================
# CORE USER INTERFACE TEMPLATE ROUTINGS
# =====================================================================
@app.route('/dashboard')
@login_required
def dashboard_page():
    user_id = session["user_id"]
    with get_db() as conn:
        skills = conn.execute("SELECT current_level FROM user_skills WHERE user_id=?", (user_id,)).fetchall()

    if skills:
        dna_score = round(sum(skill["current_level"] for skill in skills) / len(skills), 1)
    else:
        dna_score = 0

    return render_template("dashboard.html", dna_score=dna_score)

@app.route('/skill-map')
@app.route('/skill_map')
@login_required
def skill_map_page():
    return render_template('skill_map.html')

@app.route('/hidden-talents')
@login_required
def hidden_talents_page():
    user_id = session['user_id']
    with get_db() as conn:
        skills = conn.execute('SELECT skill_name, current_level, target_level, category FROM user_skills WHERE user_id = ?', (user_id,)).fetchall()
    talents = discover_hidden_talents(skills)
    return render_template('hidden_talents.html', talents=talents)

def discover_hidden_talents(skills):
    if not skills:
        return [{"title": "🌱 Blank Canvas", "description": "Add some skills to your profile map to begin discovering your hidden talents!"}]
    talents = []
    skill_levels = {s["skill_name"].lower(): s["current_level"] for s in skills}
    categories = {}
    
    for s in skills:
        cat = s["category"].lower()
        categories.setdefault(cat, []).append(s["current_level"])

    tech_list = categories.get("technical", [])
    avg_technical = sum(tech_list) / len(tech_list) if tech_list else 0

    soft_list = categories.get("soft", [])
    avg_soft = sum(soft_list) / len(soft_list) if soft_list else 0

    creative_list = categories.get("creative", [])
    avg_creative = sum(creative_list) / len(creative_list) if creative_list else 0

    highest_avg = max(avg_technical, avg_soft, avg_creative)

    if avg_technical >= 70:
        talents.append({"title": "🧠 Hidden Talent: Engineering Architect", "description": "Your consistently strong technical skills indicate natural aptitude for Software Engineering, AI, Cybersecurity or System Architecture."})
    elif avg_technical >= 40 or (highest_avg == avg_technical and avg_technical > 0):
        talents.append({"title": "🛠️ Emerging Talent: Technical Builder", "description": "You are showing an active inclination towards technical concepts. Keep building your proficiency to unlock Architect-level insights."})

    if avg_soft >= 70:
        talents.append({"title": "👑 Hidden Talent: Leadership Potential", "description": "Your communication and interpersonal abilities suggest strong potential for Product Management, Team Leadership and Entrepreneurship."})
    elif avg_soft >= 40 or (highest_avg == avg_soft and avg_soft > 0):
        talents.append({"title": "🤝 Emerging Talent: Team Connector", "description": "You have a budding foundation in soft skills. Developing these further will lead to strong leadership and management capabilities."})

    if avg_creative >= 70:
        talents.append({"title": "🎨 Hidden Talent: Creative Innovator", "description": "Your creative profile suggests strong potential in UI/UX Design, Content Creation, Branding and Product Design."})
    elif avg_creative >= 40 or (highest_avg == avg_creative and avg_creative > 0):
        talents.append({"title": "🖌️ Emerging Talent: Design Thinker", "description": "You are exploring the creative domain. Cultivate this aesthetic foundation to unlock advanced innovation potential."})

    if skill_levels.get("python", 0) >= 50 and skill_levels.get("problem solving", 0) >= 50:
        talents.append({"title": "🚀 Hidden Talent: AI & Data Science", "description": "The combination of Programming and Problem Solving indicates strong aptitude for Machine Learning, Data Science and Artificial Intelligence."})

    if skill_levels.get("html", 0) >= 40 and skill_levels.get("css", 0) >= 40 and skill_levels.get("javascript", 0) >= 40:
        talents.append({"title": "💻 Hidden Talent: Full Stack Developer", "description": "Your web development foundation indicates strong potential for becoming a Full Stack Engineer."})

    if not talents:
        talents.append({"title": "🌱 Potential Awaiting Discovery", "description": "Continue adding more skills and updating their levels to generate high-fidelity career insights."})

    return talents

def calculate_career_dna(user_id):
    with get_db() as conn:
        skills = conn.execute("SELECT current_level, target_level FROM user_skills WHERE user_id = ?", (user_id,)).fetchall()
        if not skills:
            conn.execute("UPDATE users SET career_dna_score = 0 WHERE id = ?", (user_id,))
            conn.commit()
            return 0

        current_avg = sum(skill["current_level"] for skill in skills) / len(skills)
        gap_avg = sum(max(skill["target_level"] - skill["current_level"], 0) for skill in skills) / len(skills)

        dna_score = round(current_avg - (gap_avg * 0.25))
        dna_score = max(0, min(100, dna_score))

        conn.execute("UPDATE users SET career_dna_score = ? WHERE id = ?", (dna_score, user_id))
        conn.commit()
    return dna_score

@app.route('/recommendations')
@login_required
def recommendations_page():
    return render_template('recommendations.html')

@app.route('/analytics')
@login_required
def analytics_page():
    return render_template('analytics.html')

@app.route('/company-match')
@login_required
def company_match_page():
    return render_template('company_match.html')

@app.route('/profile')
@login_required
def profile_page():
    user_id = session['user_id']
    with get_db() as conn:
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return render_template('profile.html', user=user_data)

@app.route('/pathoracle')
@login_required
def career_mentor_page():
    user_id = session['user_id']
    with get_db() as conn:
        history_count = conn.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (user_id,)).fetchone()[0]
        if history_count == 0:
            welcome_msg = (
                "Hello! I am PathOracle, your personalized AI Career Mentor.\n\n"
                "Here are some specific ways I can assist you today:\n\n"
                "📚 **Learning Sources:** Ask me to 'Recommend resources to master System Design.'\n"
                "📄 **Resume Maker & Review:** Ask me to 'Help structure my resume for a backend developer role.'\n"
                "🎯 **Interview Guidance:** Ask me to 'Run a mock interview for an AI Engineer position.'\n\n"
                "How can we boost your career today?"
            )
            conn.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)", (user_id, "ai", welcome_msg))
            conn.commit()
    return render_template("career_mentor.html")

# =====================================================================
# BACKEND TELEMETRY & MANAGEMENT API CHANNELS
# =====================================================================

@app.route('/api/skills/user', methods=['GET'])
@login_required
def get_user_skills():
    user_id = session['user_id']
    with get_db() as conn:
        skills = conn.execute('SELECT id, skill_name AS name, category, current_level, target_level FROM user_skills WHERE user_id = ?', (user_id,)).fetchall()
        return jsonify([dict(row) for row in skills])

@app.route('/api/skills/add', methods=['POST'])
@login_required
def add_custom_skill():
    user_id = session['user_id']
    data = request.get_json()
    name = data.get('name', '').strip()
    category = data.get('category', 'Technical')
    current = max(0, min(100, int(data.get('current_level', 1))))
    target = max(0, min(100, int(data.get('target_level', 1))))

    if not name:
        return jsonify({"error": "Skill name cannot be empty"}), 400

    with get_db() as conn:
        conn.execute('INSERT INTO user_skills (user_id, skill_name, category, current_level, target_level) VALUES (?, ?, ?, ?, ?)', (user_id, name, category, current, target))
        conn.commit()
    return jsonify({"success": True})

@app.route('/update-skill', methods=['POST'])
@app.route('/api/skills/update', methods=['POST'])
@login_required
def update_skill():
    data = request.get_json() or {}
    user_id = session['user_id']
    skill_id = data.get('skill_id')
    name = (data.get('name') or '').strip()
    category = data.get('category', 'Technical')

    try:
        current = int(data.get('current_level', 0))
        target = int(data.get('target_level', 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid numeric values"}), 400

    current = max(0, min(100, current))
    target = max(0, min(100, target))

    if not skill_id:
        return jsonify({"success": False, "error": "Missing skill_id"}), 400

    with get_db() as conn:
        cursor = conn.execute('UPDATE user_skills SET skill_name = ?, category = ?, current_level = ?, target_level = ? WHERE id = ? AND user_id = ?', (name, category, current, target, skill_id, user_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "error": "Skill not found"}), 404
    return jsonify({"success": True})

@app.route('/api/skills/delete/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_custom_skill(skill_id):
    user_id = session['user_id']
    with get_db() as conn:
        conn.execute('DELETE FROM user_skills WHERE id = ? AND user_id = ?', (skill_id, user_id))
        conn.commit()
    return jsonify({"success": True})

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    user_id = session['user_id']
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        bio = request.form.get('bio', user['bio'])
        target_role = request.form.get('target_role', user['target_role'])
        new_username = request.form.get('username', user['username'])
        photo_path = user['profile_photo']

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename:
                filename = secure_filename(f"user_{user_id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = f"/static/uploads/{filename}"

        conn.execute("""
            UPDATE users SET username = ?, bio = ?, target_role = ?, profile_photo = ? WHERE id = ?
        """, (new_username, bio, target_role, photo_path, user_id))
        conn.commit()

    session['username'] = new_username
    return redirect(url_for('profile_page'))

@app.route('/api/profile/remove_photo', methods=['POST'])
@login_required
def remove_photo():
    with get_db() as conn:
        conn.execute('UPDATE users SET profile_photo = NULL WHERE id = ?', (session['user_id'],))
        conn.commit()
    return redirect(url_for('profile_page'))

@app.route('/api/recommendations', methods=['GET'])
@login_required
def get_ai_recommendations():
    user_id = session['user_id']
    with get_db() as conn:
        user = conn.execute('SELECT target_role FROM users WHERE id = ?', (user_id,)).fetchone()
        skills = conn.execute('SELECT skill_name, current_level, target_level, category FROM user_skills WHERE user_id = ?', (user_id,)).fetchall()
    
    role = user['target_role'] if user and user['target_role'] else "Unassigned System Role"
    recommendations = []

    if not skills:
        return jsonify([{"title": "🔴 CRITICAL ACTION REQUIRED: SYSTEM ROADMAP ARCHITECTURE EMPTY", "description": "The analytics matrix has no metrics to evaluate. You must add skills on your profile map to generate high-fidelity guidance data."}])

    for s in skills:
        gap = s['target_level'] - s['current_level']
        if gap > 0:
            if gap > 40:
                priority = "🔥 HIGH PRIORITY STRATEGIC DEFICIT"
                est_hours = gap * 5
                strategy = "Fundamental reconstruction required. Allocate primary focus to core conceptual blocks before moving onto advanced engineering tasks."
            elif gap > 15:
                priority = "⚡ TACTICAL DEVELOPMENT GAP"
                est_hours = gap * 3
                strategy = "Immersive implementation needed. Integrate hands-on design sprints and system testing cycles to reinforce operational consistency."
            else:
                priority = "📈 FINE-TUNING REFINEMENT MILESTONE"
                est_hours = gap * 2
                strategy = "Optimization execution. Focus on peer review documentation, framework edge cases, and minimizing runtime overhead."

            recommendations.append({"title": f"{priority}: {s['skill_name'].upper()} GRAPH DISCREPANCY", "description": f"An evaluation gap of {gap} units was found between current tracking level ({s['current_level']}/100) and target tracking level ({s['target_level']}/100) on your {s['category']} trajectory. Strategy: {strategy} Plan for approximately {est_hours} hours of applied learning milestones to bridge this metric variance."})

    if not recommendations:
        recommendations.append({"title": "👑 PEER INDUSTRIAL STANDARD REACHED", "description": f"All measured parameters align with standard thresholds for a {role}. Transition into structural system maintenance and begin tracking alternative development paths."})

    return jsonify(recommendations)

@app.route('/api/hidden-talents', methods=['GET'])
@login_required
def get_hidden_talents():
    user_id = session['user_id']
    with get_db() as conn:
        skills = conn.execute('SELECT skill_name, current_level, target_level, category FROM user_skills WHERE user_id = ?', (user_id,)).fetchall()
    talents = discover_hidden_talents(skills)
    return jsonify(talents)

@app.route("/api/company-match")
@login_required
def company_match():
    user_id = session["user_id"]
    with get_db() as conn:
        skills = conn.execute("SELECT current_level FROM user_skills WHERE user_id=?", (user_id,)).fetchall()
        companies = conn.execute("SELECT company_name, role_name, required_score FROM company_roles ORDER BY required_score DESC").fetchall()

    dna_score = round(sum(skill["current_level"] for skill in skills) / len(skills), 1) if skills else 0
    results = []

    for company in companies:
        required = company["required_score"]
        
        # Core fix: default properties to 0 / restricted messaging if skills are missing
        if not skills:
            compatibility = 0
            verdict = "Add skills to unlock matches"
        else:
            compatibility = max(0, 100 - abs(required - dna_score))
            if compatibility >= 95: verdict = "Excellent Match"
            elif compatibility >= 85: verdict = "Strong Match"
            elif compatibility >= 70: verdict = "Good Match"
            elif compatibility >= 50: verdict = "Possible Match"
            else: verdict = "Need More Skills"

        results.append({
            "company": company["company_name"], "role": company["role_name"],
            "required_score": required, "your_score": dna_score,
            "compatibility": compatibility, "verdict": verdict
        })

    results.sort(key=lambda x: x["compatibility"], reverse=True)
    return jsonify(results[:10])

@app.route('/api/career-dna', methods=['GET'])
@login_required
def get_career_dna():
    user_id = session['user_id']
    dna = calculate_career_dna(user_id)
    return jsonify({"career_dna_score": dna})

# =====================================================================
# MASTERY EVALUATION (CHALLENGE API)
# =====================================================================
KNOWLEDGE_BASE = {
    "Technical": {
        "Level1": [{"q": "What is the primary purpose of a variable in programming?", "options": ["Data storage", "Styling", "Printing"], "ans": "Data storage"}],
        "Level2": [{"q": "Which data structure follows LIFO?", "options": ["Queue", "Stack", "Array"], "ans": "Stack"}],
        "Level3": [{"q": "Explain Big O complexity for nested loops.", "options": ["O(n)", "O(n^2)", "O(1)"], "ans": "O(n^2)"}]
    },
    "Soft": {
        "Level1": [{"q": "How do you handle a difference of opinion in a team?", "options": ["Ignore", "Debate calmly", "Quit"], "ans": "Debate calmly"}],
        "Level2": [{"q": "What is the most effective way to give feedback?", "options": ["Publicly", "Constructively", "Via email"], "ans": "Constructively"}],
        "Level3": [{"q": "Define the balance between empathy and assertiveness.", "options": ["Balanced leadership", "Passive", "Aggressive"], "ans": "Balanced leadership"}]
    },
    "Creative": {
        "Level1": [{"q": "What does UI stand for in digital product design?", "options": ["User Interface", "User Integration", "Universal Industry"], "ans": "User Interface"}],
        "Level2": [{"q": "Which design principle focuses on creating visual weight and order?", "options": ["Hierarchy", "Compression", "Velocity"], "ans": "Hierarchy"}],
        "Level3": [{"q": "What is the primary purpose of a design system wireframe archetype?", "options": ["Establishing layout flow and structure", "Finalizing color hex codes", "Compiling production source code"], "ans": "Establishing layout flow and structure"}]
    }
}

def get_skill_category(skill_name):
    name_lower = skill_name.lower()
    creative_keywords = ["design", "ui", "ux", "creative", "branding", "art", "content", "video", "graphics", "drawing", "illustration"]
    technical_keywords = ["python", "coding", "logic", "data", "architecture", "html", "css", "javascript", "programming", "sql", "developer"]
    if any(k in name_lower for k in creative_keywords): return "Creative"
    if any(k in name_lower for k in technical_keywords): return "Technical"
    return "Soft"

@app.route('/api/challenge/generate', methods=['POST'])
@login_required
def generate_challenge():
    data = request.json
    skill_name = data.get('skill_name', '')
    level = data.get('current_level', 0)
    cat = get_skill_category(skill_name)
    
    if level < 30: diff = "Level1"
    elif level < 70: diff = "Level2"
    else: diff = "Level3"
    
    pool = KNOWLEDGE_BASE.get(cat, {}).get(diff, [])
    question = random.choice(pool) if pool else {"q": "Question pending development.", "options": ["N/A"], "ans": "N/A"}
    
    return jsonify({
        "question": question['q'], "options": question['options'], "correct": question['ans'],
        "difficulty_multiplier": 1.0 if diff == "Level1" else (1.5 if diff == "Level2" else 2.0)
    })

@app.route('/api/challenge/evaluate', methods=['POST'])
@login_required
def evaluate_challenge():
    data = request.get_json() or {}
    return jsonify({"success": True, "score": data.get("score")})

@app.route('/challenge/<int:skill_id>')
@login_required
def challenge_page(skill_id):
    user_id = session['user_id']
    with get_db() as conn:
        skill = conn.execute('SELECT id, skill_name, category, current_level, target_level FROM user_skills WHERE id = ? AND user_id = ?', (skill_id, user_id)).fetchone()
    if not skill: return "Skill not found.", 404
    return render_template('challenge.html', skill=skill)

@app.route("/download/report")
@login_required
def download_report():
    user_id = session["user_id"]
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        skills = conn.execute("SELECT skill_name, category, current_level, target_level FROM user_skills WHERE user_id = ?", (user_id,)).fetchall()

    score = sum(skill["current_level"] for skill in skills) / len(skills) if skills else 0
    talents = discover_hidden_talents(skills)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    logo_path = os.path.join(app.root_path, "static", "images", "default-avatar.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=85, height=85)
        logo.hAlign = "CENTER"
        elements.append(logo)

    elements.append(Spacer(1, 10))
    title = Paragraph("<b><font size='20'>BeyondU Skill DNA Report</font></b>", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"<b>Name:</b> {user['username']}", styles["BodyText"]))
    elements.append(Paragraph(f"<b>Target Role:</b> {user['target_role']}", styles["BodyText"]))
    elements.append(Paragraph(f"<b>Overall Skill Score:</b> {score:.1f}/100", styles["BodyText"]))
    elements.append(Spacer(1, 20))

    data = [["Skill", "Category", "Current", "Target", "Gap"]]
    for skill in skills:
        data.append([skill["skill_name"], skill["category"], str(skill["current_level"]), str(skill["target_level"]), str(skill["target_level"] - skill["current_level"])])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6D28D9")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10), ("GRID", (0, 0), (-1, -1), 1, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("TOPPADDING", (0, 1), (-1, -1), 6), ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<b>Hidden Talents</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    for talent in talents:
        elements.append(Paragraph(talent["title"], styles["Heading3"]))
        elements.append(Paragraph(talent["description"], styles["BodyText"]))
        elements.append(Spacer(1, 8))

    elements.append(Spacer(1, 25))
    elements.append(Paragraph("<i>Generated by BeyondU Skill DNA Mapper</i>", styles["Italic"]))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="BeyondU_Skill_DNA_Report.pdf", mimetype="application/pdf")

# ==========================================================
# PATHORACLE AI CHATBOT API
# ==========================================================
@app.route("/api/pathoracle/chat", methods=["POST"])
@login_required
def pathoracle_chat():
    user_id = session["user_id"]
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please enter a message."})

    try:
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            skills = conn.execute("SELECT skill_name, category, current_level, target_level FROM user_skills WHERE user_id = ?", (user_id,)).fetchall()
            user_dict = dict(user) if user else {}
            skills_list = [dict(skill) for skill in skills]
            reply = bot.get_response(message=message, user=user_dict, skills=skills_list)
            return jsonify({"reply": reply})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"reply": str(e)}), 500

@app.route('/daily-challenge')
@login_required
def daily_challenge_page():
    user_id = session.get('user_id')
    current_date = datetime.date.today().strftime('%Y-%m-%d')
    with get_db() as conn:
        user_stats = conn.execute("SELECT xp, streak, username, profile_photo FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_stats:
            session.clear()
            return redirect(url_for('login_page'))
        completed_today = conn.execute("SELECT 1 FROM user_challenges_completed WHERE user_id = ? AND completed_date = ?", (user_id, current_date)).fetchone()
        
        challenge_data = None
        if not completed_today:
            challenge_data = conn.execute("SELECT * FROM challenges WHERE id NOT IN (SELECT challenge_id FROM user_challenges_completed WHERE user_id = ?) ORDER BY RANDOM() LIMIT 1", (user_id,)).fetchone()
            if not challenge_data:
                challenge_data = conn.execute("SELECT * FROM challenges ORDER BY RANDOM() LIMIT 1").fetchone()
                
    return render_template('daily_challenge.html', user=user_stats, challenge=challenge_data, completed_today=bool(completed_today), current_username=user_stats['username'], current_profile_photo=user_stats['profile_photo'])

@app.route('/api/daily-challenge/submit', methods=['POST'])
@login_required
def submit_challenge_evaluation():
    user_id = session.get('user_id')
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    selected_choice = data.get('selected_option')
    current_date = datetime.date.today().strftime('%Y-%m-%d')
    
    with get_db() as conn:
        already_done = conn.execute("SELECT 1 FROM user_challenges_completed WHERE user_id = ? AND completed_date = ?", (user_id, current_date)).fetchone()
        if already_done: return jsonify({"status": "error", "message": "Daily entry quota filled already!"}), 400
            
        challenge = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
        if not challenge: return jsonify({"status": "error", "message": "Invalid challenge target identification"}), 404
            
        is_correct = (selected_choice == challenge['correct_option'])
        if is_correct:
            conn.execute("UPDATE users SET xp = xp + ?, streak = streak + 1 WHERE id = ?", (challenge['xp_reward'], user_id))
            conn.execute("INSERT INTO user_challenges_completed (user_id, challenge_id, completed_date) VALUES (?, ?, ?)", (user_id, challenge_id, current_date))
            conn.commit()
            updated_stats = conn.execute("SELECT xp, streak FROM users WHERE id = ?", (user_id,)).fetchone()
            return jsonify({"status": "success", "correct": True, "xp_gained": challenge['xp_reward'], "new_xp": updated_stats['xp'], "new_streak": updated_stats['streak'], "explanation": challenge['explanation']})
        else:
            conn.execute("UPDATE users SET streak = 0 WHERE id = ?", (user_id,))
            conn.commit()
            updated_stats = conn.execute("SELECT xp, streak FROM users WHERE id = ?", (user_id,)).fetchone()
            return jsonify({"status": "success", "correct": False, "new_xp": updated_stats['xp'], "new_streak": 0, "explanation": "Incorrect choice. " + challenge['explanation']})

@app.route("/api/pathoracle/clear", methods=["POST"])
@login_required
def pathoracle_clear():
    user_id = session["user_id"]
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
        return jsonify({"success": True, "message": "Chat history cleared successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/project-reviewer")
@login_required
def project_reviewer_page():
    return render_template("project_reviewer.html")

@app.route("/api/project-review", methods=["POST"])
@login_required
def project_review():
    user_id = session["user_id"]
    if not request.is_json: return jsonify({"error": "Invalid request format"}), 400
    data = request.get_json()
    
    project_name = data.get("project_name", "").strip()
    description = data.get("description", "").strip()
    technologies = data.get("technologies", "").lower()
    github = data.get("github", "").strip()
    description_lower = description.lower()

    architecture_score, technical_score, security_score, database_score = 0, 0, 0, 0
    deployment_score, documentation_score, testing_score, scalability_score = 0, 0, 0, 0
    strengths, weaknesses, recommendations = [], [], []

    if "python" in technologies: technical_score += 15; strengths.append("Python backend development")
    if "flask" in technologies: technical_score += 15; strengths.append("Flask web framework")
    if "html" in technologies: technical_score += 5
    if "css" in technologies: technical_score += 5
    if "javascript" in technologies: technical_score += 10
    if "sqlite" in technologies: database_score += 10
    if "mysql" in technologies: database_score += 12
    if "mongodb" in technologies: database_score += 12

    if "api" in description_lower: architecture_score += 15; strengths.append("REST API architecture")
    if "authentication" in description_lower: architecture_score += 10; security_score += 10; strengths.append("Authentication implemented")
    if "dashboard" in description_lower: architecture_score += 5
    if "ai" in description_lower: architecture_score += 10; strengths.append("AI-powered functionality")

    if "render" in description_lower: deployment_score += 10
    if "railway" in description_lower: deployment_score += 10
    if "vercel" in description_lower: deployment_score += 10
    if github: deployment_score += 5; strengths.append("GitHub repository available")

    if any(word in description_lower for word in ["readme", "documentation", "docs", "setup", "guide"]):
        documentation_score += 10
    else:
        weaknesses.append("README documentation missing")
        recommendations.append("Create a professional README with screenshots")

    if "testing" in description_lower:
        testing_score += 10
    else:
        weaknesses.append("Testing not implemented")
        recommendations.append("Add unit and integration tests")

    if "docker" in technologies:
        scalability_score += 10
        strengths.append("Docker containerization")
    else:
        recommendations.append("Containerize the application using Docker")

    if "redis" in technologies: scalability_score += 8
    if "nginx" in technologies: scalability_score += 8

    overall_score = architecture_score + technical_score + security_score + database_score + deployment_score + documentation_score + testing_score + scalability_score
    overall_score = min(overall_score, 100)
    resume_score = min(overall_score + 5, 100)
    interview_score = min(overall_score + 3, 100)

    if overall_score >= 70: difficulty = "Advanced"
    elif overall_score >= 40: difficulty = "Intermediate"
    else: difficulty = "Beginner"

    if not strengths: strengths.append("Project created successfully")
    if not weaknesses: weaknesses.append("No major weaknesses detected")
    if not recommendations: recommendations.append("Continue improving project complexity")

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO project_reviews
                (user_id, project_name, project_description, technologies, github_link, difficulty, resume_score, interview_score, overall_score, strengths, weaknesses, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, project_name, description, technologies, github, difficulty, resume_score, interview_score, overall_score, "\n".join(strengths), "\n".join(weaknesses), "\n".join(recommendations)))
            conn.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "difficulty": difficulty, "resume_score": resume_score, "interview_score": interview_score,
        "overall_score": overall_score, "strengths": "<br>".join(strengths), "weaknesses": "<br>".join(weaknesses),
        "recommendations": "<br>".join(recommendations)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)