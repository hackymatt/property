"""SQLAlchemy models for scheduler"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for many-to-many relationship between Schedule and Job
schedule_jobs = Table(
    'schedule_jobs',
    Base.metadata,
    Column('schedule_id', Integer, ForeignKey('schedule.id'), primary_key=True),
    Column('job_id', Integer, ForeignKey('job.id'), primary_key=True)
)


class Job(Base):
    """SQLAlchemy model for Job table"""
    __tablename__ = 'job'

    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey('domain.id'))
    source = Column(String(255), nullable=False)
    stage = Column(String(20), nullable=False)
    url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Relationships
    domain = relationship("Domain", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, source='{self.source}', stage='{self.stage}')>"


class Domain(Base):
    """SQLAlchemy model for Domain table"""
    __tablename__ = 'domain'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Relationships
    jobs = relationship("Job", back_populates="domain")

    def __repr__(self):
        return f"<Domain(id={self.id}, name='{self.name}')>"


class Schedule(Base):
    """SQLAlchemy model for Schedule table"""
    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    cron = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Many-to-many relationship with Job
    jobs = relationship("Job", secondary=schedule_jobs, lazy='selectin')

    def __repr__(self):
        return f"<Schedule(id={self.id}, name='{self.name}', next_run={self.next_run})>"
