# add_grados_table
# Revision ID: f38f5d1658dd
# Revises: 14cb46b310db
# Create Date: 2026-06-23 19:03:29.032480+00:00

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f38f5d1658dd'
down_revision: Union[str, None] = '14cb46b310db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla grados
    op.create_table(
        'grados',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nombre', sa.String(), nullable=False),
        sa.Column('institucion_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['institucion_id'], ['configuracion_sistema.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre', 'institucion_id', name='uq_grado_nombre_institucion')
    )

    # 2. Agregar grado_id a grupos como nullable primero
    op.add_column('grupos', sa.Column('grado_id', sa.UUID(), nullable=True))

    # 3. Migrar datos existentes de grupos a grados
    connection = op.get_bind()
    
    # Obtener el ID de la primera institución si existe
    inst_id = connection.execute(
        sa.text("SELECT id FROM configuracion_sistema LIMIT 1")
    ).scalar()
    
    # Obtener nombres de grados únicos de la tabla grupos
    unique_grades = connection.execute(
        sa.text("SELECT DISTINCT grado FROM grupos WHERE grado IS NOT NULL")
    ).scalars().all()
    
    grade_map = {}
    for g_name in unique_grades:
        g_id = uuid.uuid4()
        connection.execute(
            sa.text("INSERT INTO grados (id, nombre, institucion_id) VALUES (:id, :nombre, :inst_id)"),
            {"id": g_id, "nombre": g_name, "inst_id": inst_id}
        )
        grade_map[g_name] = g_id
        
    # Actualizar la columna grado_id en grupos con el UUID correspondiente
    for g_name, g_id in grade_map.items():
        connection.execute(
            sa.text("UPDATE grupos SET grado_id = :g_id WHERE grado = :g_name"),
            {"g_id": g_id, "g_name": g_name}
        )

    # Si hay grupos pero no tienen grado asignado
    null_groups_exist = connection.execute(
        sa.text("SELECT COUNT(*) FROM grupos WHERE grado_id IS NULL")
    ).scalar()
    
    if null_groups_exist > 0:
        default_grade_id = uuid.uuid4()
        connection.execute(
            sa.text("INSERT INTO grados (id, nombre, institucion_id) VALUES (:id, :nombre, :inst_id)"),
            {"id": default_grade_id, "nombre": "Preescolar", "inst_id": inst_id}
        )
        connection.execute(
            sa.text("UPDATE grupos SET grado_id = :default_id WHERE grado_id IS NULL"),
            {"default_id": default_grade_id}
        )

    # 4. Establecer grado_id como NOT NULL
    op.alter_column('grupos', 'grado_id', nullable=False)

    # 5. Modificar las restricciones únicas y llaves foráneas
    op.drop_constraint('uq_grupo_sede', 'grupos', type_='unique')
    op.create_unique_constraint('uq_grupo_sede', 'grupos', ['nombre', 'grado_id', 'sede_id'])
    op.create_foreign_key('fk_grupos_grado_id', 'grupos', 'grados', ['grado_id'], ['id'], ondelete='CASCADE')

    # 6. Eliminar la columna vieja grado
    op.drop_column('grupos', 'grado')


def downgrade() -> None:
    # 1. Agregar columna grado como nullable
    op.add_column('grupos', sa.Column('grado', sa.TEXT(), autoincrement=False, nullable=True))

    # 2. Migrar nombres de grados de vuelta a grupos
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE grupos SET grado = grados.nombre FROM grados WHERE grupos.grado_id = grados.id")
    )

    # Si algún grado quedó nulo, poner valor por defecto
    connection.execute(
        sa.text("UPDATE grupos SET grado = 'Preescolar' WHERE grado IS NULL")
    )

    # 3. Establecer grado como NOT NULL
    op.alter_column('grupos', 'grado', nullable=False)

    # 4. Restaurar restricciones anteriores
    op.drop_constraint('fk_grupos_grado_id', 'grupos', type_='foreignkey')
    op.drop_constraint('uq_grupo_sede', 'grupos', type_='unique')
    op.create_unique_constraint('uq_grupo_sede', 'grupos', ['nombre', 'grado', 'sede_id'])

    # 5. Eliminar grado_id de grupos
    op.drop_column('grupos', 'grado_id')

    # 6. Eliminar tabla grados
    op.drop_table('grados')
