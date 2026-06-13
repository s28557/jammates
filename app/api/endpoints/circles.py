import secrets
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.circle import Circle, CircleUser
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/circles", tags=["circles"])
UPLOAD_DIR = Path("uploads/circles")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def circle_response(circle: Circle) -> dict:
    return {
        "id": circle.id,
        "name": circle.name,
        "invite_code": circle.invite_code,
        "image_url": circle.image_url,
    }


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


async def get_circle_membership(circle_id: int, user_id: int, db: AsyncSession) -> CircleUser:
    membership = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id == user_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this circle")
    return membership


async def get_circle_or_404(circle_id: int, db: AsyncSession) -> Circle:
    circle = await db.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
    return circle


async def ensure_circle_admin(circle_id: int, current_user: User, db: AsyncSession) -> CircleUser:
    membership = await get_circle_membership(circle_id, current_user.id, db)
    if membership.role != "creator":
        raise HTTPException(status_code=403, detail="Only circle admin can do this")
    return membership


async def delete_circle_rows(circle_id: int, db: AsyncSession) -> None:
    memberships = await db.scalars(
        select(CircleUser).where(CircleUser.circle_id == circle_id)
    )
    for membership in memberships:
        await db.delete(membership)

    circle = await get_circle_or_404(circle_id, db)
    await db.delete(circle)


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

    return circle_response(circle)

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
    return [
        {
            "id": c.id,
            "name": c.name,
            "invite_code": c.invite_code,
            "image_url": c.image_url,
        }
        for c in circles
    ]


@router.patch("/{circle_id}/image")
async def update_circle_image(
    circle_id: int,
    image_url: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates circle image. Any circle member can change it.
    """
    await get_circle_membership(circle_id, current_user.id, db)
    circle = await get_circle_or_404(circle_id, db)
    circle.image_url = image_url.strip() if image_url and image_url.strip() else None
    await db.commit()
    await db.refresh(circle)

    return circle_response(circle)


@router.patch("/{circle_id}/name")
async def update_circle_name(
    circle_id: int,
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates circle name. Only circle admin can change it.
    """
    await ensure_circle_admin(circle_id, current_user, db)
    cleaned_name = name.strip()

    if not cleaned_name:
        raise HTTPException(status_code=400, detail="Circle name cannot be empty")

    circle = await get_circle_or_404(circle_id, db)
    circle.name = cleaned_name
    await db.commit()
    await db.refresh(circle)

    return circle_response(circle)


@router.post("/{circle_id}/image/upload")
async def upload_circle_image(
    circle_id: int,
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads circle image from user's device. Any circle member can change it.
    """
    await get_circle_membership(circle_id, current_user.id, db)

    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    if image.size and image.size > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 5 MB)")

    extension = Path(image.filename or "").suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        extension = ".jpg"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{circle_id}_{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / filename

    contents = await image.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 5 MB)")
    file_path.write_bytes(contents)

    circle = await get_circle_or_404(circle_id, db)
    circle.image_url = str(request.url_for("uploads", path=f"circles/{filename}"))
    await db.commit()
    await db.refresh(circle)

    return circle_response(circle)


@router.delete("/{circle_id}/leave", status_code=204)
async def leave_circle(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lets current user leave a circle. If creator leaves, admin role moves to oldest member.
    If this was the last member, the circle is deleted.
    """
    circle = await get_circle_or_404(circle_id, db)
    membership = await get_circle_membership(circle_id, current_user.id, db)

    remaining_members = await db.scalars(
        select(CircleUser)
        .where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id != current_user.id,
        )
        .order_by(CircleUser.joined_at.asc())
    )
    remaining_members = list(remaining_members)

    if not remaining_members:
        await db.delete(membership)
        await db.delete(circle)
        await db.commit()
        return None

    if membership.role == "creator":
        new_creator = remaining_members[0]
        new_creator.role = "creator"
        circle.created_by = new_creator.user_id

    await db.delete(membership)
    await db.commit()
    return None


@router.delete("/{circle_id}/members/{user_id}", status_code=204)
async def remove_circle_member(
    circle_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes a member from a circle. Only circle admin can remove other members.
    """
    await ensure_circle_admin(circle_id, current_user, db)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Use leave circle or delete circle instead")

    membership = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id == user_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(membership)
    await db.commit()
    return None


@router.delete("/{circle_id}", status_code=204)
async def delete_circle(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a circle. Only circle admin can delete it.
    """
    await ensure_circle_admin(circle_id, current_user, db)
    await delete_circle_rows(circle_id, db)
    await db.commit()
    return None


@router.get("/{circle_id}/members")
async def get_circle_members(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns members of a circle only if current user belongs to it
    """
    membership = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id == current_user.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this circle")

    rows = await db.execute(
        select(CircleUser, User)
        .join(User, User.id == CircleUser.user_id)
        .where(CircleUser.circle_id == circle_id)
        .order_by(CircleUser.joined_at.asc())
    )

    return [
        {
            "id": user.id,
            "display_name": user.display_name or user.email or f"User {user.id}",
            "avatar_url": user.avatar_url,
            "role": circle_user.role,
            "is_current_user": user.id == current_user.id,
        }
        for circle_user, user in rows
    ]
