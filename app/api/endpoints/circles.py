import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.circle import Circle, CircleUser
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/circles", tags=["circles"])


async def get_user_circle_count(user_id: int, db: AsyncSession) -> int:
    """
    Counts how many circles a user belongs to
    """
    return await db.scalar(
        select(func.count()).where(CircleUser.user_id == user_id)
    )


async def ensure_user_can_join_another_circle(user_id: int, db: AsyncSession) -> None:
    """
    Checks the per-user circle limit before creating or joining a circle
    """
    circle_count = await get_user_circle_count(user_id, db)
    if circle_count >= settings.CIRCLE_MAX_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"You can be in max {settings.CIRCLE_MAX_PER_USER} circles",
        )


@router.post("")
async def create_circle(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new circle
    Creator is automatically added as first member
    """
    await ensure_user_can_join_another_circle(current_user.id, db)

    while True:
        invite_code = secrets.token_urlsafe(8) # generate unique invite code
        existing = await db.scalar(
            select(Circle).where(Circle.invite_code == invite_code)
        )
        if not existing:
            break

    circle = Circle(
        name=name,
        invite_code=invite_code,
        created_by=current_user.id
    )
    db.add(circle)
    await db.flush()  # get circle.id before commit

    # add creator as first member
    membership = CircleUser(
        circle_id=circle.id,
        user_id=current_user.id,
        role="creator"
    )
    db.add(membership)
    await db.commit()

    return {
        "id": circle.id,
        "name": circle.name,
        "invite_code": circle.invite_code,
    }

@router.post("/join")
async def join_circle(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Join an existing circle using invite code
    Max 4 members in circle
    """
    # find circle by invite code
    circle = await db.scalar(
        select(Circle).where(Circle.invite_code == invite_code)
    )
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    # check member limit
    member_count = await db.scalar(
        select(func.count()).where(CircleUser.circle_id == circle.id)
    )
    if member_count >= settings.CIRCLE_MAX_MEMBERS:
        raise HTTPException(status_code=400, detail=f"Circle is full (max {settings.CIRCLE_MAX_MEMBERS} members)")

    # check if already a member
    already_member = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle.id,
            CircleUser.user_id == current_user.id
        )
    )
    if already_member:
        raise HTTPException(status_code=400, detail="Already a member of this circle")

    await ensure_user_can_join_another_circle(current_user.id, db)

    membership = CircleUser(
        circle_id=circle.id,
        user_id=current_user.id,
        role="member"
    )
    db.add(membership)
    await db.commit()

    return {"message": "Joined circle", "circle": circle.name}

@router.get("/my")
async def get_my_circles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all circles the user is in
    """
    memberships = await db.scalars(
        select(CircleUser).where(CircleUser.user_id == current_user.id)
    )
    circle_ids = [m.circle_id for m in memberships]

    if not circle_ids:
        return []

    circles = await db.scalars(
        select(Circle).where(Circle.id.in_(circle_ids))
    )
    return [{"id": c.id, "name": c.name, "invite_code": c.invite_code} for c in circles]
