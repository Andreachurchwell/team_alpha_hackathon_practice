## TEAM ALPHA
### Hackathon MonoMeltdown

Hey team 👋

I put this small practice repo together to help us think through a possible game plan before the hackathon. This isn’t meant to be the “right” or only way to do things — just something to look at so we’re not starting from zero when we get handed that giant file.

The idea here is simple:

Instead of jumping straight into microservices and risking breaking a working app, we can first move the monolith into a cleaner folder structure while keeping everything running. Once responsibilities are clearer, splitting pieces into services becomes way less chaotic.

This repo starts with a single legacy file and shows how it can be moved into folders like:
```
app/
  api/
  models/
  data/
```
***Nothing fancy — just a safer path from “one huge file” → “organized code” → “possible services.”***

## 💡 Why this approach

My thinking was:
- Keep the app running at all times
- Split by responsibility instead of random file chunks
- Try extracting one small piece first instead of everything at once
- Totally open to other ideas — this is just a starting point for discussion.

## 🚀 How to Run (Local Setup)

Clone the repo and create a virtual environment before running the app.

1️⃣ Create and activate a virtual environment

Windows (Git Bash):
```
python -m venv .venv
source .venv/Scripts/activate
```

Mac/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```

You should see (venv) or (.venv) in your terminal once activated.

2️⃣ Install dependencies
```
pip install -r requirements.txt
```
3️⃣ Run the app
```
uvicorn app.main:app --reload
```

Then open:
```
http://localhost:8000/docs
```
