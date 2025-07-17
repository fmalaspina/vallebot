from fastapi import FastAPI, HTTPException
import chromadb, asyncio, os
from .service import ServiceAdd   # Usa import relativo si service.py está en el mismo paquete

app = FastAPI(
    title="ValleBot API",
    description="Backend de gestión de servicios por WhatsApp",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

@app.on_event("startup")
async def startup():
    # retry loop por si Chroma tarda un poco
    for _ in range(10):
        try:
            app.state.chroma = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "chroma"),
                port=int(os.getenv("CHROMA_PORT", 8000))
            )
            app.state.chroma.heartbeat()      # comprueba conexión
            break
        except Exception as e:
            await asyncio.sleep(2)
    else:
        raise RuntimeError("No se pudo conectar con Chroma")

@app.post("/add", summary="Añade un vector al almacén")
def add(item: ServiceAdd):
    col = app.state.chroma.get_or_create_collection(name=item.tipo)
    vector_id = f"{item.tipo}_{col.count()+1}"
    try:
        col.add(
            ids=[vector_id],
            documents=[item.contenido],
            metadatas=[item.metadatos]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al insertar: {e}")
    return {"id": vector_id, "coleccion": item.tipo, "metadata": item.metadatos}
