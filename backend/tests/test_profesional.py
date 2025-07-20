import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, delete
from app.database import engine
from app.models import ProfesionalModel
from sentence_transformers import SentenceTransformer

# Cargamos el modelo una sola vez (CPU)
model = SentenceTransformer("all-mpnet-base-v2", device="cpu")

def generar_embedding(texto: str):
    return model.encode(texto).tolist()

@pytest.mark.asyncio
async def test_busqueda_semantica_profesional():
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        nombre_psico = "Lucía Test RAG"
        desc_psico = "Psicóloga especialista en familias y adolescentes. Terapia, acompañamiento emocional."

        nombre_teatro = "Carolina Test RAG"
        desc_teatro = "Profesora que dicta clases de teatro creativo y expresión corporal para niños y adolescentes."

        # Insertar psicóloga
        psicologa = ProfesionalModel(
            nombre=nombre_psico,
            especialidad="Psicología",
            servicios=[{"nombre": "Terapia adolescente", "tipo": "turno", "duracion_min": 50}],
            agenda=[],
            embedding=generar_embedding(desc_psico)
        )
        session.add(psicologa)

        # Insertar profesora de teatro
        teatro = ProfesionalModel(
            nombre=nombre_teatro,
            especialidad="Teatro",
            servicios=[{"nombre": "Clases de teatro", "tipo": "regular", "duracion_min": 60}],
            agenda=[],
            embedding=generar_embedding(desc_teatro)
        )
        session.add(teatro)

        await session.commit()

        try:
            # Embedding de la consulta (lo que diría un usuario)
            query_embedding = generar_embedding("Busco una terapeuta para mi hija adolescente con problemas familiares")

            # Expresión de distancia (coseno)
            distance_expr = ProfesionalModel.embedding.cosine_distance(query_embedding).label("distancia")

            # Traemos los 2 mejores para comparar distancias
            stmt = (
                select(ProfesionalModel.id,
                       ProfesionalModel.nombre,
                       distance_expr)
                .order_by(distance_expr.asc())
                .limit(2)
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            assert rows, "No se recuperó ningún profesional"
            assert len(rows) >= 2, "Se esperaba al menos 2 resultados para comparar distancias"

            primero = rows[0]
            segundo = rows[1]

            # Aserciones semánticas
            assert primero.nombre == nombre_psico, (
                f"El primer resultado debería ser la psicóloga, pero vino: {primero.nombre}"
            )

            # Verificamos que la distancia del primero sea menor que la del segundo
            assert primero.distancia < segundo.distancia, (
                f"La distancia del primero ({primero.distancia}) no es menor que la del segundo ({segundo.distancia})"
            )

            # (Opcional) Podés establecer un umbral razonable si querés test más estricto:
            # assert primero.distancia < 0.7, f"Distancia muy alta para un match semántico: {primero.distancia}"

        except Exception:
            await session.rollback()
            raise
        finally:
            # Limpieza siempre (aunque falle el test)
            await session.execute(
                delete(ProfesionalModel).where(
                    ProfesionalModel.nombre.in_([nombre_psico, nombre_teatro])
                )
            )
            await session.commit()
