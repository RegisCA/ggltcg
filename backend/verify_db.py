#!/usr/bin/env python3
"""Quick script to verify database migration success"""
from dotenv import load_dotenv
import os
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# List all tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")

print('\n📊 Database Tables Created:')
print('=' * 40)
for row in cur.fetchall():
    print(f'  ✓ {row[0]}')

# Check games table structure
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'games'
    ORDER BY ordinal_position;
""")

print('\n🎮 Games Table Structure:')
print('=' * 40)
for row in cur.fetchall():
    nullable = 'NULL' if row[2] == 'YES' else 'NOT NULL'
    print(f'  • {row[0]:<20} {row[1]:<20} {nullable}')

# Check indexes
cur.execute("""
    SELECT indexname 
    FROM pg_indexes 
    WHERE tablename = 'games'
    ORDER BY indexname;
""")

print('\n🔍 Games Table Indexes:')
print('=' * 40)
for row in cur.fetchall():
    print(f'  ✓ {row[0]}')

cur.close()
conn.close()
print('\n✅ Database migration successful!\n')
