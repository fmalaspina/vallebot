from fastapi import FastAPI
import chromadb

app = FastAPI()
client = chromadb.HttpClient(host="chroma", port=8000)  # ← usa servicio Compose

@app.get("/")
def root():
    return {"msg": "Backend conectado a Chroma!"}

@app.post("/add")
def add():
    col = client.get_or_create_collection("alojamientos")
    col.add(
        documents=["Cabaña El Refugio, pileta, acepta mascotas"],
        metadatas=[{"nombre": "El Refugio"}],
        ids=["cabana_1"]
    )
    return {"ok": True}
