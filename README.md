# Travel planner API.
RESTful API for travel planning and managing cultural objects.  
Built with FastAPI, using asynchronous SQLAlchemy 2.0 and integration with a public API.  

## Project Structure
```
travel_planner
├── alembic                # Database migrations
│   ├── versions           # Individual migration files
│   ├── env.py             # Alembic environment configuration
│   ├── README             # Alembic documentation
│   └── script.py.mako     # Template for generating migrations
├── app                    # Main application code
│   ├── core               # Configurations, dependencies, authentication
│   ├── models             # SQLAlchemy models
│   ├── router             # FastAPI routers (auth, projects, places)
│   ├── schemas            # Pydantic schemas for request/response validation
│   └── services           # Business logic and integrations
│       └── main.py        # FastAPI entry point (app = FastAPI())
├── .dockerignore          # Files excluded from Docker image
├── .gitignore             # Files excluded from Git
├── alembic.ini            # Alembic global configuration
├── docker-compose.yml     # Docker services configuration
├── Dockerfile             # Docker image build instructions
├── README.md              # Project documentation
└── requirements.txt       # Python dependencies
```
## Technologies Used

- **FastAPI** — modern Python web framework for building RESTful APIs
- **SQLAlchemy 2.0 (async)** — ORM for database models and asynchronous queries
- **Alembic** — database migrations management
- **SQLite** — lightweight relational database for local development
- **Docker & Docker Compose** — containerization and service orchestration
- **Uvicorn + Gunicorn** — ASGI server for running FastAPI
- **Pydantic** — data validation and serialization
- **JWT (JSON Web Tokens)** — authentication and authorization
- **Art Institute of Chicago API** — third‑party API integration for validating places

## Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
APP_NAME="Travel Planner API"          # Application name (used in docs/metadata)
APP_VERSION="1.0.0"                    # Application version
DEBUG=true                             # Debug mode (true/false)

DATABASE_URL=sqlite+aiosqlite:///./travel_planner.db   # Database connection string (SQLite for local dev)

SECRET_KEY=secret-key                  # Secret key for JWT signing
ALGORITHM=HS256                        # Algorithm used for JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15         # Access token lifetime in minutes
REFRESH_TOKEN_EXPIRE_DAYS=7            # Refresh token lifetime in days

ADMIN_USERNAME=admin                   # Default admin username
ADMIN_PASSWORD=secret                  # Default admin password

ARTIC_BASE_URL=https://api.artic.edu/api/v1   # Base URL for Art Institute of Chicago API
ARTIC_REQUEST_TIMEOUT=10.0              # Timeout for requests to external API (seconds)

CACHE_TTL_SECONDS=3600                  # Cache lifetime for external API responses (seconds)
MAX_PLACES_PER_PROJECT=10               # Maximum number of places allowed per project
```


## Running the Project with Docker

### Build and start containers
```bash
docker-compose up --build
```
**This will:**  
- Build the Docker image from the Dockerfile  
- Start the application container defined in docker-compose.yml  
- Run the FastAPI server inside the container

## Access the API
Once the container is running, the API is available at:

```
http://localhost:8000
```
Swagger UI (interactive documentation):

```
http://localhost:8000/docs
```
Healthcheck  
Verify the service is running:

```
curl http://localhost:8000/health
```
Expected response:  
**{"status":"ok"}**

## Screenshots

### Swagger UI
<img width="1104" height="790" alt="зображення" src="https://github.com/user-attachments/assets/123bcf70-1ace-467c-b401-cd6fb143e6e3" />
<img width="1224" height="852" alt="зображення" src="https://github.com/user-attachments/assets/307315f7-81a6-40ad-b44b-0d77af8c7c1a" />




