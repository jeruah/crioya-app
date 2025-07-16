from app.database import Base, engine
from app import models

if __name__ == "__main__":
    table_names = ['entradas_insumo', 'salidas_insumo', 'insumos', 'movimientos']
    tables = [Base.metadata.tables[name] for name in table_names]
    print("Dropping tables...")
    Base.metadata.drop_all(engine, tables=tables)
    print("Creating tables...")
    Base.metadata.create_all(engine, tables=tables)
    print("Done.")