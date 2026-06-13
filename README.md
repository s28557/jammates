# Jam×Mates

A concert discovery web application that recommends live music events based on your Spotify listening history and lets you find concerts you can attend together with friends.

## Features

- **Spotify authentication**: log in with your Spotify account
- **For You**: concert recommendations tailored to your music taste
- **Something New**: concerts by artists similar to ones you already like
- **Circles**: create groups with friends (up to 4 members) and get shared concert recommendations based on everyone's taste
- **Interactive map**: browse concert locations on an OpenStreetMap-powered map
- **Concert filtering**: filter by country and other criteria

## Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) - REST API
- [PostgreSQL](https://www.postgresql.org/) - primary database
- [SQLAlchemy](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/) - ORM and migrations
- [Redis](https://redis.io/) - response caching
- [Ticketmaster API](https://developer.ticketmaster.com/) - concert data
- [Spotify Web API](https://developer.spotify.com/documentation/web-api) - user music data and authentication

**Frontend**
- [React](https://react.dev/) + [Vite](https://vitejs.dev/)
- [React Leaflet](https://react-leaflet.js.org/) - interactive map
- [Lucide React](https://lucide.dev/) - icons

**Infrastructure**
- Docker Compose - PostgreSQL, Redis, pgAdmin

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- A [Spotify Developer](https://developer.spotify.com/dashboard) app
- A [Ticketmaster API](https://developer.ticketmaster.com/) key

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd jammates
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL (port 5433), Redis (port 6379), and pgAdmin (port 5050).

### 3. Configure the backend

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DATABASE_URI=postgresql+asyncpg://jammates:jammates_pass@localhost:5433/jammates_db
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/auth/spotify/callback
TICKETMASTER_API_KEY=your-ticketmaster-api-key
REDIS_URL=redis://localhost:6379
FRONTEND_URL=http://localhost:5173
ENCRYPTION_KEY=your-fernet-key
```

To generate a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

To generate an `ENCRYPTION_KEY` (Fernet):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

In your Spotify Developer Dashboard, add `http://127.0.0.1:8000/api/v1/auth/spotify/callback` as a Redirect URI.

### 4. Install backend dependencies and run migrations

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Project Structure

```
jammates/
├── app/
│   ├── api/endpoints/      # FastAPI route handlers
│   ├── core/               # Config, database, cache, security
│   ├── models/             # SQLAlchemy models
│   └── services/           # Business logic (Spotify, Ticketmaster, recommendations)
├── alembic/                # Database migrations
├── frontend/
│   └── src/
│       ├── api/            # API client functions
│       ├── components/     # Reusable React components
│       ├── pages/          # Page components
│       └── layout/         # App shell and navigation
├── uploads/                # Circle images
└── docker-compose.yml
```

## pgAdmin

pgAdmin is available at `http://localhost:5050` with:
- Email: `admin@jammates.dev`
- Password: `admin`

Connect to the database using host `postgres`, port `5432`, user `jammates`, password `jammates_pass`, database `jammates_db`.