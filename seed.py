from database import Base, engine

print("☢️ INITIATING DATABASE WIPE...")
# This drops all tables in your Postgres database
Base.metadata.drop_all(bind=engine)

print("🏗️ REBUILDING FRESH TABLES...")
# This recreates the empty tables based on your models
Base.metadata.create_all(bind=engine)

print("✅ DATABASE IS CLEAN AND READY FOR SEEDING!")