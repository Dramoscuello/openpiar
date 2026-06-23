# add_areas_table
# Revision ID: 61d7be033df6
# Revises: f38f5d1658dd
# Create Date: 2026-06-23 19:31:28.277977+00:00

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '61d7be033df6'
down_revision: Union[str, None] = 'f38f5d1658dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATALOGO_AREAS = {
    "Ciencias Naturales y Educación Ambiental": ["Ciencias Naturales", "Física", "Química", "Procesos Fisicoquímicos"],
    "Matemáticas": ["Matemáticas", "Geometría", "Estadística"],
    "Ciencias Sociales": ["Ciencias Sociales", "Historia", "Geografía"],
    "Humanidades, Lengua Castellana e Idiomas Extranjeros": ["Humanidades / Lengua Castellana (Español)", "Inglés"],
    "Educación Física, Recreación y Deportes": ["Educación Física"],
    "Educación Artística y Cultural": ["Educación Artística y Cultural"],
    "Educación Ética y en Valores Humanos": ["Ética y Valores"],
    "Educación Religiosa": ["Educación Religiosa"],
    "Tecnología e Informática": ["Tecnología e Informática"],
    "Filosofía": ["Filosofía"],
    "Ciencias Económicas y Políticas": ["Ciencias Económicas y Políticas"]
}


def get_area_for_subject(sub_name: str) -> str:
    for area, subjects in CATALOGO_AREAS.items():
        if any(s.strip().lower() == sub_name.strip().lower() for s in subjects):
            return area
    return "General"


def upgrade() -> None:
    # 1. Crear tabla areas si no existe (por si se auto-creó por SQLAlchemy metadata)
    connection = op.get_bind()
    table_exists = connection.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'areas')")
    ).scalar()

    if not table_exists:
        op.create_table(
            'areas',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('nombre', sa.Text(), nullable=False),
            sa.Column('institucion_id', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['institucion_id'], ['configuracion_sistema.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nombre', 'institucion_id', name='uq_area_nombre_institucion')
        )

    # 2. Agregar area_id a asignaturas como nullable primero
    op.add_column('asignaturas', sa.Column('area_id', sa.UUID(), nullable=True))

    # 3. Migración de Datos: poblar la tabla areas y asociar asignaturas existentes
    inst_id = connection.execute(
        sa.text("SELECT id FROM configuracion_sistema LIMIT 1")
    ).scalar()

    # Obtener todas las asignaturas actuales
    existing_asignaturas = connection.execute(
        sa.text("SELECT id, nombre FROM asignaturas")
    ).all()

    # Pre-crear áreas del catálogo en la BD para evitar duplicados
    area_name_to_id = {}
    
    # También asegurar que "General" exista si alguna asignatura no coincide
    areas_needed = set()
    for asig_id, asig_nombre in existing_asignaturas:
        areas_needed.add(get_area_for_subject(asig_nombre))

    # Insertar las áreas requeridas y guardar sus UUIDs
    for area_name in areas_needed:
        # Verificar si ya existe en la BD
        existing_area_id = connection.execute(
            sa.text("SELECT id FROM areas WHERE nombre = :nombre"),
            {"nombre": area_name}
        ).scalar()
        
        if existing_area_id:
            area_name_to_id[area_name] = existing_area_id
        else:
            new_area_id = uuid.uuid4()
            connection.execute(
                sa.text("INSERT INTO areas (id, nombre, institucion_id) VALUES (:id, :nombre, :inst_id)"),
                {"id": new_area_id, "nombre": area_name, "inst_id": inst_id}
            )
            area_name_to_id[area_name] = new_area_id

    # Actualizar asignaturas existentes con sus respectivos area_ids
    for asig_id, asig_nombre in existing_asignaturas:
        target_area_name = get_area_for_subject(asig_nombre)
        target_area_id = area_name_to_id[target_area_name]
        connection.execute(
            sa.text("UPDATE asignaturas SET area_id = :area_id WHERE id = :id"),
            {"area_id": target_area_id, "id": asig_id}
        )

    # Si hay alguna asignatura huérfana (por si acaso), asignarle o crear una área General
    null_asig_exist = connection.execute(
        sa.text("SELECT COUNT(*) FROM asignaturas WHERE area_id IS NULL")
    ).scalar()

    if null_asig_exist > 0:
        general_area_id = area_name_to_id.get("General")
        if not general_area_id:
            general_area_id = uuid.uuid4()
            connection.execute(
                sa.text("INSERT INTO areas (id, nombre, institucion_id) VALUES (:id, 'General', :inst_id)"),
                {"id": general_area_id, "inst_id": inst_id}
            )
        connection.execute(
            sa.text("UPDATE asignaturas SET area_id = :general_id WHERE area_id IS NULL"),
            {"general_id": general_area_id}
        )

    # 4. Establecer area_id como NOT NULL
    op.alter_column('asignaturas', 'area_id', nullable=False)

    # 5. Modificar restricciones de asignaturas
    # Eliminar índice de unicidad global
    try:
        op.drop_constraint('asignaturas_nombre_key', 'asignaturas', type_='unique')
    except Exception:
        # En algunos entornos el constraint tiene otro nombre o se creó como index
        try:
            op.drop_index('uq_asignaturas_nombre', table_name='asignaturas')
        except Exception:
            pass

    # Crear la nueva restricción única por área
    op.create_unique_constraint('uq_asignatura_nombre_area', 'asignaturas', ['nombre', 'area_id'])

    # Crear clave foránea
    op.create_foreign_key('fk_asignaturas_area_id', 'asignaturas', 'areas', ['area_id'], ['id'], ondelete='CASCADE')

    # 6. Estandarizar campo grados.nombre a Text si era VARCHAR (compatibilidad)
    op.alter_column('grados', 'nombre',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=False)


def downgrade() -> None:
    # 1. Agregar de vuelta la unicidad global
    op.drop_constraint('fk_asignaturas_area_id', 'asignaturas', type_='foreignkey')
    op.drop_constraint('uq_asignatura_nombre_area', 'asignaturas', type_='unique')
    
    # En caso de nombres duplicados entre áreas distintas, downgrade podría fallar si no se limpian
    # Pero para downgrade básico, intentamos recrear el unique constraint
    try:
        op.create_unique_constraint('asignaturas_nombre_key', 'asignaturas', ['nombre'])
    except Exception:
        pass

    op.drop_column('asignaturas', 'area_id')
    op.drop_table('areas')
