from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate

db = SQLAlchemy()
ma = Marshmallow()

class Blacklist(db.Model):
    __tablename__ = 'blacklists'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    app_uuid = db.Column(db.String(36), nullable=False)
    blocked_reason = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=False) # Soporta IPv4 e IPv6
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class BlacklistSchema(ma.SQLAlchemyAutoSchema):
    email = fields.Email(required=True, validate=validate.Length(max=120))
    app_uuid = fields.UUID(required=True)
    blocked_reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    ip_address = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

    class Meta:
        model = Blacklist
        load_instance = True
        include_fk = True
        dump_only = ('id', 'ip_address', 'created_at')
