from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Association Table for User-Skill Many-to-Many Relationship
class UserSkill(db.Model):
    __tablename__ = 'user_skills'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', on_delete='CASCADE'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id', on_delete='CASCADE'), primary_key=True)
    current_level = db.Column(db.Integer, default=1)  # Scale 1-5
    target_level = db.Column(db.Integer, default=5)   # Scale 1-5
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships to access properties easily
    skill = db.relationship("Skill", back_populates="user_links")
    user = db.relationship("User", back_populates="skill_links")


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship linking to the association table
    skill_links = db.relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Technical', 'Soft', or 'Creative'
    description = db.Column(db.Text, nullable=True)

    # Relationship linking to the association table
    user_links = db.relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")
