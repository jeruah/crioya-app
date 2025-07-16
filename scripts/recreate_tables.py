from app.database import Base, engine
from app import models

if __name__ == "__main__":
    print("Dropping tables...")
    Base.metadata.drop_all(engine)
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Done.")
