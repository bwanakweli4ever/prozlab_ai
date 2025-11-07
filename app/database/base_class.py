# app/database/base_class.py
from sqlalchemy.ext.declarative import declarative_base

# Simple base class without automatic fields
Base = declarative_base()