# Property Management and Scraping Platform

A comprehensive, microservices-based platform for property market analysis, web scraping, and data management. This project automates the process of discovery, extraction, and normalization of property listings from various sources (like Otodom) while providing a robust management interface.

## System Architecture

The project follows a distributed microservices architecture using **RabbitMQ** for asynchronous communication, **PostgreSQL** for data persistence, and **Redis** for distributed state management.

### Core Services

- **[crudhouse/](crudhouse/)**: A Django-based management portal. Handles user authentication, domain management, job definitions, and provides a web-based dashboard for monitoring.
- **[scraper/](scraper/)**: The core scraping engine. Listen for jobs via RabbitMQ and extracts data from configured sources.
- **[scheduler/](scheduler/)**: Monitors the database for scheduled tasks and dispatches jobs to RabbitMQ.
- **[throttling/](throttling/)**: A distributed rate-limiting service using the **Token Bucket** algorithm to prevent blocking from target domains.
- **[data_ingestion/](data_ingestion/)**: Handles the normalization and insertion of scraped data into the primary database.
- **[logger/](logger/)**: Centralized logging service that monitors job progress and execution logs across the system.
- **[shared/](shared/)**: Common utilities, constants, and database models used across multiple services.
- **[bench/](bench/)**: Performance monitoring and benchmarking tools for the scraping pipeline.

## Technology Stack

- **Languages**: Python 3.x
- **Frameworks**: Django (Management), Asyncio (Microservices)
- **Messaging**: RabbitMQ
- **Database**: PostgreSQL
- **Caching/State**: Redis
- **Containerization**: Docker & Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd property
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the root directory based on the configuration expected in [docker-compose.yml](docker-compose.yml).

3. **Spin up the infrastructure**:
   ```bash
   docker-compose up --build
   ```

4. **Access the Management Portal**:
   Once the services are up, navigate to `http://localhost:8000` to access the CRUDHouse dashboard.

## Service Breakdown

| Service | Description | Port |
|---------|-------------|------|
| `crudhouse` | Django Web Management | 8000 |
| `rabbitmq` | Message Broker & Management UI | 5672, 15672 |
| `postgres` | Primary Database | 5432 |
| `redis` | Throttling & State Store | 6379|

## Project Structure

```text
├── bench/            # Pipeline benchmarking
├── crudhouse/        # Django management application
├── data_ingestion/   # Scraped data processing
├── logger/           # Distributed logging service
├── scheduler/        # Task scheduling service
├── scraper/          # Web scraping engine
├── shared/           # Common code library
├── throttling/       # Rate limiting service
└── docker-compose.yml # Orchestration
```
