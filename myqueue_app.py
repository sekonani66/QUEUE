# myqueue_app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myqueue.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------------
# Database Models
# -------------------------

class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'requester' or 'queuer'
    rating = db.Column(db.Float, default=5.0)

class QueueRequest(db.Model):
    id = db.Column(db.String, primary_key=True)
    requester_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200))
    location = db.Column(db.String(200))
    payment = db.Column(db.Float)
    status = db.Column(db.String(20), default="open")  # open, accepted, completed
    queuer_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------
# Helper Functions
# -------------------------

def generate_id():
    return str(uuid.uuid4())

# -------------------------
# Routes
# -------------------------

@app.route('/')
def home():
    return jsonify({"message": "Welcome to MyQueue API!"})

# --- User Registration ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data.get('name') or not data.get('email') or not data.get('role'):
        return jsonify({"error": "Missing fields"}), 400

    if data['role'] not in ['requester', 'queuer']:
        return jsonify({"error": "Role must be requester or queuer"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400

    new_user = User(
        id=generate_id(),
        name=data['name'],
        email=data['email'],
        role=data['role']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully", "user_id": new_user.id})

# --- Post a Queue Request ---
@app.route('/queue/request', methods=['POST'])
def post_queue_request():
    data = request.get_json()
    requester = User.query.filter_by(id=data.get('requester_id')).first()
    if not requester or requester.role != 'requester':
        return jsonify({"error": "Invalid requester ID"}), 400

    new_request = QueueRequest(
        id=generate_id(),
        requester_id=requester.id,
        description=data.get('description'),
        location=data.get('location'),
        payment=data.get('payment', 0.0)
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({"message": "Queue request created", "request_id": new_request.id})

# --- View All Open Requests (for Queuers) ---
@app.route('/queue/open', methods=['GET'])
def open_requests():
    open_jobs = QueueRequest.query.filter_by(status="open").all()
    return jsonify([
        {
            "id": job.id,
            "description": job.description,
            "location": job.location,
            "payment": job.payment,
            "created_at": job.created_at
        } for job in open_jobs
    ])

# --- Accept a Queue Request ---
@app.route('/queue/accept/<request_id>', methods=['POST'])
def accept_request(request_id):
    data = request.get_json()
    queuer = User.query.filter_by(id=data.get('queuer_id')).first()
    if not queuer or queuer.role != 'queuer':
        return jsonify({"error": "Invalid queuer ID"}), 400

    job = QueueRequest.query.filter_by(id=request_id, status="open").first()
    if not job:
        return jsonify({"error": "Request not found or already accepted"}), 400

    job.status = "accepted"
    job.queuer_id = queuer.id
    db.session.commit()
    return jsonify({"message": "Request accepted", "job_id": job.id})

# --- Complete Queue Job ---
@app.route('/queue/complete/<request_id>', methods=['POST'])
def complete_request(request_id):
    job = QueueRequest.query.filter_by(id=request_id, status="accepted").first()
    if not job:
        return jsonify({"error": "Request not found or not accepted"}), 400

    job.status = "completed"
    db.session.commit()
    return jsonify({"message": "Queue job completed successfully"})

# -------------------------
# Run App
# -------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

