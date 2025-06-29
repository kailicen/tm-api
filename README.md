# 🛠️ API App for [my-tm-app](https://my-tm-app.vercel.app/)

This is the backend API for the [my-tm-app](https://my-tm-app.vercel.app/) – a Toastmasters role assignment assistant.

---

## 🚀 Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
# Activate for Windows:
venv\Scripts\activate
# Activate for macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 🔑 Environment Variables

### Create a .env file in the project root:

```bash
CLUB_NUMBER=6247
PASSWORD=HotelSOHO6247
SUPABASE_URL=https://viensgnbkrxetuoremvp.supabase.co
SUPABASE_KEY=eyJhbGciOiJI.... (your Supabase API key)
```

## 🏃 Run Locally

### Start the API server:

```bash
uvicorn main:app --reload
```

### The API will be available at:

http://127.0.0.1:8000

## 📦 Deployment with Fly.io

```bash
flyctl deploy
```

## 🗂️ Git Workflow

```bash
git add .
git commit -m "Your commit message"
git push origin main
```

## ✅ Notes

Make sure your .env file is NOT committed to version control.
The frontend app is hosted here: https://my-tm-app.vercel.app/
Fly.io will automatically build and deploy your app when you run flyctl deploy.
