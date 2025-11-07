# prozlab_ai

A FastAPI backend with a modular structure inspired by Laravel, providing a clean and organized approach to building APIs.

## Getting Started

### Prerequisites

- Python 3.12
- PostgreSQL

### Installation

1. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```bash
   python setup_db.py
   ```

4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at http://localhost:8000.
