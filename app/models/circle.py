from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Circle(Base):
    __tablename__ = "circles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(20), unique=True)  # unique code to join
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["CircleUser"]] = relationship("CircleUser", back_populates="circle")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])


class CircleUser(Base):
    __tablename__ = "circle_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20), default="member")  # creator or member
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    circle: Mapped["Circle"] = relationship("Circle", back_populates="members")
    user: Mapped["User"] = relationship("User")